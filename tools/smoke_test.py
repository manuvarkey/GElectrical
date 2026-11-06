#!/usr/bin/env python3
"""Headless-ish end-to-end smoke test for GElectrical.

Opens each sample project, runs the full analysis pipeline (diagnostics,
power flow, short circuit, rules check) and exports JSON/PDF report/drawing
into a temporary folder. The main window is constructed but never shown, so
a display (or Windows desktop session) is still required for GTK.

Usage:
    pixi run smoke                       # all sample_files/**/*.gepro
    pixi run smoke path/to/project.gepro # specific project(s)
    pixi run smoke --keep                # keep output folder for inspection
"""

import glob
import logging
import os
import sys
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gio, GdkPixbuf

from gelectrical import MainWindow, misc
from gelectrical.view.analysis import AnalysisSettingsDialog

log = logging.getLogger('smoke_test')


def check_environment():
    """Fail early on GTK runtime gaps that otherwise abort the process."""
    if Gio.SettingsSchemaSource.get_default() is None or \
            Gio.SettingsSchemaSource.get_default().lookup('org.gtk.Settings.FileChooser', True) is None:
        raise RuntimeError('GSettings schemas not compiled (GtkFileChooser would abort)')
    if 'svg' not in [f.get_name() for f in GdkPixbuf.Pixbuf.get_formats()]:
        raise RuntimeError('gdk-pixbuf svg loader not registered')


def run_project(filename, out_root):
    window = MainWindow()
    try:
        # Construct (without running) dialogs that use GtkFileChooser
        sim = window.project.get_project_fields(page='Simulation')
        AnalysisSettingsDialog(window.window, sim, out_root).dialog.destroy()
        if not window.open_project(filename):
            raise RuntimeError('open_project returned False')
        project = window.project
        sim = project.get_project_fields(page='Simulation')

        project.setup_base_model()
        project.build_power_model()
        if project.run_diagnostics() == misc.ERROR:
            raise RuntimeError('Diagnostics returned critical errors')
        if sim['pf_method']['value'] == 'Time series':
            project.run_powerflow_timeseries()
        else:
            project.run_powerflow(sim['pf_method']['value'])
        project.run_sym_sccalc()
        project.run_linetoground_sccalc()
        project.update_results()
        project.run_rulescheck()

        folder = os.path.join(out_root, os.path.splitext(os.path.basename(filename))[0])
        os.makedirs(folder, exist_ok=True)
        settings = {'powerflow': True, 'sc_sym': True, 'sc_gf': True}
        project.export_json(misc.posix_path(folder, 'network.json'))
        project.export_pdf_report(folder, settings)
        project.export_drawing(misc.posix_path(folder, 'drawing.pdf'))
        outputs = sorted(os.listdir(folder))
        if 'report.pdf' not in outputs and not any(f.endswith('.pdf') for f in outputs):
            raise RuntimeError('No PDF output generated: %s' % outputs)
        return outputs
    finally:
        window.window.destroy()


def main(argv):
    logging.basicConfig(level=logging.WARNING,
                        format='%(levelname)s - %(name)s - %(message)s')
    check_environment()
    keep = '--keep' in argv
    files = [a for a in argv if not a.startswith('--')]
    if not files:
        files = sorted(glob.glob(os.path.join(ROOT, 'sample_files', '**', '*.gepro'),
                                 recursive=True))

    out_root = tempfile.mkdtemp(prefix='gelectrical_smoke_')
    failures = 0
    for filename in files:
        name = os.path.relpath(filename, ROOT)
        try:
            outputs = run_project(os.path.abspath(filename), out_root)
            print('PASS', name, '->', ', '.join(outputs))
        except Exception:
            failures += 1
            print('FAIL', name)
            traceback.print_exc()

    print('\n%d/%d projects passed. Output: %s' % (len(files) - failures, len(files), out_root))
    if not keep and failures == 0:
        import shutil
        shutil.rmtree(out_root, ignore_errors=True)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
