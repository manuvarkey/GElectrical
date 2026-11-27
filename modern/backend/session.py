# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Document session: one open project with its history, revision, dirty
state, file path and analysis results (docs/architecture/backend.md
sections 4 and 5, ADR 0009).

Command contract (:meth:`Session.execute`):

1. ``if_revision`` is checked before any change (STALE_REVISION).
2. The command runs inside a transaction; nested commands join it.
3. Engine methods apply the change (``@undoable`` methods record their
   legacy label on the session's :class:`RecordingStack`).
4. On success the "after" snapshot is captured. If the document changed:
   one history entry, ``revision + 1``, a ``changed`` event.
5. On failure the "before" snapshot is restored; nothing is recorded.
6. ``preview=True`` runs the command, returns its result and change set and
   restores the "before" snapshot without touching history or revision.
"""

import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Any, List, Optional

from gelectrical.core.fields import new_program_settings
from gelectrical.model.project import ProjectModel

from . import document
from .protocol import ServiceError, STALE_REVISION, BACKEND_ERROR

log = logging.getLogger(__name__)

DEFAULT_HISTORY_LIMIT = 200


@dataclass
class HistoryEntry:
    label: str
    before: document.Snapshot
    after: document.Snapshot
    source: str = 'desktop'


class History:
    """Bounded linear undo history of snapshot pairs"""

    def __init__(self, limit=DEFAULT_HISTORY_LIMIT):
        self.limit = limit
        self.undos = deque()
        self.redos = []

    def push(self, entry):
        self.undos.append(entry)
        while len(self.undos) > self.limit:
            self.undos.popleft()
        self.redos = []

    def clear(self):
        self.undos.clear()
        self.redos = []

    def can_undo(self):
        return bool(self.undos)

    def can_redo(self):
        return bool(self.redos)

    def undo_text(self):
        return 'Undo ' + self.undos[-1].label if self.undos else None

    def redo_text(self):
        return 'Redo ' + self.redos[-1].label if self.redos else None

    def state(self):
        return {'can_undo': self.can_undo(), 'can_redo': self.can_redo(),
                'undo_text': self.undo_text(), 'redo_text': self.redo_text(),
                'undo_count': len(self.undos), 'redo_count': len(self.redos)}


@dataclass
class CommandResult:
    value: Any = None
    changes: List[dict] = field(default_factory=list)
    label: Optional[str] = None
    revision: int = 0
    preview: bool = False

    def to_dict(self):
        return {'value': self.value, 'changes': self.changes, 'label': self.label,
                'revision': self.revision, 'preview': self.preview}


class Session:
    """One open document"""

    def __init__(self, session_id, program_settings=None, history_limit=DEFAULT_HISTORY_LIMIT, emit=None):
        self.id = session_id
        self.program_settings = program_settings if program_settings is not None else new_program_settings()
        self.stack = document.RecordingStack()
        self.project = self.new_project()
        self.history = History(history_limit)
        self.path = None
        self.revision = 0
        self.emit = emit or (lambda message: None)
        self.analysis = None   # analysis.AnalysisState of the last finished analysis
        self._depth = 0
        self._current = document.capture(self.project)
        self._saved = self._current

    # -- document lifecycle ---------------------------------------------------

    def new_project(self):
        return ProjectModel(stack=self.stack, program_settings=self.program_settings['Defaults'])

    def project_factory(self):
        """Factory of detached projects (analysis and export copies)"""
        def factory():
            return ProjectModel(stack=document.RecordingStack(),
                                program_settings=self.program_settings['Defaults'])
        return factory

    def reset_document(self, loader=None, path=None):
        """Replace the document (new or open): history cleared, as today.
        ``loader(project)`` fills a fresh project; on failure nothing changes."""
        project = self.new_project()
        if loader is not None:
            loader(project)
        document.ensure_uids(project)
        document.refresh_derived(project)
        old = self._current
        self.project = project
        self.history.clear()
        self.analysis = None
        self.path = path
        self._current = document.capture(project)
        self._saved = self._current
        self.revision += 1
        self.stack.reset()
        self.emit_changed([{'kind': 'document'}], source='desktop')
        return old

    def mark_saved(self, path):
        self.path = path
        self._saved = self._current

    @property
    def dirty(self):
        return self._current is not self._saved

    @property
    def snapshot(self):
        """Snapshot of the committed state (immutable)"""
        return self._current

    # -- events ---------------------------------------------------------------

    def emit_changed(self, changes, source='desktop'):
        self.emit({'event': 'changed', 'session': self.id, 'revision': self.revision,
                   'changes': changes, 'source': source, 'dirty': self.dirty})

    # -- commands -------------------------------------------------------------

    def check_revision(self, if_revision):
        if if_revision is not None and if_revision != self.revision:
            raise ServiceError(STALE_REVISION,
                               'The project changed (revision %d, edit based on %d); retry' % (self.revision, if_revision),
                               details={'revision': self.revision})

    def execute(self, func, label=None, preview=False, if_revision=None, source='desktop'):
        """Run ``func()`` as one command; returns :class:`CommandResult`.

        ``label``: description used when the engine recorded no single legacy
        action label (a string, or a callable taking the recorded labels)."""
        if self._depth:
            # Nested command: join the outer transaction
            return CommandResult(value=func(), revision=self.revision)
        self.check_revision(if_revision)
        before = self._current
        self.stack.reset()
        self._depth += 1
        try:
            value = func()
            after = document.capture(self.project, previous=before)
        except BaseException:
            self._rollback(before)
            raise
        finally:
            self._depth -= 1
        texts = self.stack.take_texts()
        changes = document.diff(before, after)
        if preview:
            self._rollback(before)
            return CommandResult(value=value, changes=changes, label=self._label(texts, label),
                                 revision=self.revision, preview=True)
        if not changes:
            self._current = before
            return CommandResult(value=value, changes=[], label=None, revision=self.revision)
        resolved = self._label(texts, label)
        self.history.push(HistoryEntry(resolved, before, after, source))
        self._current = after
        self.revision += 1
        self.emit_changed(changes, source)
        return CommandResult(value=value, changes=changes, label=resolved, revision=self.revision)

    @staticmethod
    def _label(texts, label):
        if callable(label):
            return label(texts)
        if len(texts) == 1:
            return texts[0]
        if label:
            return label
        return texts[0] if texts else 'Edit project'

    def _rollback(self, before):
        self.stack.reset()
        try:
            document.restore(self.project, before)
        except Exception:
            log.exception('Session - rollback - restore failed, rebuilding the document')
            try:
                self.project = document.new_project_from(before, self.new_project)
            except Exception:
                log.exception('Session - rollback - rebuild failed')
                raise ServiceError(BACKEND_ERROR, 'The document could not be restored') from None
        self._current = before

    # -- history --------------------------------------------------------------

    def undo(self, source='desktop'):
        if not self.history.can_undo():
            return CommandResult(revision=self.revision)
        entry = self.history.undos.pop()
        self._restore_history(entry.before, entry, redo=False)
        self.history.redos.append(entry)
        changes = document.diff(entry.after, entry.before)
        self.revision += 1
        self.emit_changed(changes, source)
        return CommandResult(changes=changes, label='Undo ' + entry.label, revision=self.revision)

    def redo(self, source='desktop'):
        if not self.history.can_redo():
            return CommandResult(revision=self.revision)
        entry = self.history.redos.pop()
        self._restore_history(entry.after, entry, redo=True)
        self.history.undos.append(entry)
        changes = document.diff(entry.before, entry.after)
        self.revision += 1
        self.emit_changed(changes, source)
        return CommandResult(changes=changes, label='Redo ' + entry.label, revision=self.revision)

    def _restore_history(self, target, entry, redo):
        try:
            document.restore(self.project, target)
        except Exception:
            # Put the entry back and recover the committed state
            (self.history.redos if redo else self.history.undos).append(entry)
            self._rollback(self._current)
            raise
        self._current = target
        self.stack.reset()

    # -- state ----------------------------------------------------------------

    def state(self):
        project = self.project
        state = {'session': self.id, 'path': self.path, 'revision': self.revision,
                 'dirty': self.dirty, 'history': self.history.state(),
                 'sheets': [{'uid': d.uid, 'name': d.fields['name']['value'],
                             'sheet_no': d.fields['sheet_no']['value']} for d in project.drawing_models],
                 'analysis': self.analysis.summary(self.revision) if self.analysis else None}
        return state
