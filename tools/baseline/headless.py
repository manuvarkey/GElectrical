"""Drive the headless GElectrical engine for baseline capture (M2).

Same interface as ``legacy.py`` (``isolate_environment``, ``import_legacy``,
``LegacySession``) so that ``capture.py --headless`` runs every capture step
on the engine alone: no GTK, no display. PyGObject is blocked, so a GTK
import anywhere in the engine fails the capture.
"""

import copy
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def isolate_environment(scratch_dir=None):
    """Same isolation as the legacy capture (locale, Matplotlib backend).

    ``GELECTRICAL_TEXT_BACKEND=pango`` (diagnostics only) draws text with
    PangoCairo like the GTK application; PyGObject is then importable, but
    GTK itself is still not loaded."""
    import legacy
    scratch = legacy.isolate_environment(scratch_dir)
    if os.environ.get('GELECTRICAL_TEXT_BACKEND') == 'pango':
        if ROOT not in sys.path:
            sys.path.insert(0, ROOT)
        from gelectrical.gtk.pango_text import PangoTextBackend
        from gelectrical.symbols.text import set_text_backend
        set_text_backend(PangoTextBackend())
    else:
        sys.modules['gi'] = None
    return scratch


def import_legacy():
    """Return (None, misc-like namespace) built from the engine modules."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    if os.environ.get('GELECTRICAL_TEXT_BACKEND') != 'pango':
        sys.modules.setdefault('gi', None)
    from gelectrical.core import constants, style, undoable, fields
    ns = types.SimpleNamespace()
    for module in (constants, fields, undoable):
        for name in dir(module):
            if not name.startswith('__'):
                setattr(ns, name, getattr(module, name))
    # Style values are read live from gelectrical.core.style
    ns_class = type('EngineMisc', (types.SimpleNamespace,), {
        '__getattr__': lambda self, name: getattr(style, name)})
    misc = ns_class(**vars(ns))
    return None, misc


class LegacySession:
    """One headless ProjectModel with one project loaded."""

    def __init__(self):
        _, misc = import_legacy()
        self.misc = misc
        from gelectrical import undo
        from gelectrical.model.project import ProjectModel
        self.stack = undo.Stack()
        self.stack.savepoint()
        self.project = ProjectModel(stack=self.stack)
        self.messages = []

        def listener(event, **data):
            if event == 'diagnostics':
                self.messages.append(copy.deepcopy(data['results']))

        self.project.subscribe(listener)

    def open(self, filename):
        from gelectrical import persistence
        persistence.load_project(self.project, os.path.abspath(filename))
        self.stack.clear()
        self.stack.savepoint()

    def save(self, filename):
        from gelectrical import persistence
        persistence.save_project(self.project, os.path.abspath(filename))
        self.stack.savepoint()

    def close(self):
        pass

    @property
    def sim(self):
        return self.project.get_project_fields(page='Simulation')

    def elements(self):
        for page, drawing_model in enumerate(self.project.drawing_models):
            for index, element in enumerate(drawing_model.elements):
                yield (page, index), element
