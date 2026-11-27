"""JSON Lines protocol: spawn ``python -m modern.backend`` and talk to it (M4)"""

import json
import os
import queue
import subprocess
import sys
import threading
import time

import pytest

from conftest import ROOT, SAMPLE, _DATA_DIR


class Backend:
    def __init__(self):
        env = dict(os.environ, GELECTRICAL_USER_DATA_DIR=_DATA_DIR, PYTHONIOENCODING='utf-8')
        self.process = subprocess.Popen([sys.executable, '-m', 'modern.backend', '--no-log-file'],
                                        cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)
        self.lines = queue.Queue()
        self.raw = []
        self.stderr = []
        threading.Thread(target=self._read, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()
        self.counter = 0

    def _read(self):
        for line in self.process.stdout:
            self.raw.append(line)
            self.lines.put(json.loads(line))   # every stdout line must be JSON
        self.lines.put(None)

    def _read_err(self):
        for line in self.process.stderr:
            self.stderr.append(line)

    def send(self, method, params=None, session=None, identity=None):
        self.counter += 1
        identity = identity or 'r-%d' % self.counter
        request = {'id': identity, 'method': method, 'params': params or {}}
        if session:
            request['session'] = session
        self.write(json.dumps(request))
        return identity

    def write(self, text):
        self.process.stdin.write(text + '\n')
        self.process.stdin.flush()

    def next(self, timeout=120):
        message = self.lines.get(timeout=timeout)
        assert message is not None, 'backend exited:\n' + ''.join(self.stderr[-30:])
        return message

    def until(self, predicate, timeout=300):
        seen = []
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            message = self.next(timeout=deadline - time.monotonic())
            seen.append(message)
            if predicate(message):
                return message, seen
        raise TimeoutError(seen)

    def response(self, identity, timeout=120):
        message, seen = self.until(lambda m: m.get('id') == identity and ('result' in m or 'error' in m),
                                   timeout)
        return message

    def close(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(10)


@pytest.fixture
def backend():
    proc = Backend()
    yield proc
    proc.close()


def test_requests_responses_and_shutdown(backend):
    info = backend.response(backend.send('runtime.info'))['result']
    assert info['protocol'] == 1 and 'drawing.insert' in info['methods']
    state = backend.response(backend.send('project.open', {'path': SAMPLE}))['result']
    assert state['session'] == 'main' and not state['dirty']
    identity = backend.send('shutdown')
    assert backend.response(identity)['result'] is True
    assert backend.process.wait(30) == 0


def test_invalid_requests_get_structured_errors(backend):
    backend.write('this is not json')
    assert backend.next()['error']['code'] == 'INVALID_REQUEST'
    backend.write(json.dumps({'method': 'runtime.info'}))
    message = backend.next()
    assert message['id'] is None and message['error']['field'] == 'id'
    backend.write(json.dumps({'id': 'x1', 'method': 'runtime.info', 'params': []}))
    assert backend.response('x1')['error']['code'] == 'INVALID_REQUEST'
    backend.write(json.dumps({'id': 'x' * 101, 'method': 'runtime.info'}))
    assert backend.next()['error']['code'] == 'INVALID_REQUEST'
    error = backend.response(backend.send('no.such.method'))['error']
    assert error['code'] == 'INVALID_REQUEST' and error['field'] == 'method'
    error = backend.response(backend.send('project.state', session='closed-session'))['error']
    assert error['code'] == 'NOT_FOUND'
    error = backend.response(backend.send('project.open', {'path': os.path.join(ROOT, 'missing.gepro')}))['error']
    assert error['code'] == 'FILE_ERROR'
    # The backend is still serving
    assert backend.response(backend.send('runtime.info'))['result']['protocol'] == 1


def test_queries_are_answered_while_an_analysis_runs(backend):
    backend.response(backend.send('project.open', {'path': SAMPLE}))
    start = backend.send('analysis.start', {'settings': {'pf_method': 'Time series'}, 'rules_check': True})
    job = backend.response(start)['result']
    assert job['status'] in ('queued', 'running')
    queries = [backend.send('project.state'), backend.send('drawing.sheets'), backend.send('history.state')]
    answered = set()
    finished = None
    seen = []
    while finished is None:
        message = backend.next(timeout=300)
        seen.append(message)
        if message.get('id') in queries:
            answered.add(message['id'])
        if message.get('event') == 'job_finished' and message.get('job') == job['job']:
            finished = message
    # All queries were answered before the analysis finished
    assert answered == set(queries)
    assert finished['status'] == 'finished'
    progress = [m for m in seen if m.get('event') == 'progress' and m.get('job') == job['job']]
    assert progress and progress[-1]['fraction'] <= 1
    results = backend.response(backend.send('analysis.results', {'nodes': False}))['result']
    assert results['summary']['completed'] and results['elements']
    # Library prints (pandapower diagnostics) went to stderr, not the protocol
    assert any('PANDAPOWER DIAGNOSTIC' in line for line in backend.stderr)


def test_commands_emit_changed_events(backend):
    backend.response(backend.send('project.open', {'path': SAMPLE}))
    sheet = backend.response(backend.send('drawing.sheets'))['result'][0]['uid']
    identity = backend.send('drawing.insert', {'sheet': sheet, 'code': 'element_load', 'x': 5000, 'y': 5000})
    event, seen = backend.until(lambda m: m.get('event') == 'changed')
    assert event['changes'][0]['kind'] == 'element_added' and event['source'] == 'desktop'
    response = next((m for m in seen if m.get('id') == identity), None) or backend.response(identity)
    assert response['result']['revision'] == event['revision']
    assert response['result']['label'] == 'Insert element(s) at None'


def test_end_of_input_stops_the_backend(backend):
    backend.response(backend.send('runtime.info'))
    backend.process.stdin.close()
    assert backend.process.wait(30) == 0
