# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Analysis service (docs/architecture/backend.md section 6).

``analysis.start`` captures the committed snapshot, returns a job id at once
and runs the legacy pipeline (``gelectrical.analysis.run_analysis``) on a
detached copy of the project on the job thread. The live document is never
changed: node display elements exist only in the copy (E09 *Changed*:
results overlay keyed by node identity). Results are stored per session with
the revision they were computed from and reported ``stale`` after edits.
"""

import logging
import time

from gelectrical.analysis import (AnalysisSettings, AnalysisResult, AnalysisError, run_analysis,
                                  run_rules_check)
from gelectrical.analysis.pipeline import POWERFLOW_METHODS
from gelectrical.core import constants

from .. import document, dto
from ..protocol import json_safe, invalid, validation, not_found
from ..registry import query, session_method
from .common import require_bool, require_choice, require_uid_list
from .drawing import node_identities

log = logging.getLogger(__name__)

_STAGES = ((0.6, 'results'), (0.5, 'sc_gf'), (0.4, 'sc_sym'), (0.3, 'powerflow'),
           (0.2, 'diagnostics'), (0.1, 'power_model'), (0.0, 'base_model'))


def _stage(fraction):
    for limit, name in _STAGES:
        if fraction >= limit:
            return name
    return 'base_model'


class AnalysisState:
    """Results of one analysis run (owned by the session)"""

    def __init__(self, job_id, revision, settings, three_phase):
        self.job_id = job_id
        self.revision = revision
        self.settings = settings
        self.three_phase = three_phase
        self.project = None         # analysed copy (job thread only)
        self.result = None          # AnalysisResult
        self.error = None
        self.elements = {}          # uid -> result field records
        self.nodes = []             # node overlay
        self.diagnostics = []
        self.rules = None
        self.node_keys = {}         # global node number -> node key
        self.duration_s = None

    def node_key(self, gnode):
        return self.node_keys.get(gnode, 'gnode:%s' % gnode)

    def summary(self, current_revision):
        result = self.result
        return {'job': self.job_id, 'revision': self.revision, 'stale': self.revision != current_revision,
                'completed': bool(result and result.completed), 'error': self.error,
                'steps': [step.name for step in result.steps] if result else [],
                'diagnostics_ret_code': result.diagnostics_ret_code if result else None,
                'rules_check_ready': bool(result and result.rules_check_ready),
                'rules_checked': self.rules is not None,
                'settings': {'diagnostics': self.settings.diagnostics, 'powerflow': self.settings.powerflow,
                             'pf_method': self.settings.pf_method, 'three_phase': self.three_phase,
                             'sc_sym': self.settings.sc_sym, 'sc_gf': self.settings.sc_gf},
                'duration_s': self.duration_s}


def _key_to_uid(snapshot):
    return {(k1, k2): uid for k1, sheet in enumerate(snapshot.sheets)
            for k2, (uid, _model) in enumerate(sheet.elements)}


def _collect(state, project, key_to_uid):
    """Typed results of the analysed copy (job thread)"""
    for k1, drawing_model in enumerate(project.drawing_models):
        for k2, element in enumerate(drawing_model.elements):
            uid = key_to_uid.get((k1, k2))
            if uid and element.res_fields and element.code not in constants.DISPLAY_ELEMENT_CODES:
                state.elements[uid] = dto.result_fields(element.res_fields)
    nodes = []
    powermodel = project.powermodel
    networkmodel = project.networkmodel
    if networkmodel is not None:
        identities = node_identities(project, networkmodel)
        state.node_keys = {gnode: identity['key'] for gnode, identity in identities.items()}
        if powermodel is not None and state.result.completed:
            for gnode, identity in identities.items():
                if gnode in powermodel.node_results:
                    nodes.append(dict(identity, gnode=gnode,
                                      results=dto.result_fields(powermodel.node_results[gnode])))
    state.nodes = nodes
    state.diagnostics = dto.message_list(state.result.diagnostics, key_to_uid, state.node_key)


def _settings(project, options):
    sim = project.get_project_fields(page='Simulation')
    base = AnalysisSettings.from_project(project, run_all=False)
    three_phase = bool(sim['power_flow_3ph']['value'])
    if options is None:
        return base, three_phase
    if not isinstance(options, dict):
        raise invalid('Expected an object of analysis settings', field='settings')
    allowed = ('diagnostics', 'powerflow', 'pf_method', 'three_phase', 'sc_sym', 'sc_gf')
    for key in options:
        if key not in allowed:
            raise invalid('Unknown analysis setting %r' % key, field='settings')
    for key in ('diagnostics', 'powerflow', 'sc_sym', 'sc_gf'):
        if key in options:
            setattr(base, key, require_bool(options[key], 'settings.' + key))
    if 'pf_method' in options:
        base.pf_method = require_choice(options['pf_method'], POWERFLOW_METHODS, 'settings.pf_method')
    if 'three_phase' in options:
        three_phase = require_bool(options['three_phase'], 'settings.three_phase')
    return base, three_phase


SAVE_SETTINGS_LABEL = 'Update analysis settings'
# AnalysisSettings attribute -> Simulation field (legacy MainWindow.on_run_analysis)
_SIMULATION_FIELDS = (('diagnostics', 'run_diagnostics'), ('powerflow', 'run_powerflow'),
                      ('pf_method', 'pf_method'), ('sc_sym', 'run_sc_sym'), ('sc_gf', 'run_sc_gf'))


def _save_settings(project, analysis_settings, three_phase):
    sim = project.get_project_fields(page='Simulation')
    for attribute, code in _SIMULATION_FIELDS:
        sim[code]['value'] = getattr(analysis_settings, attribute)
    sim['power_flow_3ph']['value'] = three_phase


@session_method('analysis.start')
def start(ctx, settings=None, rules_check=False):
    """Start an analysis job; returns the job id at once.

    ``settings`` (optional: diagnostics, powerflow, pf_method, three_phase,
    sc_sym, sc_gf) are saved into the project's Simulation settings first, as
    the legacy analysis dialog does (one undo entry when they change)."""
    session = ctx.session
    analysis_settings, three_phase = _settings(ctx.project, settings)
    require_bool(rules_check, 'rules_check')
    if settings is not None:
        session.execute(lambda: _save_settings(ctx.project, analysis_settings, three_phase),
                        label=SAVE_SETTINGS_LABEL, source=ctx.source)
    snapshot = session.snapshot
    factory = session.project_factory()
    key_to_uid = _key_to_uid(snapshot)

    def work(job):
        started = time.monotonic()
        state = AnalysisState(job.id, job.revision, analysis_settings, three_phase)
        job.report(0, 'Preparing project copy...', 'prepare')
        project = document.new_project_from(snapshot, factory)
        project.fields['Simulation']['power_flow_3ph']['value'] = three_phase
        state.project = project
        state.result = AnalysisResult(settings=analysis_settings)

        def progress(fraction, message):
            job.report(fraction, message, _stage(fraction))

        try:
            run_analysis(project, analysis_settings, progress=progress, result=state.result)
        except AnalysisError as exc:
            state.error = 'Diagnostics run returned critical errors'
            log.info('analysis.start - %s', exc)
        _collect(state, project, key_to_uid)
        if rules_check and state.result.rules_check_ready:
            job.report(0.8, 'Running Rules Check...', 'rules_check')
            state.rules = dto.message_list(run_rules_check(project), key_to_uid, state.node_key)
        state.duration_s = round(time.monotonic() - started, 3)
        return state

    def finish(session, job, state):
        session.analysis = state
        session.emit({'event': 'changed', 'session': session.id, 'revision': session.revision,
                      'changes': [{'kind': 'analysis'}], 'source': ctx.source, 'dirty': session.dirty})
        return state.summary(session.revision)

    job = ctx.runtime.start_job(session, 'analysis', work, finish)
    return job.summary()


def _state(ctx, require_fresh=False, require_completed=False):
    state = ctx.session.analysis
    if state is None:
        raise not_found('No analysis results; run the analysis first')
    if require_fresh and state.revision != ctx.session.revision:
        raise validation('Analysis results are out of date; run the analysis again')
    if require_completed and not (state.result and state.result.completed):
        raise validation('The last analysis did not complete')
    return state


@query('analysis.status')
def status(ctx):
    """Summary of the stored results (``null`` if none) and running jobs"""
    session = ctx.session
    jobs = [job.summary() for job in ctx.runtime.jobs.values()
            if job.session_id == session.id and job.status in ('queued', 'running')]
    return {'results': session.analysis.summary(session.revision) if session.analysis else None, 'jobs': jobs}


@query('analysis.results')
def results(ctx, uids=None, nodes=True):
    """Result fields per element uid, node overlay, diagnostics and rules messages"""
    state = _state(ctx)
    require_bool(nodes, 'nodes')
    if uids is None:
        elements = state.elements
    else:
        elements = {uid: state.elements[uid] for uid in require_uid_list(uids, allow_empty=True)
                    if uid in state.elements}
    return json_safe({'summary': state.summary(ctx.session.revision), 'elements': elements,
                      'nodes': state.nodes if nodes else None,
                      'diagnostics': state.diagnostics, 'rules': state.rules})


@session_method('analysis.clear')
def clear(ctx):
    """Clear stored results (not a document change; nothing to undo)"""
    session = ctx.session
    session.analysis = None
    session.emit({'event': 'changed', 'session': session.id, 'revision': session.revision,
                  'changes': [{'kind': 'analysis'}], 'source': ctx.source, 'dirty': session.dirty})
    return {'cleared': True}


@session_method('analysis.rules_check')
def rules_check(ctx):
    """Run the electrical rules check on the stored results (job)"""
    state = _state(ctx, require_completed=True)
    if not state.result.rules_check_ready:
        raise validation('Rules check needs power flow and both short circuit calculations')
    key_to_uid = {}
    for uid, (k1, k2, _model) in ctx.session.snapshot.element_index().items():
        key_to_uid[(k1, k2)] = uid
    if state.revision != ctx.session.revision:
        raise validation('Analysis results are out of date; run the analysis again')

    def work(job):
        job.report(0, 'Running Rules Check...', 'rules_check')
        return dto.message_list(run_rules_check(state.project), key_to_uid, state.node_key)

    def finish(session, job, messages):
        state.rules = messages
        session.emit({'event': 'changed', 'session': session.id, 'revision': session.revision,
                      'changes': [{'kind': 'analysis'}], 'source': ctx.source, 'dirty': session.dirty})
        return {'messages': len(messages)}

    return ctx.runtime.start_job(ctx.session, 'rules_check', work, finish).summary()


@session_method('analysis.job')
def job(ctx, job):
    """State of a job (with its result once finished)"""
    entry = ctx.runtime.get_job(job)
    if entry.session_id != ctx.session.id:
        raise not_found('Unknown job', field='job')
    data = entry.summary()
    if entry.status == 'finished':
        data['result'] = json_safe(entry.result)
    return data


@session_method('analysis.cancel')
def cancel(ctx, job):
    """Cancel a job (between stages)"""
    entry = ctx.runtime.get_job(job)
    if entry.session_id != ctx.session.id:
        raise not_found('Unknown job', field='job')
    if entry.status in ('queued', 'running'):
        entry.cancel_event.set()
    return entry.summary()
