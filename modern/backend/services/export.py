# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Exports (jobs; they never change project state): drawing PDF, project
report (HTML + PDF), pandapower JSON and HTML, element graph.

Analysis-based exports use the stored analysis copy and require results of
the current revision. The drawing PDF uses the analysis copy when its results
are current (node markers and result labels drawn, as in the legacy app after
an analysis) and a copy of the committed snapshot otherwise.
"""

import os

from gelectrical.reports import export as reports

from .. import document
from ..protocol import ServiceError, FILE_ERROR
from ..registry import session_method
from .analysis import _state
from .common import require_bool, require_str


def _output_path(path, extension, field='path'):
    require_str(path, field, allow_empty=False, max_length=4096)
    if '\x00' in path:
        raise ServiceError(FILE_ERROR, 'Invalid path', field=field)
    path = os.path.abspath(path)
    if extension and not path.endswith(extension):
        path += extension
    if not os.path.isdir(os.path.dirname(path)):
        raise ServiceError(FILE_ERROR, 'Folder does not exist', field=field)
    return path


def _folder(path, field='folder'):
    require_str(path, field, allow_empty=False, max_length=4096)
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        raise ServiceError(FILE_ERROR, 'Folder does not exist', field=field)
    return path


def _analysis_job(ctx, kind, path, func):
    state = _state(ctx, require_fresh=True, require_completed=True)

    def work(job):
        job.report(0, 'Exporting %s...' % kind, kind)
        func(state.project, path)
        return {'path': path}

    return ctx.runtime.start_job(ctx.session, kind, work).summary()


@session_method('export.drawing_pdf')
def drawing_pdf(ctx, path, with_results=True):
    """Export all sheets to a vector PDF (job)"""
    path = _output_path(path, '.pdf')
    require_bool(with_results, 'with_results')
    session = ctx.session
    state = session.analysis
    use_analysis = (with_results and state is not None and state.project is not None
                    and state.revision == session.revision)
    snapshot = session.snapshot
    factory = session.project_factory()

    def work(job):
        job.report(0, 'Exporting drawing...', 'drawing_pdf')
        project = state.project if use_analysis else document.new_project_from(snapshot, factory)
        reports.export_drawing(project, path)
        return {'path': path, 'with_results': use_analysis}

    return ctx.runtime.start_job(session, 'drawing_pdf', work).summary()


@session_method('export.report')
def report(ctx, folder):
    """Export the project report (report.html, report.css, report.pdf) to a folder (job)"""
    folder = _folder(folder)
    state = _state(ctx, require_fresh=True, require_completed=True)
    # The analysis dialog options the report reads (legacy settings dict)
    options = {'diagnostics': state.settings.diagnostics, '3ph': state.three_phase,
               'powerflow': state.settings.powerflow, 'pf_method': state.settings.pf_method,
               'sc_sym': state.settings.sc_sym, 'sc_gf': state.settings.sc_gf,
               'export': True, 'folder': folder}
    return _analysis_job(ctx, 'report', folder,
                         lambda project, path: reports.export_pdf_report(project, path, options))


@session_method('export.network_json')
def network_json(ctx, path):
    """Export the pandapower network to JSON (job)"""
    return _analysis_job(ctx, 'network_json', _output_path(path, '.json'), reports.export_json)


@session_method('export.network_html')
def network_html(ctx, path):
    """Export the pandapower HTML report (job)"""
    return _analysis_job(ctx, 'network_html', _output_path(path, '.html'), reports.export_html_report)


@session_method('export.element_graph')
def element_graph(ctx, path):
    """Export the element graph HTML (job)"""
    return _analysis_job(ctx, 'element_graph', _output_path(path, '.html'), reports.export_element_graph)
