# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Drawing service: sheets, elements, wires, assemblies, references.

Commands call the same engine methods as the legacy drawing view, so derived
fields update exactly as today and the undo label is the legacy action's
label (recorded from the engine's ``@undoable`` call). Differences from the
legacy interaction are listed in docs/architecture/backend.md section 5
(undo label table).
"""

import copy

from gelectrical.core import constants
from gelectrical.core.fields import apply_alter_values
from gelectrical.core.undoable import get_undoable_set_field, get_undoable_set_field_multiple
from gelectrical.model.clipboard import ClipboardError
from gelectrical.model.networkmodel import NetworkModel
from gelectrical.elementmodel.wire import Wire

from .. import document, dto
from ..document import stored_elements
from ..protocol import validation, invalid, not_found
from ..registry import query, command
from .common import (sheet_index, find_element, find_elements, require_number, require_int, require_str,
                     require_bool, require_choice, require_point, require_uid, require_uid_list,
                     require_values, validate_field_value)

ORIENTATIONS = ('vertical', 'horizontal')
RENUMBER_MODES = ('All', 'New elements only', 'Selected elements only')
MAX_WIRE_POINTS = 1000


def _drawing(ctx, sheet):
    page = sheet_index(ctx.project, sheet)
    return page, ctx.project.drawing_models[page]


def _select(project, elements):
    """Engine selection (selection order = list order) for engine methods
    that act on the selection; selection is not document state"""
    project.de_select_all()
    for drawing_model in project.drawing_models:
        drawing_model.selected_ports = []
    for element in elements:
        element.set_selection(True)


def _new_uids(project, drawing_model, count_before):
    document.ensure_uids(project)
    return [e.uid for e in stored_elements(drawing_model)[count_before:]]


def node_identities(project, networkmodel=None):
    """Connectivity of a document: one entry per electrical node (keyed by
    global node number) with its members ``[uid, port]`` and the drawing
    positions of its ports. Node keys ``N[uid:port|...]`` are stable across
    edits that do not change the node. Uses ``networkmodel`` when given
    (analysis copies), otherwise builds one without touching the project."""
    if networkmodel is None:
        networkmodel = NetworkModel(project)
        networkmodel.setup_base_elements()
        networkmodel.setup_global_nodes()
    members = {}
    for p0, gnode in networkmodel.node_mapping.items():
        code, _sep, port = p0.rpartition(':')
        try:
            page, index = (int(v) for v in code.strip('()').split(','))
            uid = project.drawing_models[page].elements[index].uid
        except (ValueError, IndexError, AttributeError):
            continue
        members.setdefault(gnode, []).append([uid, port])
    nodes = {}
    for gnode in sorted(networkmodel.global_nodes):
        entry = sorted(members.get(gnode, []))
        positions = []
        for port in sorted(networkmodel.port_mapping_inverted.get(gnode, ()), key=str):
            if len(port) == 3 and 0 <= port[0] < len(project.drawing_models):
                positions.append([project.drawing_models[port[0]].uid, port[1], port[2]])
        key = 'N[' + '|'.join('%s:%s' % (uid, port) for uid, port in entry) + ']'
        nodes[gnode] = {'key': key, 'members': entry, 'positions': positions}
    return nodes


# -- queries ------------------------------------------------------------------

@query('drawing.sheets')
def sheets(ctx):
    """Sheets in order"""
    return [dto.sheet_summary(d, i) for i, d in enumerate(ctx.project.drawing_models)]


@query('drawing.sheet')
def sheet(ctx, sheet, detail=False):
    """Sheet fields, page size and elements (``detail`` adds field schemas)"""
    require_bool(detail, 'detail')
    page, drawing_model = _drawing(ctx, sheet)
    return dto.sheet(drawing_model, page, detail)


@query('drawing.element')
def element(ctx, uid):
    """One element with values, field schemas and derived field state"""
    page, index, drawing_model, element = find_element(ctx.project, uid)
    uids = [e.uid for e in stored_elements(drawing_model)]
    data = dto.element(element, drawing_model.uid, uids, detail=True)
    data['field_state'] = dto.field_state(element.fields)
    return data


@query('drawing.hit_test')
def hit_test(ctx, sheet, x, y, size=None):
    """Element and port around a drawing coordinate (selection helper)"""
    page, drawing_model = _drawing(ctx, sheet)
    x, y = require_number(x, 'x'), require_number(y, 'y')
    size = constants.SELECT_PORT_RECT if size is None else require_number(size, 'size')
    port = drawing_model.get_port_around_coordinate(x, y, w=size, h=size, ignore_display_elements=True)
    _index, found = drawing_model.get_element_around_coordinate(x, y, w=size, h=size, ignore_display_elements=True)
    return {'uid': found.uid if found is not None else None, 'port': list(port) if port else None}


@query('drawing.connectivity')
def connectivity(ctx):
    """Electrical nodes as sets of (element uid, port) with port positions"""
    return {'nodes': list(node_identities(ctx.project).values())}


@query('drawing.copy')
def copy_elements(ctx, uids):
    """Clipboard text (versioned JSON) of elements of one sheet"""
    found = find_elements(ctx.project, uids, same_sheet=True)
    drawing_model = found[0][2]
    _select(ctx.project, [entry[3] for entry in found])
    try:
        text = drawing_model.get_clipboard_text()
    finally:
        ctx.project.de_select_all()
    return {'text': text}


# -- element commands ---------------------------------------------------------

def _place_floating(drawing_model, x, y, orientation, attachment_port):
    floating = drawing_model.floating_model
    if orientation == 'horizontal':
        if not floating.rotate_model():
            raise validation('Only single elements can be rotated while inserting', field='orientation')
    port_count = sum(len(e.get_ports()) for e in floating.elements)
    if attachment_port and attachment_port >= max(port_count, 1):
        raise validation('Attachment port out of range', field='attachment_port')
    for _ in range(attachment_port):
        floating.modify_attachment_port()
    port = drawing_model.get_port_around_coordinate(x, y, ignore_display_elements=True)
    if port is None:
        gx, gy = drawing_model.get_grid_point(x, y)
        floating.set_coordinates(gx, gy)
    drawing_model.make_floating_model_permenant(port)
    drawing_model.reset_floating_model()


@command('drawing.insert')
def insert(ctx, sheet, code, x, y, orientation='vertical', attachment_port=0, fields=None):
    """Insert an element; its attachment port goes to (x, y), snapped to a nearby port or the grid"""
    page, drawing_model = _drawing(ctx, sheet)
    require_str(code, 'code', allow_empty=False, max_length=100)
    if code not in drawing_model.element_models or code in constants.DISPLAY_ELEMENT_CODES:
        raise not_found('Unknown element type %r' % code, field='code')
    x, y = require_number(x, 'x'), require_number(y, 'y')
    require_choice(orientation, ORIENTATIONS, 'orientation')
    attachment_port = require_int(attachment_port, 'attachment_port', minimum=0)
    count = len(stored_elements(drawing_model))
    element = drawing_model.set_floating_model_from_code(code)
    try:
        if fields is not None:
            for field_code, value in require_values(fields, 'fields').items():
                element.set_text_field_value(field_code, validate_field_value(element.fields, field_code, value, 'fields'))
                if element.fields[field_code].get('alter_structure'):
                    apply_alter_values(element.fields, field_code)
        _place_floating(drawing_model, x, y, orientation, attachment_port)
    finally:
        drawing_model.reset_floating_model()
    return {'uids': _new_uids(ctx.project, drawing_model, count)}


@command('drawing.paste')
def paste(ctx, sheet, text, x, y, attachment_port=0):
    """Insert elements from clipboard text (validated JSON, never executed)"""
    page, drawing_model = _drawing(ctx, sheet)
    require_str(text, 'text', allow_empty=False, max_length=1_900_000)
    x, y = require_number(x, 'x'), require_number(y, 'y')
    attachment_port = require_int(attachment_port, 'attachment_port', minimum=0)
    try:
        elements, assembly_dict = drawing_model.elements_from_clipboard(text)
    except ClipboardError as exc:
        raise validation('No valid data in clipboard: %s' % exc, field='text') from None
    if not elements:
        raise validation('No elements in clipboard', field='text')
    count = len(stored_elements(drawing_model))
    drawing_model.add_floating_model(elements, assembly_dict)
    try:
        _place_floating(drawing_model, x, y, 'vertical', attachment_port)
    finally:
        drawing_model.reset_floating_model()
    return {'uids': _new_uids(ctx.project, drawing_model, count)}


@command('drawing.delete')
def delete(ctx, uids):
    """Delete elements"""
    found = find_elements(ctx.project, uids)
    by_page = {}
    for page, index, drawing_model, element in found:
        by_page.setdefault(page, []).append(index)
    for page, indices in by_page.items():
        ctx.project.drawing_models[page].delete_rows(indices)
    return {'deleted': list(uids)}


@command('drawing.move', label='Move element(s)')
def move(ctx, uids, dx, dy):
    """Move elements by (dx, dy) in place; moving an assembly moves its children"""
    found = find_elements(ctx.project, uids)
    dx, dy = require_number(dx, 'dx'), require_number(dy, 'dy')
    moved = []
    for page, index, drawing_model, element in found:
        group = [element]
        if element.code == 'element_assembly':
            group += [drawing_model.elements[i] for _p, i in element.get_children()
                      if 0 <= i < len(drawing_model.elements)]
        for item in group:
            if all(item is not other for other in moved):
                item.move(dx, dy)
                item.extents_stale = True
                moved.append(item)
    # Assembly boxes follow moved children (as the GTK view after redraw)
    for drawing_model in {id(entry[2]): entry[2] for entry in found}.values():
        for element in drawing_model.elements:
            if element.code == 'element_assembly' and element not in moved:
                children = [drawing_model.elements[i] for _p, i in element.get_children()
                            if 0 <= i < len(drawing_model.elements)]
                if any(child in moved for child in children):
                    element.set_children(element.get_children(), children)
    return {'moved': list(uids)}


@command('drawing.rotate', label='Rotate element')
def rotate(ctx, uid):
    """Toggle orientation of a placed element about its first port"""
    page, index, drawing_model, element = find_element(ctx.project, uid)
    if element.code in ('element_wire', 'element_assembly'):
        raise validation('Wires and assemblies cannot be rotated', field='uid')
    ports = element.get_ports_global()
    element.orientation = 'vertical' if element.orientation == 'horizontal' else 'horizontal'
    if ports:
        new_ports = element.get_ports_global()
        element.move(ports[0][0] - new_ports[0][0], ports[0][1] - new_ports[0][1])
    element.extents_stale = True
    return {'orientation': element.orientation}


def _set_fields_label(texts):
    # One field: the legacy label; several: one entry for all of them
    return texts[0] if len(texts) == 1 else 'Modify {} fields'.format(len(texts))


@command('drawing.set_fields', label=_set_fields_label)
def set_fields(ctx, uids, values):
    """Set field values of one element or of several elements of one type"""
    found = find_elements(ctx.project, uids)
    require_values(values)
    elements = [entry[3] for entry in found]
    if len({e.code for e in elements}) > 1 or (len(elements) > 1 and elements[0].code == 'element_wire'):
        raise validation('Multiple elements must be of the same type', field='uids')
    for element in elements:
        if element.code in constants.LOADPROFILE_CODES:
            element.fields['load_profile']['selection_list'] = ctx.project.loadprofiles
    stack = ctx.session.stack
    if len(elements) == 1:
        element = elements[0]
        setter = get_undoable_set_field(stack, None, element)
        for code, value in values.items():
            setter(code, validate_field_value(element.fields, code, value))
            if element.fields[code].get('alter_structure'):
                apply_alter_values(element.fields, code)
    else:
        for element in elements:
            for code, value in values.items():
                validate_field_value(element.fields, code, value)
        multiselect_fields = copy.deepcopy(elements[0].fields)
        setter = get_undoable_set_field_multiple(stack, None, elements, multiselect_fields)
        for code, value in values.items():
            setter(code, validate_field_value(elements[0].fields, code, value))
    return {'uids': list(uids)}


# -- wires --------------------------------------------------------------------

def _wire_points(drawing_model, points, field='points'):
    if not isinstance(points, list) or not 2 <= len(points) <= MAX_WIRE_POINTS:
        raise invalid('Expected 2 to %d points' % MAX_WIRE_POINTS, field=field)
    snapped = []
    for point in points:
        x, y = require_point(point, field)
        port = drawing_model.get_port_around_coordinate(x, y, ignore_display_elements=True)
        snapped.append(tuple(port) if port else drawing_model.get_grid_point(x, y))
    return snapped


@command('drawing.add_wire')
def add_wire(ctx, sheet, points):
    """Add a wire; points snap to nearby ports, otherwise to the grid"""
    page, drawing_model = _drawing(ctx, sheet)
    snapped = _wire_points(drawing_model, points)
    count = len(stored_elements(drawing_model))
    drawing_model.wire_points = list(snapped[:-1])
    drawing_model.make_wire_permenant(*snapped[-1], grid_constraint=False)
    return {'uids': _new_uids(ctx.project, drawing_model, count)}


@command('drawing.edit_wire')
def edit_wire(ctx, uid, points):
    """Replace the points of a wire"""
    page, index, drawing_model, element = find_element(ctx.project, uid)
    if element.code != 'element_wire':
        raise validation('Element is not a wire', field='uid')
    wire = Wire(_wire_points(drawing_model, points))
    for code, field in element.fields.items():
        if code in wire.fields:
            wire.fields[code]['value'] = field['value']
    wire.set_gid(element.get_gid())
    wire.set_gid_assembly(element.get_gid_assembly())
    wire.uid = element.uid
    drawing_model.update_element_at_index(wire, index)
    return {'uid': uid}


# -- assemblies and references ------------------------------------------------

@command('drawing.assemble')
def assemble(ctx, uids):
    """Group elements of one sheet into an assembly (an assembly in the selection is extended)"""
    found = find_elements(ctx.project, uids, same_sheet=True)
    drawing_model = found[0][2]
    previous = {i: getattr(e, 'uid', None) for i, e in enumerate(drawing_model.elements)
                if e.code == 'element_assembly'}
    count = len(stored_elements(drawing_model))
    _select(ctx.project, [entry[3] for entry in found])
    try:
        drawing_model.add_assembly_from_selection()
    finally:
        ctx.project.de_select_all()
    # An extended assembly keeps its identifier
    for index, uid in previous.items():
        element = drawing_model.elements[index]
        if element.code == 'element_assembly' and getattr(element, 'uid', None) is None:
            element.uid = uid
            return {'uid': uid}
    return {'uid': _new_uids(ctx.project, drawing_model, count)[0]}


@command('drawing.ungroup')
def ungroup(ctx, uid):
    """Remove an assembly; its children stay"""
    page, index, drawing_model, element = find_element(ctx.project, uid)
    if element.code != 'element_assembly':
        raise validation('Element is not an assembly', field='uid')
    for _p, child in element.get_children():
        if 0 <= child < len(drawing_model.elements):
            drawing_model.elements[child].set_gid_assembly(None)
    drawing_model.delete_rows([index])
    return {'uid': uid}


@command('drawing.link_references')
def link_references(ctx, uid, targets, copy_titles=False):
    """Link a cross-reference element with reference elements on other sheets"""
    page, index, drawing_model, element = find_element(ctx.project, uid)
    if element.code not in constants.REFERENCE_CODES:
        raise validation('Select a cross reference element to link', field='uid')
    require_bool(copy_titles, 'copy_titles')
    selected = {p: [] for p in range(len(ctx.project.drawing_models))}
    for t_page, t_index, _d, target in find_elements(ctx.project, require_uid_list(targets, 'targets')):
        if target.code not in constants.REFERENCE_CODES or target is element:
            raise validation('Targets must be other cross reference elements', field='targets')
        selected[t_page].append(t_index)
    ctx.project.link_references((page, index), selected, copy_titles=copy_titles)
    return {'reference': ctx.project.drawing_models[page].elements[index].fields['ref']['value']}


@command('drawing.renumber')
def renumber(ctx, mode, uids=None):
    """Renumber element references: All, New elements only, Selected elements only"""
    require_choice(mode, RENUMBER_MODES, 'mode')
    if mode == 'Selected elements only':
        _select(ctx.project, [entry[3] for entry in find_elements(ctx.project, uids)])
    elif uids is not None:
        raise invalid('uids only apply to "Selected elements only"', field='uids')
    try:
        ctx.project.renumber_elements(mode)
    finally:
        ctx.project.de_select_all()
    return {'mode': mode}


# -- sheets -------------------------------------------------------------------

@command('drawing.add_sheet')
def add_sheet(ctx, copy_from=None):
    """Append a sheet; fields copied from ``copy_from`` (default: first sheet)"""
    project = ctx.project
    if copy_from is not None:
        project.page_no = sheet_index(project, copy_from, 'copy_from')
        project.append_page(copy_selected_sheet=True)
    else:
        project.append_page(copy_selected_sheet=False)
    document.ensure_uids(project)
    return {'uid': project.drawing_models[-1].uid}


@command('drawing.remove_sheet')
def remove_sheet(ctx, sheet):
    """Remove a sheet (not the first one, as in the legacy app)"""
    page = sheet_index(ctx.project, sheet)
    if page == 0:
        raise validation('Deleting sheet number 1 not permitted.', field='sheet')
    ctx.project.remove_page(page)
    return {'uid': sheet}


@command('drawing.reorder_sheet')
def reorder_sheet(ctx, sheet, index):
    """Move a sheet to a new position"""
    page = sheet_index(ctx.project, sheet)
    index = require_int(index, 'index', minimum=0, maximum=len(ctx.project.drawing_models) - 1)
    ctx.project.reorder_tab(page, index)
    return {'uid': sheet, 'index': index}


@command('drawing.set_sheet_fields', label='Update page fields')
def set_sheet_fields(ctx, sheet, values):
    """Set sheet fields (name, page size, title block)"""
    page, drawing_model = _drawing(ctx, sheet)
    require_values(values)
    validated = {code: validate_field_value(drawing_model.fields, code, value) for code, value in values.items()}
    for code, value in validated.items():
        drawing_model.update_page_field(code, value)
    return dto.sheet_summary(drawing_model, page)
