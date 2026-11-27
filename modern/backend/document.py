# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Project document helpers for services: stable identifiers, snapshots for
transactions (ADR 0009), storage model with additive ``uid`` keys (ADR 0008)
and the recording undo stack that captures legacy action labels.

A snapshot is the canonical state of the document as it would be saved: the
project fields (full dictionaries, so derived states survive undo), load
profiles and, per sheet, the sheet fields and ``(uid, element model)`` pairs.
Models pass through a JSON round trip so that they are plain data, compare by
value and never share mutable objects with live elements.
"""

import copy
import json
from dataclasses import dataclass
from typing import Tuple

from gelectrical import __version__
from gelectrical.core import constants
from gelectrical.core.fields import get_fields_trunc, get_fields_dict_trunc
from gelectrical.core.ids import new_uid, is_uid
from gelectrical.model.drawing import DrawingModel


class RecordingStack:
    """Stand-in for ``undo.Stack`` used by service sessions.

    Engine methods decorated with ``@undoable`` or wrapped in ``group()``
    append their action here. Undo itself is snapshot based, so the actions
    are dropped; only the description of each top-level action is kept: the
    service uses it as the label of the command, which therefore matches the
    legacy label for the same engine call."""

    def __init__(self):
        self.texts = []
        self._receivers = []

    def append(self, action):
        if self._receivers:
            self._receivers[-1].append(action)
        else:
            self.texts.append(action.text())

    def setreceiver(self, receiver):
        self._receivers.append(receiver)

    def resetreceiver(self):
        if self._receivers:
            self._receivers.pop()

    def haschanged(self):
        return True

    def reset(self):
        self.texts = []
        self._receivers = []

    def take_texts(self):
        texts, self.texts = self.texts, []
        return texts


def _plain(value):
    """Deep, JSON-normalised copy (tuples -> lists)"""
    return json.loads(json.dumps(value))


def stored_elements(drawing_model):
    """Elements written to the file (display elements are analysis artefacts)"""
    return [e for e in drawing_model.elements if e.code not in constants.DISPLAY_ELEMENT_CODES]


def element_model(element):
    return _plain(element.get_model())


# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------

def ensure_uids(project):
    """Give every sheet and stored element a unique ``uid`` attribute.
    Elements created by engine methods have none; copies made with
    ``copy.deepcopy`` keep the original's uid and get a new one here."""
    seen = set()
    for drawing_model in project.drawing_models:
        uid = getattr(drawing_model, 'uid', None)
        if not is_uid(uid) or uid in seen:
            drawing_model.uid = uid = new_uid()
        seen.add(uid)
        for element in stored_elements(drawing_model):
            uid = getattr(element, 'uid', None)
            if not is_uid(uid) or uid in seen:
                element.uid = uid = new_uid()
            seen.add(uid)


def apply_file_uids(project, pages):
    """After ``ProjectModel.set_model(document, pages)``: take ``uid`` keys
    stored in the file pages (sheet order, element order), then fill gaps."""
    drawing_pages = [page for name, page in pages.items() if name.startswith('proj_drawing_page_')]
    for drawing_model, page in zip(project.drawing_models, drawing_pages):
        try:
            data = page[1]
        except (IndexError, KeyError, TypeError):
            continue
        if not isinstance(data, dict):
            continue
        if is_uid(data.get('uid')):
            drawing_model.uid = data['uid']
        models = data.get('elements', [])
        elements = stored_elements(drawing_model)
        if len(models) == len(elements):
            for element, model in zip(elements, models):
                if isinstance(model, dict) and is_uid(model.get('uid')):
                    element.uid = model['uid']
    ensure_uids(project)


def refresh_derived(project):
    """Derived references that the GTK views set on selection"""
    for drawing_model in project.drawing_models:
        for element in drawing_model.elements:
            if element.code in constants.LOADPROFILE_CODES:
                element.fields['load_profile']['selection_list'] = project.loadprofiles


