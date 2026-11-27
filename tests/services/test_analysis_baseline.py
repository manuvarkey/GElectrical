"""Analysis through the services equals the regression baseline (M4).

Each baseline project is opened with ``project.open`` and analysed with
``analysis.start`` in the ``pf_bal`` mode of the baseline (diagnostics,
balanced power flow, symmetric and line-to-ground short circuit, rules
check). The element and node results of the analysed copy are captured with
the baseline tools and compared with ``tests/baseline/<project>/pf_bal`` with
the documented tolerances (unchanged). The typed results returned by
``analysis.results`` must carry exactly the values of the analysed copy.
Projects whose baseline run stops (critical diagnostics, a failing short
circuit) must stop the same way.
"""

import os
import sys
import types

import pytest

from modern.backend.protocol import json_safe

from conftest import ROOT, wait_job

sys.path.insert(0, os.path.join(ROOT, 'tools', 'baseline'))
import canonical  # noqa: E402
import capture  # noqa: E402

BASELINE = os.path.join(ROOT, 'tests', 'baseline')
PROJECTS = {capture.project_name(f): f for f in capture.default_projects()}
NAMES = sorted(n for n in PROJECTS if os.path.isdir(os.path.join(BASELINE, n, 'pf_bal')))
PF_BAL = {'diagnostics': True, 'powerflow': True, 'pf_method': 'Power flow', 'three_phase': False,
          'sc_sym': True, 'sc_gf': True}


def baseline(name, artefact):
    return canonical.read_json(os.path.join(BASELINE, name, 'pf_bal', artefact))


def analysed_copy_state(runtime):
    """Baseline-format results of the analysed copy (read on the owner thread)"""
    from gelectrical.core import constants

    def read():
        state = runtime.get_session().analysis
        project = state.project
        fake = types.SimpleNamespace(project=project, misc=types.SimpleNamespace(
            DISPLAY_ELEMENT_CODES=constants.DISPLAY_ELEMENT_CODES))
        fake.elements = lambda: ((((k1, k2), e) for k1, d in enumerate(project.drawing_models)
                                  for k2, e in enumerate(d.elements)))
        results = canonical.canon(capture.results_state(fake))
        nodes = canonical.canon(capture.node_results_state(fake))
        values = {}
        for (k1, k2), element in fake.elements():
            uid = getattr(element, 'uid', None)
            if uid and element.res_fields and element.code not in constants.DISPLAY_ELEMENT_CODES:
                values[uid] = {code: field.get('value') for code, field in element.res_fields.items()}
        return results, nodes, values
    return runtime.run_on_owner(read).result()


def _messages(data):
    """(category, severity, text, element count) of baseline messages"""
    out = []
    for category, items in (data or {}).items():
        for head, links in items:
            severity = head.get('type', 'info') if isinstance(head, dict) else 'info'
            text = head['message'] if isinstance(head, dict) else head
            count = sum(len(ids) for kind, ids in links if kind != 'node')
            nodes = sum(len(ids) for kind, ids in links if kind == 'node')
            out.append((category, severity, text, count, nodes))
    return sorted(out)


def _dto_messages(messages):
    return sorted((m['category'], m['severity'], m['text'], len(m['uids']), len(m['nodes'])) for m in messages)


@pytest.mark.parametrize('name', NAMES)
def test_service_analysis_matches_baseline(runtime, name):
    status = baseline(name, 'status.json')
    runtime.call('project.open', {'path': PROJECTS[name]})
    job = runtime.call('analysis.start', {'settings': PF_BAL, 'rules_check': True})
    job = wait_job(runtime, job['job'])

    if status.get('stopped'):
        # Critical diagnostics: the run stops with the messages recorded
        assert job['status'] == 'finished'
        summary = runtime.call('analysis.status')['results']
        assert summary['error'] == 'Diagnostics run returned critical errors'
        assert not summary['completed']
        return
    if not status['completed']:
        failed = [s for s in status['steps'] if not s['ok']][0]
        assert job['status'] == 'failed', job
        exception = failed['error'].split(':')[0]
        assert job['error']['message'].startswith(exception), (job['error'], failed['error'])
        return

    assert job['status'] == 'finished', job
    summary = runtime.call('analysis.status')['results']
    assert summary['completed'] and not summary['stale'] and summary['rules_checked']
    results, nodes, values = analysed_copy_state(runtime)
    failures = canonical.compare(results, baseline(name, 'results.json'), 'results.json')
    failures += canonical.compare(nodes, baseline(name, 'node_results.json'), 'node_results.json')
    assert not failures, '\n'.join(failures[:40])

    # The typed results are the values of the analysed copy
    dto = runtime.call('analysis.results')
    assert set(dto['elements']) == set(values)
    for uid, records in dto['elements'].items():
        got = {r['code']: r['value'] for r in records}
        assert got == json_safe(values[uid]), uid
    assert len(dto['nodes']) == len(baseline(name, 'node_results.json'))
    assert _dto_messages(dto['rules']) == _messages(baseline(name, 'rules.json'))


