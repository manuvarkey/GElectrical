"""analysis.pipeline (M2 step 7) on a sample project, headless."""

import os

import pytest

from gelectrical import analysis, persistence, undo, reports
from gelectrical.model.project import ProjectModel

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SAMPLE = os.path.join(ROOT, 'sample_files', 'sample.gepro')


@pytest.fixture(scope='module')
def analysed():
    project = ProjectModel(stack=undo.Stack())
    persistence.load_project(project, SAMPLE)
    result = analysis.run_analysis(project)
    return project, result


def test_pipeline_runs_all_steps(analysed):
    project, result = analysed
    assert result.completed and result.rules_check_ready
    assert [s.name for s in result.steps][:3] == ['setup_base_model', 'build_power_model',
                                                  'run_diagnostics']
    assert result.diagnostics is not None
    nodes = [e for d in project.drawing_models for e in d.elements if e.code == 'element_display_node']
    assert nodes and any(e.res_fields for e in nodes)


def test_rules_check_returns_messages(analysed):
    project, _ = analysed
    assert isinstance(analysis.run_rules_check(project), dict)


def test_exports(analysed, tmp_path):
    project, _ = analysed
    reports.export_json(project, str(tmp_path / 'network.json'))
    reports.export_drawing(project, str(tmp_path / 'drawing.pdf'))
    reports.export_pdf_report(project, str(tmp_path), {'powerflow': True, 'sc_sym': True, 'sc_gf': True})
    for name in ('network.json', 'drawing.pdf', 'report.html', 'report.pdf'):
        assert (tmp_path / name).stat().st_size > 0


def test_unknown_method_rejected():
    project = ProjectModel()
    with pytest.raises(ValueError):
        analysis.run_analysis(project, analysis.AnalysisSettings(pf_method='bogus'))
