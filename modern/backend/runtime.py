# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey
#
# Adapted from GEstimator modern/backend/runtime.py at 6ba679b (owner thread,
# bounded queue, futures, session management).

"""Runtime: one owner thread for all project state, document sessions and a
job runner for long work (docs/architecture/backend.md sections 4 and 6).

Every read and write of a session runs on the owner thread. Transports (the
JSON Lines loop, later MCP) only parse requests, :meth:`Runtime.submit` them
and wait for the future. Analysis and exports run on a job thread against
immutable snapshots; their results are handed back to the owner thread.
"""

import itertools
import logging
import threading
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from queue import Queue, Full

from . import registry
from .protocol import (ServiceError, invalid, not_found, check_session_id, JOB_ERROR, CANCELLED,
                       BACKEND_ERROR, INVALID_REQUEST)
from .session import Session, DEFAULT_HISTORY_LIMIT

log = logging.getLogger(__name__)

MAIN_SESSION = 'main'
MAX_SESSIONS = 32
QUEUE_SIZE = 256


class Context:
    """What a service method sees"""

    def __init__(self, runtime, session, source):
        self.runtime = runtime
        self.session = session
        self.source = source

    @property
    def project(self):
        return self.session.project


class JobCancelled(Exception):
    pass


class Job:
    def __init__(self, runtime, session_id, kind, revision):
        self.id = 'j-' + uuid.uuid4().hex[:12]
        self.runtime = runtime
        self.session_id = session_id
        self.kind = kind
        self.revision = revision
        self.status = 'queued'
        self.fraction = 0.0
        self.message = ''
        self.stage = ''
        self.result = None
        self.error = None
        self.cancel_event = threading.Event()

    def report(self, fraction, message='', stage=''):
        """Progress from the job thread; raises JobCancelled when cancelled
        (cooperative cancellation between stages)"""
        if self.cancel_event.is_set():
            raise JobCancelled()
        self.fraction = float(fraction)
        self.message = message
        self.stage = stage
        self.runtime.emit({'event': 'progress', 'session': self.session_id, 'job': self.id,
                           'kind': self.kind, 'stage': stage, 'fraction': self.fraction, 'message': message})

    def summary(self):
        data = {'job': self.id, 'session': self.session_id, 'kind': self.kind, 'status': self.status,
                'revision': self.revision, 'fraction': self.fraction, 'message': self.message,
                'stage': self.stage}
        if self.error is not None:
            data['error'] = self.error
        return data


