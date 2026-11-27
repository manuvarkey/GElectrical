# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Service method registry. The canonical method list of the protocol is
generated from it (``python -m modern.backend --write-docs``).

Kinds:

* ``query``: read-only, runs on the owner thread against one session.
* ``command``: mutation of one session through :meth:`Session.execute`;
  accepts the generic parameters ``preview`` and ``if_revision`` and returns
  ``{"value", "changes", "label", "revision", "preview"}``.
* ``session``: acts on a session without the command contract (open, save,
  undo, redo, analysis jobs).
* ``runtime``: needs no session (session management, catalogue, settings).
"""

import inspect
from dataclasses import dataclass
from typing import Callable, Optional

from .protocol import invalid

KINDS = ('query', 'command', 'session', 'runtime')

METHODS = {}


@dataclass
class Method:
    name: str
    kind: str
    func: Callable
    summary: str
    label: Optional[object] = None   # command label fallback (str or callable)

    def params(self):
        """Public parameter names and defaults (``ctx`` excluded)"""
        out = []
        for name, param in list(inspect.signature(self.func).parameters.items())[1:]:
            default = None if param.default is inspect.Parameter.empty else param.default
            out.append((name, param.default is inspect.Parameter.empty, default))
        if self.kind == 'command':
            out += [('preview', False, False), ('if_revision', False, None)]
        return out

    def bind(self, ctx, params):
        try:
            inspect.signature(self.func).bind(ctx, **params)
        except TypeError as exc:
            raise invalid('Invalid parameters for %s: %s' % (self.name, exc)) from None


def _register(name, kind, label=None):
    def decorator(func):
        if name in METHODS:
            raise ValueError('Duplicate method %s' % name)
        doc = inspect.getdoc(func) or ''
        METHODS[name] = Method(name, kind, func, doc.split('\n\n')[0].replace('\n', ' '), label)
        return func
    return decorator


def query(name):
    return _register(name, 'query')


def command(name, label=None):
    return _register(name, 'command', label)


def session_method(name):
    return _register(name, 'session')


def runtime_method(name):
    return _register(name, 'runtime')


def load_services():
    """Import the service modules (registration side effect)"""
    from .services import (sessions, project, catalog, drawing, library, loadprofiles,  # noqa: F401
                           protection, analysis, export, history, settings)
    return METHODS


def method_table_markdown():
    """Markdown table of all methods (generated documentation)"""
    load_services()
    lines = ['| Method | Kind | Parameters | Summary |', '| --- | --- | --- | --- |']
    for name in sorted(METHODS):
        method = METHODS[name]
        params = ', '.join(('`%s`' % p) if required else ('`%s?`' % p) for p, required, _ in method.params())
        lines.append('| `%s` | %s | %s | %s |' % (name, method.kind, params or '-', method.summary.replace('|', '\\|')))
    return '\n'.join(lines) + '\n'


DOC_BEGIN = '<!-- BEGIN GENERATED METHOD TABLE -->'
DOC_END = '<!-- END GENERATED METHOD TABLE -->'


def write_method_table(path):
    """Replace the generated table between the markers of ``path``"""
    with open(path, encoding='utf-8') as fp:
        text = fp.read()
    head, rest = text.split(DOC_BEGIN, 1)
    _old, tail = rest.split(DOC_END, 1)
    with open(path, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(head + DOC_BEGIN + '\n' + method_table_markdown() + DOC_END + tail)
