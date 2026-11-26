"""Regression baseline (milestone M1).

A fresh capture of every sample and coverage project is compared with the
committed baseline in ``tests/baseline/`` using the tolerances of
``docs/migration/regression-baseline.md`` (implemented in
``tools/baseline/canonical.py``).

The capture builds the legacy GTK ``MainWindow``, so a display is required:
run ``xvfb-run -a pixi run -e test test`` on headless Linux.

Set ``GELECTRICAL_BASELINE_CAPTURE=/path`` to compare an existing capture
instead of capturing again (the folder is created and filled if missing).
"""

import json
import os
import sys
import tempfile
import warnings

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, 'tests', 'baseline')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'baseline'))

import canonical  # noqa: E402
import capture  # noqa: E402
import compare  # noqa: E402

BASELINE_PROJECTS = sorted(d for d in os.listdir(BASELINE)
                           if os.path.isdir(os.path.join(BASELINE, d)))


@pytest.fixture(scope='session')
def capture_root():
    root = os.environ.get('GELECTRICAL_BASELINE_CAPTURE')
    if root and os.path.isdir(root) and os.listdir(root):
        return root
    root = root or tempfile.mkdtemp(prefix='gelectrical_baseline_capture_')
    _, failures = capture.capture_all(capture.default_projects(), root)
    if failures:
        pytest.fail('capture failed:\n' + '\n'.join('%s\n%s' % f for f in failures))
    return root


def test_project_set_matches_baseline():
    expected = sorted(capture.project_name(p) for p in capture.default_projects())
    assert BASELINE_PROJECTS == expected, 'tests/baseline out of sync with project files'


def test_environment(capture_root):
    diffs = compare.environment_differences(capture_root, BASELINE)
    if diffs:
        # Informational: tolerances apply to the same environment.
        warnings.warn('Environment differs from baseline:\n' + '\n'.join(diffs))


@pytest.mark.parametrize('project', BASELINE_PROJECTS)
def test_project_matches_baseline(capture_root, project):
    actual = os.path.join(capture_root, project)
    assert os.path.isdir(actual), 'project not captured'
    failures, notes = compare.compare_project(
        actual, os.path.join(BASELINE, project),
        compare_drawings=compare.fonts_match(capture_root, BASELINE))
    for note in notes:
        warnings.warn('%s: %s' % (project, note))
    assert not failures, '\n'.join(failures[:60])


@pytest.mark.parametrize('project', BASELINE_PROJECTS)
def test_roundtrip_equals_model(capture_root, project):
    """Saved then reloaded model equals the loaded model (canonical form)."""
    data = canonical.read_json(os.path.join(capture_root, project, 'roundtrip.json'))
    if data != {'equal_to_model': True}:
        model = canonical.read_json(os.path.join(capture_root, project, 'model.json'))
        diffs = canonical.compare(data, model, 'roundtrip.json')
        assert not diffs, '\n'.join(diffs[:40])


def _codes_in_baseline():
    codes = set()
    for project in BASELINE_PROJECTS:
        model = canonical.read_json(os.path.join(BASELINE, project, 'model.json'))
        for sheet in model['sheets']:
            codes.update(e['code'] for e in sheet['elements'])
        undo = canonical.read_json(os.path.join(BASELINE, project, 'undo.json'))
        for entry in undo['actions']:
            for sheet in entry['model']['sheets']:
                codes.update(code for code, _ in sheet)
    return codes


def test_every_registered_element_code_is_covered():
    env = canonical.read_json(os.path.join(BASELINE, 'environment.json'))
    registered = set(env['registered_element_codes'])
    missing = sorted(registered - _codes_in_baseline())
    assert not missing, 'registered codes without a baseline project: %s' % missing


def test_every_analysis_mode_completes_somewhere():
    completed = {name: [] for name, _, _ in capture.MODES}
    for project in BASELINE_PROJECTS:
        for name in completed:
            path = os.path.join(BASELINE, project, name, 'status.json')
            if os.path.exists(path) and json.load(open(path, encoding='utf-8')).get('completed'):
                completed[name].append(project)
    assert all(completed.values()), completed