def storage_model(project):
    """``ProjectModel.get_model()`` with additive ``uid`` keys on sheets and
    elements and ``children_uids`` on assemblies"""
    proj_settings, proj_pages = project.get_model()
    pages = []
    for slno, (name, page) in enumerate(proj_pages):
        if name.startswith('proj_drawing_page_') and slno < len(project.drawing_models):
            drawing_model = project.drawing_models[slno]
            page = copy.copy(page)
            data = dict(page[1])
            data['uid'] = drawing_model.uid
            elements = stored_elements(drawing_model)
            uids = [e.uid for e in elements]
            models = []
            for element, model in zip(elements, data['elements']):
                model = dict(model)
                model['uid'] = element.uid
                if model['code'] == 'element_assembly':
                    model['children_uids'] = [uids[index] for _page, index in model.get('children_codes', [])
                                              if 0 <= index < len(uids)]
                models.append(model)
            data['elements'] = models
            page = [page[0], data]
        pages.append((name, page))
    return proj_settings, pages


APP_PROVENANCE = {'name': 'GElectrical', 'version': __version__, 'saved_by': 'modern'}


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SheetSnapshot:
    uid: str
    fields: dict
    elements: Tuple[Tuple[str, dict], ...]


@dataclass(frozen=True)
class Snapshot:
    fields: dict
    loadprofiles: dict
    sheets: Tuple[SheetSnapshot, ...]
    page_no: int = 0

    def element_index(self):
        """uid -> (sheet index, element index, model)"""
        index = {}
        for k1, sheet in enumerate(self.sheets):
            for k2, (uid, model) in enumerate(sheet.elements):
                index[uid] = (k1, k2, model)
        return index

    def storage(self):
        """Storage model ``(proj_settings, proj_pages)`` of this snapshot"""
        pages = []
        names = []
        for slno, sheet in enumerate(self.sheets):
            name = 'proj_drawing_page_' + str(slno) + '.json'
            models = [dict(model, uid=uid) for uid, model in sheet.elements]
            pages.append((name, ['DrawingModel', {'fields': copy.deepcopy(sheet.fields),
                                                  'elements': copy.deepcopy(models),
                                                  'uid': sheet.uid}]))
            names.append(name)
        pages.append(('proj_loadprofiles.json', copy.deepcopy(self.loadprofiles)))
        settings = {'proj_drawing_names': names,
                    'proj_fields': _plain(get_fields_dict_trunc(self.fields))}
        return settings, pages


def capture(project, previous=None):
    """Snapshot of the live document. Parts equal to those of ``previous``
    reuse its objects (structural sharing: history memory grows with the
    changed elements only). Snapshot data is never mutated."""
    ensure_uids(project)
    old_models = {}
    old_sheet_fields = {}
    if previous is not None:
        for sheet in previous.sheets:
            old_sheet_fields[sheet.uid] = sheet.fields
            for uid, model in sheet.elements:
                old_models[uid] = model
    sheets = []
    for drawing_model in project.drawing_models:
        elements = []
        for element in stored_elements(drawing_model):
            model = element_model(element)
            old = old_models.get(element.uid)
            elements.append((element.uid, old if old is not None and old == model else model))
        fields = _plain(get_fields_trunc(drawing_model.fields))
        old = old_sheet_fields.get(drawing_model.uid)
        sheets.append(SheetSnapshot(drawing_model.uid, old if old is not None and old == fields else fields,
                                    tuple(elements)))
    loadprofiles = _plain(project.loadprofiles)
    fields = copy.deepcopy(project.fields)
    if previous is not None:
        if previous.loadprofiles == loadprofiles:
            loadprofiles = previous.loadprofiles
        if previous.fields == project.fields:
            fields = previous.fields
    return Snapshot(fields=fields, loadprofiles=loadprofiles, sheets=tuple(sheets), page_no=project.page_no)


def _fields_equal(a, b):
    try:
        return _plain(get_fields_dict_trunc(a)) == _plain(get_fields_dict_trunc(b))
    except (TypeError, ValueError):
        return False


