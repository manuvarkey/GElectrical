"""Symbols (M2 step 4): extents without rendering, deterministic, headless."""

import glob
import os

import cairo
import pytest

from gelectrical import persistence, undo
from gelectrical.core import constants
from gelectrical.model.project import ProjectModel
from gelectrical.symbols import text

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECTS = sorted(glob.glob(os.path.join(ROOT, 'sample_files', '**', '*.gepro'), recursive=True)) + \
    sorted(glob.glob(os.path.join(ROOT, 'tests', 'projects', 'cov_*.gepro')))


def test_default_backend_is_cairo():
    assert text.get_text_backend().name == 'cairo'


def test_measure_multiline_and_empty():
    w1, h1 = text.measure_text('AB', 'osifont', 7, constants.SCHEM_FONT_WEIGHT)
    w2, h2 = text.measure_text('AB\nAB', 'osifont', 7, constants.SCHEM_FONT_WEIGHT)
    w0, h0 = text.measure_text('', 'osifont', 7, constants.SCHEM_FONT_WEIGHT)
    assert w1 > 0 and w2 == w1 and h2 == 2*h1 and w0 == 0 and h0 == h1


@pytest.mark.parametrize('filename', PROJECTS, ids=os.path.basename)
def test_dimensions_without_render_equal_rendered(filename):
    project = ProjectModel(stack=undo.Stack())
    persistence.load_project(project, filename)
    elements = [e for d in project.drawing_models for e in d.elements]
    before = [e.get_dimensions() for e in elements]
    assert all(w >= 0 and h >= 0 for (_, _, w, h) in before)
    assert any(w > 0 for (_, _, w, _) in before)
    surface = cairo.PDFSurface(None, 100, 100)
    context = cairo.Context(surface)
    for drawing_model in project.drawing_models:
        drawing_model.export_drawing(context)
    after = [e.get_dimensions() for e in elements]
    assert before == after