class Runtime:
    def __init__(self, emit=None, settings=None, history_limit=DEFAULT_HISTORY_LIMIT, create_main=True):
        registry.load_services()
        from .services.settings import SettingsStore
        self._emit = emit or (lambda message: None)
        self.settings = settings if settings is not None else SettingsStore()
        self.history_limit = history_limit
        self.sessions = {}
        self.active = None
        self.jobs = {}
        self._counter = itertools.count(1)
        self.closed = False
        self.queue = Queue(maxsize=QUEUE_SIZE)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='gelectrical-job')
        self.thread = threading.Thread(target=self._run, name='gelectrical-owner', daemon=True)
        self.thread.start()
        if create_main:
            self.call('session.create', {'session': MAIN_SESSION})

    # -- events ---------------------------------------------------------------

    def emit(self, message):
        try:
            self._emit(message)
        except Exception:
            log.exception('Runtime - emit - event could not be sent')

    # -- owner thread ---------------------------------------------------------

    def _run(self):
        while True:
            item = self.queue.get()
            if item is None:
                break
            future, func = item
            if not future.set_running_or_notify_cancel():
                continue
            try:
                future.set_result(func())
            except BaseException as exc:  # delivered to the caller
                future.set_exception(exc)

    def run_on_owner(self, func, block=False):
        """Run ``func()`` on the owner thread; returns a Future"""
        future = Future()
        if self.closed:
            future.set_exception(ServiceError(INVALID_REQUEST, 'Application is closing'))
            return future
        try:
            if block:
                self.queue.put((future, func))
            else:
                self.queue.put_nowait((future, func))
        except Full:
            future.set_exception(ServiceError(BACKEND_ERROR, 'Backend is busy; retry shortly'))
        return future

    def submit(self, method, params=None, session=None, source='desktop'):
        """Queue a request; returns a Future of its result"""
        params = dict(params or {})
        return self.run_on_owner(lambda: self.dispatch(method, params, session, source))

    def call(self, method, params=None, session=None, source='desktop', timeout=120):
        """Blocking :meth:`submit` (tests, MCP adapter)"""
        return self.submit(method, params, session, source).result(timeout=timeout)

    # -- dispatch (owner thread) ----------------------------------------------

    def dispatch(self, method, params, session_id=None, source='desktop'):
        entry = registry.METHODS.get(method)
        if entry is None:
            raise invalid('Unknown method %r' % method, field='method')
        if entry.kind == 'runtime':
            ctx = Context(self, None, source)
            entry.bind(ctx, params)
            return entry.func(ctx, **params)
        session = self.get_session(session_id)
        ctx = Context(self, session, source)
        if entry.kind == 'command':
            preview = params.pop('preview', False)
            if_revision = params.pop('if_revision', None)
            if not isinstance(preview, bool):
                raise invalid('preview must be true or false', field='preview')
            if if_revision is not None and (not isinstance(if_revision, int) or isinstance(if_revision, bool)):
                raise invalid('if_revision must be an integer', field='if_revision')
            entry.bind(ctx, params)
            result = session.execute(lambda: entry.func(ctx, **params), label=entry.label,
                                     preview=preview, if_revision=if_revision, source=source)
            return result.to_dict()
        entry.bind(ctx, params)
        return entry.func(ctx, **params)

    # -- sessions (owner thread) ----------------------------------------------

    def get_session(self, session_id=None):
        identity = self.active if session_id is None else check_session_id(session_id)
        session = self.sessions.get(identity)
        if session is None:
            raise not_found('This document is closed; reopen the project', field='session')
        return session

    def create_session(self, session_id=None):
        if session_id is None:
            session_id = 's-%d' % next(self._counter)
            while session_id in self.sessions:
                session_id = 's-%d' % next(self._counter)
        check_session_id(session_id)
        if session_id in self.sessions:
            raise ServiceError('CONFLICT', 'Document session already exists', field='session')
        if len(self.sessions) >= MAX_SESSIONS:
            raise ServiceError('CONFLICT', 'Close a document before opening more than %d' % MAX_SESSIONS)
        session = Session(session_id, program_settings=self.settings.values,
                          history_limit=self.history_limit, emit=self.emit)
        self.sessions[session_id] = session
        if self.active is None:
            self.active = session_id
        return session

    def close_session(self, session_id):
        session = self.get_session(session_id)
        for job in self.jobs.values():
            if job.session_id == session.id and job.status in ('queued', 'running'):
                job.cancel_event.set()
        del self.sessions[session.id]
        if self.active == session.id:
            self.active = next(iter(self.sessions), None)
        self.emit({'event': 'session_closed', 'session': session.id})
        return {'active': self.active}

    # -- jobs -----------------------------------------------------------------

    def start_job(self, session, kind, work, finish=None):
        """Run ``work(job)`` on the job thread. ``finish(session, job,
        result)`` then runs on the owner thread if the session is still open.
        Returns the Job (status ``queued``)."""
        job = Job(self, session.id, kind, session.revision)
        self.jobs[job.id] = job
        # Keep the job table bounded
        if len(self.jobs) > 200:
            for job_id in [j for j, entry in self.jobs.items()
                           if entry.status not in ('queued', 'running')][:len(self.jobs) - 200]:
                del self.jobs[job_id]

        def run():
            if job.cancel_event.is_set():
                outcome = ('cancelled', None, None)
            else:
                job.status = 'running'
                try:
                    outcome = ('finished', work(job), None)
                except JobCancelled:
                    outcome = ('cancelled', None, None)
                except ServiceError as exc:
                    outcome = ('failed', None, exc.to_dict())
                except Exception as exc:
                    log.exception('Runtime - job %s (%s) failed', job.id, kind)
                    outcome = ('failed', None, {'code': JOB_ERROR, 'message': '%s: %s' % (type(exc).__name__, exc)})
            self.run_on_owner(lambda: self._finish_job(job, outcome, finish), block=True)

        self.executor.submit(run)
        return job

    def _finish_job(self, job, outcome, finish):
        status, result, error = outcome
        session = self.sessions.get(job.session_id)
        if status == 'finished' and finish is not None and session is not None:
            try:
                result = finish(session, job, result)
            except Exception as exc:
                log.exception('Runtime - job %s - storing results failed', job.id)
                status, error = 'failed', {'code': JOB_ERROR, 'message': str(exc)}
        if status == 'cancelled':
            error = {'code': CANCELLED, 'message': 'Cancelled'}
        job.status = status
        job.result = result
        job.error = error
        if status == 'finished':
            job.fraction = 1.0
        event = {'event': 'job_finished', **job.summary()}
        self.emit(event)

    def get_job(self, job_id):
        if not isinstance(job_id, str) or job_id not in self.jobs:
            raise not_found('Unknown job', field='job')
        return self.jobs[job_id]

    # -- shutdown -------------------------------------------------------------

    def close(self, timeout=30):
        if self.closed:
            return
        for job in self.jobs.values():
            job.cancel_event.set()
        self.closed = True
        self.executor.shutdown(wait=True, cancel_futures=True)
        self.queue.put((Future(), lambda: None))
        self.queue.put(None)
        self.thread.join(timeout)
