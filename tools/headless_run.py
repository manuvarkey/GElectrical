#!/usr/bin/env python3
"""Run GElectrical headless: open a project, analyse, export (M2 deliverable).

No GTK and no display: the engine is imported with PyGObject blocked, so an
accidental GTK import fails loudly.

Usage::

    pixi run headless path/to/project.gepro [--out DIR] [--pf-method METHOD]
        [--three-phase|--balanced] [--no-diagnostics] [--no-rules]
        [--no-report] [--no-drawing] [--save copy.gepro]

Exit status 0 when every requested step succeeded.
"""

import argparse
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.modules.setdefault('gi', None)  # headless: GTK must not be imported

from gelectrical.model.project import ProjectModel  # noqa: E402
from gelectrical.persistence import load_project, save_project  # noqa: E402
from gelectrical.analysis import (AnalysisSettings, AnalysisError, run_analysis,  # noqa: E402
                                  run_rules_check)
from gelectrical import reports  # noqa: E402
from gelectrical.core import constants  # noqa: E402


def _message_count(messages):
    """Count messages by type ({heading: [[{'message', 'type'}|str, data], ...]})"""
    counts = {}
    for entries in (messages or {}).values():
        for entry in entries:
            head = entry[0] if isinstance(entry, (list, tuple)) and entry else entry
            kind = head.get('type', 'info') if isinstance(head, dict) else 'info'
            counts[kind] = counts.get(kind, 0) + 1
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('project')
    parser.add_argument('--out', help='export folder (default: <project>_results)')
    parser.add_argument('--pf-method', choices=['Power flow', 'Power flow with diversity', 'Time series'],
                        help='power flow method (default: project setting)')
    phase = parser.add_mutually_exclusive_group()
    phase.add_argument('--three-phase', action='store_true', help='asymmetric power flow')
    phase.add_argument('--balanced', action='store_true', help='balanced power flow')
    parser.add_argument('--no-diagnostics', action='store_true')
    parser.add_argument('--no-rules', action='store_true')
    parser.add_argument('--no-report', action='store_true')
    parser.add_argument('--no-drawing', action='store_true')
    parser.add_argument('--save', help='save the (loaded) project to this file')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING,
                        format='%(levelname)s - %(name)s - %(message)s')

    project = ProjectModel()
    load_project(project, args.project)
    summary = {'project': os.path.abspath(args.project), 'sheets': project.get_page_nos()}
    if args.save:
        save_project(project, args.save)
        summary['saved'] = os.path.abspath(args.save)

    sim = project.get_project_fields(page='Simulation')
    if args.three_phase:
        sim['power_flow_3ph']['value'] = True
    elif args.balanced:
        sim['power_flow_3ph']['value'] = False
    settings = AnalysisSettings.from_project(project)
    if args.pf_method:
        settings.pf_method = args.pf_method
    settings.diagnostics = not args.no_diagnostics
    summary['settings'] = dict(vars(settings), three_phase=bool(sim['power_flow_3ph']['value']))

    status = 0
    try:
        result = run_analysis(project, settings)
        summary['analysis'] = {'completed': result.completed,
                               'steps': [s.name for s in result.steps],
                               'diagnostics': _message_count(result.diagnostics)}
    except AnalysisError as exc:
        summary['analysis'] = {'completed': False, 'error': str(exc),
                               'diagnostics': _message_count(exc.result.diagnostics)}
        print(json.dumps(summary, indent=2))
        return 1

    if not args.no_rules and result.rules_check_ready:
        summary['rules'] = _message_count(run_rules_check(project))

    out = args.out or os.path.splitext(os.path.abspath(args.project))[0] + '_results'
    os.makedirs(out, exist_ok=True)
    exported = []
    reports.export_json(project, os.path.join(out, 'network.json'))
    exported.append('network.json')
    if not args.no_report:
        try:
            reports.export_pdf_report(project, out, {'powerflow': True, 'sc_sym': True, 'sc_gf': True})
            exported += ['report.html', 'report.pdf']
        except Exception as exc:  # report errors (e.g. D18) do not hide the analysis
            summary['report_error'] = '%s: %s' % (type(exc).__name__, exc)
            status = 1
    if not args.no_drawing:
        reports.export_drawing(project, os.path.join(out, 'drawing.pdf'))
        exported.append('drawing.pdf')
    summary['out'] = out
    summary['exported'] = exported
    print(json.dumps(summary, indent=2))
    return status


if __name__ == '__main__':
    sys.exit(main())
