"""Regression baseline through the headless engine (milestone M2).

Every baseline project is captured with ``capture.py --headless`` (no GTK,
no display; PyGObject blocked) and compared with ``tests/baseline/`` with
the documented tolerances, unchanged. Differences from the legacy capture:

* GTK-only warnings (``PyGTKDeprecationWarning``) are not expected.
* Drawings: the headless engine draws text with the Cairo toy API, the
  baseline was drawn with PangoCairo. Raster comparison therefore runs only
  for captures made with ``GELECTRICAL_TEXT_BACKEND=pango`` (PangoCairo text
  without GTK); for Cairo text the measured difference is reported as a
  warning. The owner decides on a raster limit for Cairo text (validation
  log, M2 entry); no tolerance is widened here.

Set ``GELECTRICAL_HEADLESS_CAPTURE=/path`` to reuse an existing capture.
"""

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
def headless_root():
    root = os.environ.get('GELECTRICAL_HEADLESS_CAPTURE')
    if root and os.path.isdir(root) and os.listdir(root):
        return root
    root = root or tempfile.mkdtemp(prefix='gelectrical_headless_capture_')
    _, failures = capture.capture_all(capture.default_projects(), root, headless=True)
    if failures:
        pytest.fail('headless capture failed:\n' + '\n'.join('%s\n%s' % f for f in failures))
    return root


def _environment(root):
    return canonical.read_json(os.path.join(root, 'environment.json'))


def test_headless_capture_did_not_load_gtk(headless_root):
    env = _environment(headless_root)
    if env.get('text_backend') == 'pango':
        pytest.skip('diagnostic capture with PangoCairo text (PyGObject importable)')
    assert 'gtk' not in env


@pytest.mark.parametrize('project', BASELINE_PROJECTS)
def test_headless_project_matches_baseline(headless_root, project):
    actual = os.path.join(headless_root, project)
    assert os.path.isdir(actual), 'project not captured'
    pango_text = _environment(headless_root).get('text_backend') == 'pango'
    failures, notes = compare.compare_project(
        actual, os.path.join(BASELINE, project),
        compare_drawings=pango_text and compare.fonts_match(headless_root, BASELINE),
        headless=True)
    for note in notes:
        warnings.warn('%s: %s' % (project, note))
    assert not failures, '\n'.join(failures[:60])
