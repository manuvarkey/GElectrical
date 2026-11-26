"""Headless text metrics vs PangoCairo (M2 step 4 decision rule).

The headless Cairo text backend must reproduce the element extents of the
legacy PangoCairo measurement within one grid unit. Needs PyGObject/Pango
(no display); skipped when unavailable.
"""

import glob
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCRIPT = r'''
import glob, json, os, sys
sys.path.insert(0, ROOT)
from gelectrical import persistence, undo
from gelectrical.model.project import ProjectModel
from gelectrical.symbols import text

def extents(backend):
    text.set_text_backend(backend)
    out = {}
    for filename in FILES:
        project = ProjectModel(stack=undo.Stack())
        persistence.load_project(project, filename)
        for page, drawing_model in enumerate(project.drawing_models):
            for index, element in enumerate(drawing_model.elements):
                element.extents_stale = True
                out['%s:%d:%d:%s' % (os.path.basename(filename), page, index, element.code)] = \
                    list(element.get_dimensions())
    return out

from gelectrical.symbols.text import CairoTextBackend
cairo_ext = extents(CairoTextBackend())
from gelectrical.gtk.pango_text import PangoTextBackend
pango_ext = extents(PangoTextBackend())
print(json.dumps({'cairo': cairo_ext, 'pango': pango_ext}))
'''


def _files():
    files = sorted(glob.glob(os.path.join(ROOT, 'sample_files', '**', '*.gepro'), recursive=True))
    files += sorted(f for f in glob.glob(os.path.join(ROOT, 'tests', 'projects', '**', '*.gepro'),
                                         recursive=True) if os.sep + 'malicious' + os.sep not in f)
    return files


def measure():
    import json
    code = 'ROOT = %r\nFILES = %r\n' % (ROOT, _files()) + SCRIPT
    proc = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        if "No module named 'gi'" in proc.stderr or 'Namespace Pango not available' in proc.stderr:
            pytest.skip('PyGObject/Pango not available')
        raise AssertionError(proc.stderr[-3000:])
    return json.loads(proc.stdout.strip().splitlines()[-1])


def test_cairo_extents_within_one_grid_unit_of_pango():
    from gelectrical.core.constants import GRID_WIDTH
    data = measure()
    assert data['cairo'].keys() == data['pango'].keys()
    worst = 0
    offenders = []
    for key, c in data['cairo'].items():
        p = data['pango'][key]
        diff = max(abs(a - b) for a, b in zip(c, p))
        worst = max(worst, diff)
        if diff > GRID_WIDTH:
            offenders.append((key, c, p))
    print('elements: %d, largest difference: %d drawing units' % (len(data['cairo']), worst))
    assert not offenders, offenders[:20]
