"""M2 acceptance: the engine imports without PyGObject (``gi`` blocked)."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ACCEPTANCE = ("import sys; sys.modules['gi'] = None; "
              "import gelectrical.model.project, gelectrical.analysis.pipeline, "
              "gelectrical.persistence.gepro, gelectrical.reports")


def test_acceptance_import_command():
    proc = subprocess.run([sys.executable, '-c', ACCEPTANCE], cwd=ROOT,
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr[-2000:]


def test_engine_modules_do_not_load_gtk():
    code = ("import sys; import gelectrical.model.project, gelectrical.analysis, "
            "gelectrical.persistence, gelectrical.reports, gelectrical.elementmodel.registry, "
            "gelectrical.symbols.render; "
            "bad = sorted(m for m in sys.modules if m == 'gi' or m.startswith('gi.') "
            "or m.startswith('gelectrical.gtk') or m == 'gelectrical.misc'); "
            "print(bad); sys.exit(1 if bad else 0)")
    proc = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr[-2000:]