def restore(project, snapshot):
    """Make the live document equal to ``snapshot``. Element objects whose
    model is unchanged are kept (cheap undo of local edits); others are
    rebuilt with ``DrawingModel.new_element_from_model`` exactly like loading
    a file."""
    project.fields = copy.deepcopy(snapshot.fields)
    project.loadprofiles = copy.deepcopy(snapshot.loadprofiles)
    existing = {getattr(d, 'uid', None): d for d in project.drawing_models}
    drawing_models = []
    for sheet in snapshot.sheets:
        drawing_model = existing.get(sheet.uid)
        if drawing_model is None:
            drawing_model = DrawingModel(project)
            drawing_model.uid = sheet.uid
        current = {}
        for element in stored_elements(drawing_model):
            current.setdefault(getattr(element, 'uid', None), element)
        elements = []
        gids = set()
        for uid, model in sheet.elements:
            element = current.get(uid)
            if element is None or element.get_gid() in gids or element_model(element) != model:
                element = drawing_model.new_element_from_model(copy.deepcopy(model))
                element.uid = uid
            gids.add(element.get_gid())
            elements.append(element)
        drawing_model.set_model(['DrawingModel', {'fields': copy.deepcopy(sheet.fields), 'elements': []}],
                                copy_elements=False)
        drawing_model.elements = elements
        # Assembly membership from the positional children codes (as set_model)
        for element in elements:
            element.set_gid_assembly(None)
        for element in elements:
            if element.code == 'element_assembly':
                for _page, child_el_no in element.get_children():
                    if 0 <= child_el_no < len(elements):
                        elements[child_el_no].set_gid_assembly(element.get_gid())
        drawing_models.append(drawing_model)
    project.drawing_models[:] = drawing_models
    project.page_no = min(snapshot.page_no, len(drawing_models) - 1)
    project.drawing_model = drawing_models[project.page_no]
    # Stored fields (sheet numbers, assembly children codes) are restored as
    # they were; only derived state is rebuilt
    project.update_title_blocks()
    for drawing_model in drawing_models:
        drawing_model.update_state_variables()
    project.clear_status()
    project.networkmodel = None
    project.powermodel = None
    refresh_derived(project)


def new_project_from(snapshot, project_factory):
    """A fresh project equal to ``snapshot`` (analysis copies)"""
    project = project_factory()
    project.drawing_models[0].uid = snapshot.sheets[0].uid if snapshot.sheets else new_uid()
    restore(project, snapshot)
    return project


# ---------------------------------------------------------------------------
# Change sets
# ---------------------------------------------------------------------------

def diff(before, after):
    """Changes between two snapshots as event entries
    ``[{"kind": ..., "uids": [...]}, ...]`` (empty list: no change)"""
    changes = []
    if not _fields_equal(before.fields, after.fields):
        changes.append({'kind': 'project'})
    if before.loadprofiles != after.loadprofiles:
        changes.append({'kind': 'loadprofiles'})
    before_sheets = {s.uid: (i, s) for i, s in enumerate(before.sheets)}
    after_sheets = {s.uid: (i, s) for i, s in enumerate(after.sheets)}
    sheet_uids = []
    for uid, (index, sheet) in after_sheets.items():
        old = before_sheets.get(uid)
        if old is None or old[0] != index or old[1].fields != sheet.fields:
            sheet_uids.append(uid)
    removed_sheets = [uid for uid in before_sheets if uid not in after_sheets]
    if sheet_uids:
        changes.append({'kind': 'sheet', 'uids': sheet_uids})
    if removed_sheets:
        changes.append({'kind': 'sheet_removed', 'uids': removed_sheets})
    before_elements = before.element_index()
    after_elements = after.element_index()
    added, modified, removed = [], [], []
    for uid, (k1, k2, model) in after_elements.items():
        old = before_elements.get(uid)
        if old is None:
            added.append(uid)
        elif old[2] != model or before.sheets[old[0]].uid != after.sheets[k1].uid:
            modified.append(uid)
    removed = [uid for uid in before_elements if uid not in after_elements]
    if added:
        changes.append({'kind': 'element_added', 'uids': added})
    if modified:
        changes.append({'kind': 'element', 'uids': modified})
    if removed:
        changes.append({'kind': 'element_removed', 'uids': removed})
    return changes


def same_state(before, after):
    return not diff(before, after)