def test_results_become_stale_after_an_edit(runtime):
    runtime.call('project.open', {'path': PROJECTS['cov_radial_lv']})
    job = wait_job(runtime, runtime.call('analysis.start', {'settings': PF_BAL})['job'])
    assert job['status'] == 'finished'
    assert runtime.call('analysis.status')['results']['stale'] is False
    sheet = runtime.call('project.state')['sheets'][0]['uid']
    uid = runtime.call('drawing.sheet', {'sheet': sheet})['elements'][0]['uid']
    runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'EDITED'}})
    assert runtime.call('analysis.status')['results']['stale'] is True
    # The live document never receives node display elements (E09)
    codes = [e['code'] for e in runtime.call('drawing.sheet', {'sheet': sheet})['elements']]
    assert 'element_display_node' not in codes
    runtime.call('analysis.clear')
    assert runtime.call('analysis.status')['results'] is None


def test_analysis_can_be_cancelled(runtime, events):
    runtime.call('project.open', {'path': PROJECTS['sample__sample']})
    job = runtime.call('analysis.start', {'settings': dict(PF_BAL, pf_method='Time series')})
    runtime.call('analysis.cancel', {'job': job['job']})
    job = wait_job(runtime, job['job'])
    assert job['status'] in ('cancelled', 'finished')
    if job['status'] == 'cancelled':
        assert job['error']['code'] == 'CANCELLED'
        assert runtime.call('analysis.status')['results'] is None
    finished = [e for e in events if e['event'] == 'job_finished']
    assert finished and finished[-1]['job'] == job['job']


def test_exports_run_as_jobs_without_changing_the_document(runtime, tmp_path):
    runtime.call('project.open', {'path': PROJECTS['sample__sample']})
    revision = runtime.call('project.state')['revision']
    # Drawing without results: from the committed snapshot
    job = wait_job(runtime, runtime.call('export.drawing_pdf', {'path': str(tmp_path / 'plain')})['job'])
    assert job['status'] == 'finished' and job['result']['with_results'] is False
    assert (tmp_path / 'plain.pdf').stat().st_size > 0
    # Analysis-based exports need current results
    error = None
    try:
        runtime.call('export.network_json', {'path': str(tmp_path / 'net.json')})
    except Exception as exc:
        error = exc
    assert getattr(error, 'code', None) == 'NOT_FOUND'
    assert wait_job(runtime, runtime.call('analysis.start', {})['job'])['status'] == 'finished'
    for method, params, produced in (
            ('export.drawing_pdf', {'path': str(tmp_path / 'drawing.pdf')}, ['drawing.pdf']),
            ('export.network_json', {'path': str(tmp_path / 'net.json')}, ['net.json']),
            ('export.report', {'folder': str(tmp_path)}, ['report.html', 'report.pdf'])):
        job = wait_job(runtime, runtime.call(method, params)['job'])
        assert job['status'] == 'finished', (method, job)
        for name in produced:
            assert (tmp_path / name).stat().st_size > 0, name
    assert runtime.call('project.state')['revision'] == revision
    assert runtime.call('project.state')['dirty'] is False


def test_analysis_settings_are_saved_to_the_project(runtime):
    """Owner decision 2026-11-27: like the legacy dialog, the settings of a run
    are written to the Simulation settings (one undo entry when they change)"""
    runtime.call('project.open', {'path': PROJECTS['cov_radial_lv']})
    settings = dict(PF_BAL, pf_method='Time series', sc_gf=False)
    job = runtime.call('analysis.start', {'settings': settings})
    history = runtime.call('history.state')
    assert history['undo_text'] == 'Undo Update analysis settings' and history['undo_count'] == 1
    sim = runtime.call('project.settings')['pages']['Simulation']['values']
    assert (sim['pf_method'], sim['power_flow_3ph'], sim['run_sc_gf']) == ('Time series', False, False)
    assert runtime.call('project.state')['dirty']
    job = wait_job(runtime, job['job'])
    assert job['status'] == 'finished'
    summary = runtime.call('analysis.status')['results']
    assert not summary['stale'] and summary['settings']['pf_method'] == 'Time series'
    # Same settings again: nothing to record
    wait_job(runtime, runtime.call('analysis.start', {'settings': settings})['job'])
    assert runtime.call('history.state')['undo_count'] == 1
    runtime.call('history.undo')
    assert runtime.call('project.settings')['pages']['Simulation']['values']['pf_method'] != 'Time series'
