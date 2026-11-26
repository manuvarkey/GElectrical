"""Drive the legacy GTK-coupled GElectrical code for baseline capture.

Read-only with respect to the engine: this module only calls existing
``MainWindow``/``ProjectModel``/element methods, in the same order the GTK
callbacks use them, and records what they produce. It never changes engine
behaviour. A display (or ``xvfb-run``) is required because importing any
``gelectrical`` module imports GTK and ``MainWindow`` builds real widgets.

Call :func:`isolate_environment` before importing this module's GTK parts
(``capture.py`` does this) so that user settings, themes and locale cannot
change captured values.
"""

import copy
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def isolate_environment(scratch_dir=None):
    """Point per-user directories at a scratch folder and fix theme/locale.

    Must run before ``gi``/``gelectrical`` are imported.
    """
    scratch_dir = scratch_dir or tempfile.mkdtemp(prefix='gelectrical_baseline_home_')
    for var, sub in (('XDG_DATA_HOME', 'data'), ('XDG_CONFIG_HOME', 'config'),
                     ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state')):
        path = os.path.join(scratch_dir, sub)
        os.makedirs(path, exist_ok=True)
        os.environ[var] = path
    # A dark GTK theme switches the drawing colours (program_state['dark_mode']).
    os.environ['GTK_THEME'] = 'Adwaita:light'
    os.environ['LC_ALL'] = 'C.UTF-8'
    os.environ['LANG'] = 'C.UTF-8'
    os.environ.setdefault('NO_AT_BRIDGE', '1')
    os.environ['MPLBACKEND'] = 'Agg'
    return scratch_dir


def import_legacy():
    """Import GTK and the legacy application; return the modules used."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import Gtk  # noqa: F401
    import gelectrical
    from gelectrical import misc
    return gelectrical, misc


class LegacySession:
    """One legacy ``MainWindow`` with one project loaded."""

    def __init__(self):
        gelectrical, misc = import_legacy()
        self.misc = misc
        # D4: ProjectModel aliases these module globals. Restore pristine
        # copies before every window so that one capture cannot leak into
        # the next (harness isolation only; the engine is unchanged).
        if not hasattr(LegacySession, '_pristine'):
            LegacySession._pristine = (copy.deepcopy(misc.default_project_settings),
                                       copy.deepcopy(misc.DEFAULT_LOAD_PROFILE))
        settings, profiles = LegacySession._pristine
        misc.default_project_settings.clear()
        misc.default_project_settings.update(copy.deepcopy(settings))
        misc.DEFAULT_LOAD_PROFILE.clear()
        misc.DEFAULT_LOAD_PROFILE.update(copy.deepcopy(profiles))

        self.window = gelectrical.MainWindow()
        self.project = self.window.project
        self.stack = self.window.stack
        self.messages = []
        original_update = self.project.diagnostics_view.update

        def spy_update(data, *args, **kwargs):
            self.messages.append(copy.deepcopy(data))
            return original_update(data, *args, **kwargs)

        self.project.diagnostics_view.update = spy_update

    # -- lifecycle ---------------------------------------------------------

    def open(self, filename):
        if not self.window.open_project(os.path.abspath(filename)):
            raise RuntimeError('open_project returned False for %s' % filename)

    def save(self, filename):
        """Save through the legacy ``MainWindow.on_save`` code path."""
        self.window.filename = os.path.abspath(filename)
        self.window.program_state['filename'] = self.window.filename
        self.window.project_active = True
        self.window.on_save(None)

    def close(self):
        self.window.window.destroy()

    # -- accessors ---------------------------------------------------------

    @property
    def sim(self):
        return self.project.get_project_fields(page='Simulation')

    def elements(self):
        """Yield ((page, index), element) for every element in every sheet."""
        for page, drawing_model in enumerate(self.project.drawing_models):
            for index, element in enumerate(drawing_model.elements):
                yield (page, index), element
