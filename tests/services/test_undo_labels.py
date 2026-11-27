"""Each legacy user action maps to one service command with the same undo
granularity and label (M4 acceptance; backend.md section 5, undo table).

Every case performs the legacy action on a ProjectModel with the legacy
``undo.Stack`` (the calls the GTK views make) and the service command on a
runtime session loaded from the same file, then checks:

* one legacy undo entry and one service history entry, same label;
* the stored document is the same after both (identity keys stripped);
* service undo restores the initial document, redo the edited one.
"""

import copy

import pytest

from gelectrical import persistence, undo
from gelectrical.core import constants
from gelectrical.core.database import load_database, validate_database_item
from gelectrical.core.fields import get_fields_from_params, update_params_from_fields
from gelectrical.core.undoable import get_undoable_set_field, get_undoable_set_field_multiple, group
from gelectrical.model.project import ProjectModel

from conftest import MULTISHEET, strip_uids


class Legacy:
    def __init__(self, filename):
        self.stack = undo.Stack()
        self.project = ProjectModel(stack=self.stack)
        persistence.load_project(self.project, filename)
        self.stack.clear()

    def stored(self):
        settings, pages = self.project.get_model()
        return strip_uids({'settings': settings, 'pages': dict(pages)})

    def dm(self, page=0):
        return self.project.drawing_models[page]


def service_stored(runtime):
    def read():
        from modern.backend.document import storage_model
        settings, pages = storage_model(runtime.get_session().project)
        return strip_uids({'settings': settings, 'pages': dict(pages)})
    return runtime.run_on_owner(read).result()


def uid_at(runtime, page, index):
    def read():
        return runtime.get_session().project.drawing_models[page].elements[index].uid
    return runtime.run_on_owner(read).result()


def sheet_uid(runtime, page):
    return runtime.call('project.state')['sheets'][page]['uid']


def index_of(project, codes, page=0, nth=0):
    found = [i for i, e in enumerate(project.drawing_models[page].elements) if e.code in codes]
    return found[nth]


# -- legacy actions (as the GTK views call the engine) and service commands --

def legacy_set_field(lg):
    element = lg.dm()[index_of(lg.project, ('element_circuitbreaker',))]
    get_undoable_set_field(lg.stack, None, element)('ref', 'UNDO-TEST')


def service_set_field(rt, lg):
    uid = uid_at(rt, 0, index_of(lg.project, ('element_circuitbreaker',)))
    return rt.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'UNDO-TEST'}})


def legacy_set_field_multiple(lg):
    elements = [lg.dm()[index_of(lg.project, ('element_circuitbreaker',), nth=n)] for n in (0, 1)]
    get_undoable_set_field_multiple(lg.stack, None, elements, copy.deepcopy(elements[0].fields))('ref', 'Q-TEST')


def service_set_field_multiple(rt, lg):
    uids = [uid_at(rt, 0, index_of(lg.project, ('element_circuitbreaker',), nth=n)) for n in (0, 1)]
    return rt.call('drawing.set_fields', {'uids': uids, 'values': {'ref': 'Q-TEST'}})


def _legacy_insert(lg, code, x, y):
    dm = lg.dm()
    dm.set_floating_model_from_code(code)
    port = dm.get_port_around_coordinate(x, y, ignore_display_elements=True)
    if port is None:
        dm.floating_model.set_coordinates(*dm.get_grid_point(x, y))
    dm.make_floating_model_permenant(port)
    dm.reset_floating_model()


def legacy_insert(lg):
    _legacy_insert(lg, 'element_load', 5003, 5011)


def service_insert(rt, lg):
    return rt.call('drawing.insert', {'sheet': sheet_uid(rt, 0), 'code': 'element_load', 'x': 5003, 'y': 5011})


def _busbar_port(lg):
    return lg.dm()[index_of(lg.project, ('element_busbar',))].get_ports_global()[0]


def legacy_insert_at_port(lg):
    x, y = _busbar_port(lg)
    _legacy_insert(lg, 'element_circuitbreaker', x + 1, y + 1)


def service_insert_at_port(rt, lg):
    x, y = _busbar_port(lg)
    return rt.call('drawing.insert', {'sheet': sheet_uid(rt, 0), 'code': 'element_circuitbreaker',
                                      'x': x + 1, 'y': y + 1})


def legacy_delete(lg):
    lg.dm().delete_rows([0, 2])


def service_delete(rt, lg):
    return rt.call('drawing.delete', {'uids': [uid_at(rt, 0, 0), uid_at(rt, 0, 2)]})


WIRE = [[5005, 5010], [5005, 5100], [5200, 5100]]


def legacy_wire(lg):
    dm = lg.dm()
    for x, y in WIRE[:-1]:
        dm.add_wire_point(x, y)
    dm.make_wire_permenant(*WIRE[-1])


def service_wire(rt, lg):
    return rt.call('drawing.add_wire', {'sheet': sheet_uid(rt, 0), 'points': WIRE})


def _plain_indices(lg):
    return [i for i, e in enumerate(lg.dm().elements) if e.code == 'element_load'][:2]


def legacy_assemble(lg):
    dm = lg.dm()
    lg.project.de_select_all()
    for index in _plain_indices(lg):
        dm.elements[index].set_selection(True)
    dm.add_assembly_from_selection()
    lg.project.de_select_all()


def service_assemble(rt, lg):
    return rt.call('drawing.assemble', {'uids': [uid_at(rt, 0, i) for i in _plain_indices(lg)]})


def legacy_ungroup(lg):
    lg.dm().delete_rows([index_of(lg.project, ('element_assembly',))])


def service_ungroup(rt, lg):
    return rt.call('drawing.ungroup', {'uid': uid_at(rt, 0, index_of(lg.project, ('element_assembly',)))})


def _renumber(mode):
    def legacy(lg):
        if mode == 'Selected elements only':
            for index in (1, 3):
                lg.dm().elements[index].set_selection(True)
        lg.project.renumber_elements(mode)
        lg.project.de_select_all()

    def service(rt, lg):
        params = {'mode': mode}
        if mode == 'Selected elements only':
            params['uids'] = [uid_at(rt, 0, 1), uid_at(rt, 0, 3)]
        return rt.call('drawing.renumber', params)
    return legacy, service


def legacy_add_sheet(lg):
    lg.project.set_page(1)
    lg.project.append_page(copy_selected_sheet=True)


def service_add_sheet(rt, lg):
    return rt.call('drawing.add_sheet', {'copy_from': sheet_uid(rt, 1)})


def legacy_remove_sheet(lg):
    lg.project.remove_page(1)


def service_remove_sheet(rt, lg):
    return rt.call('drawing.remove_sheet', {'sheet': sheet_uid(rt, 1)})


def legacy_reorder(lg):
    lg.project.reorder_tab(2, 1)


def service_reorder(rt, lg):
    return rt.call('drawing.reorder_sheet', {'sheet': sheet_uid(rt, 2), 'index': 1})


def legacy_sheet_field(lg):
    lg.dm().update_page_field('title', 'NEW TITLE')


def service_sheet_field(rt, lg):
    return rt.call('drawing.set_sheet_fields', {'sheet': sheet_uid(rt, 0), 'values': {'title': 'NEW TITLE'}})


def legacy_project_settings(lg):
    fields = copy.deepcopy(lg.project.get_project_fields(full=True))
    fields['Information']['project_name']['value'] = 'Renamed project'
    lg.project.update_project_fields(fields)


def service_project_settings(rt, lg):
    return rt.call('project.set_settings', {'values': {'Information': {'project_name': 'Renamed project'}}})


NEW_PROFILES = {'load_prof_1': ['Flat', [{'mode': constants.GRAPH_DATATYPE_PROFILE, 'title': 'Default',
                                          'xval': [0, 23], 'yval': [1, 1]}]],
                'load_prof_2': ['Day', [{'mode': constants.GRAPH_DATATYPE_PROFILE, 'title': 'Day',
                                         'xval': [0, 8, 18, 23], 'yval': [0.2, 1, 1, 0.2]}]]}


def legacy_loadprofiles(lg):
    lg.project.modify_loadprofiles(copy.deepcopy(NEW_PROFILES))


def service_loadprofiles(rt, lg):
    return rt.call('loadprofiles.set', {'profiles': NEW_PROFILES})


def _cable(lg):
    index = index_of(lg.project, ('element_line_cable',))
    element = lg.dm()[index]
    data = load_database(element.database_path)
    category = list(data)[-1]
    item = list(data[category])[-1]
    return index, element, data, category, item


def legacy_library(lg):
    index, element, data, category, item = _cable(lg)
    validated = validate_database_item(element.fields, data[category][item], element.database_path)
    setter = get_undoable_set_field(lg.stack, None, element)

    class View:
        stack = lg.stack
    with group(View, 'Update data from database'):
        for code, value in validated.items():
            setter(code, value)


def service_library(rt, lg):
    index, element, data, category, item = _cable(lg)
    return rt.call('library.apply', {'uid': uid_at(rt, 0, index), 'category': category, 'item': item})


def _references(lg):
    """Base reference on sheet 1 and every reference on other sheets (one of
    them carries a different reference code, so linking changes it)"""
    first = (0, index_of(lg.project, ('element_reference',), page=0))
    others = []
    for page in range(1, len(lg.project.drawing_models)):
        others += [(page, i) for i, e in enumerate(lg.project.drawing_models[page].elements)
                   if e.code in constants.REFERENCE_CODES]
    return first, others


def legacy_link(lg):
    first, others = _references(lg)
    selected = {p: [] for p in range(len(lg.project.drawing_models))}
    for page, index in others:
        selected[page].append(index)
    lg.project.link_references(first, selected)


def service_link(rt, lg):
    first, others = _references(lg)
    return rt.call('drawing.link_references', {'uid': uid_at(rt, *first),
                                               'targets': [uid_at(rt, *other) for other in others]})


def _protection_change(lg):
    index = index_of(lg.project, ('element_circuitbreaker',))
    element = lg.dm()[index]
    fields = get_fields_from_params(element.fields['pcurve_l']['value']['parameters'])
    for code, field in fields.items():
        if not field.get('status_enable', True):
            continue
        options = field.get('selection_list')
        if options:
            if len(options) > 1:
                return index, element, code, next(o for o in options if o != field['value'])
        elif field['type'] == 'float':
            return index, element, code, round(field['value'] * 2 + 0.01, 6)
    raise AssertionError('no editable protection parameter')


def legacy_protection(lg):
    index, element, code, value = _protection_change(lg)
    data_new = copy.deepcopy(element.fields['pcurve_l']['value'])
    fields = get_fields_from_params(data_new['parameters'])
    fields[code]['value'] = value
    update_params_from_fields(data_new['parameters'], fields)
    setter = get_undoable_set_field(lg.stack, None, element)

    class View:
        stack = lg.stack
    with group(View, 'Update protection parameters - ' + element.name):
        setter('pcurve_l', data_new)


def service_protection(rt, lg):
    index, element, code, value = _protection_change(lg)
    return rt.call('protection.set_parameters', {'uid': uid_at(rt, 0, index), 'curve': 'pcurve_l',
                                                 'parameters': {code: value}})


def legacy_paste(lg):
    dm = lg.dm()
    lg.project.de_select_all()
    for index in (1, 2):
        dm.elements[index].set_selection(True)
    text = dm.get_clipboard_text()
    lg.project.de_select_all()
    elements, assembly_dict = dm.elements_from_clipboard(text)
    dm.add_floating_model(elements, assembly_dict)
    dm.floating_model.set_coordinates(*dm.get_grid_point(6007, 6013))
    dm.make_floating_model_permenant(None)
    dm.reset_floating_model()


def service_paste(rt, lg):
    text = rt.call('drawing.copy', {'uids': [uid_at(rt, 0, 1), uid_at(rt, 0, 2)]})['text']
    return rt.call('drawing.paste', {'sheet': sheet_uid(rt, 0), 'text': text, 'x': 6007, 'y': 6013})


CASES = [
    ('set_field', legacy_set_field, service_set_field),
    ('set_field_multiple', legacy_set_field_multiple, service_set_field_multiple),
    ('insert', legacy_insert, service_insert),
    ('insert_at_port', legacy_insert_at_port, service_insert_at_port),
    ('paste', legacy_paste, service_paste),
    ('delete', legacy_delete, service_delete),
    ('add_wire', legacy_wire, service_wire),
    ('assemble', legacy_assemble, service_assemble),
    ('ungroup_by_delete', legacy_ungroup, service_ungroup),
    ('renumber_all', *_renumber('All')),
    ('renumber_new', *_renumber('New elements only')),
    ('renumber_selected', *_renumber('Selected elements only')),
    ('add_sheet', legacy_add_sheet, service_add_sheet),
    ('remove_sheet', legacy_remove_sheet, service_remove_sheet),
    ('reorder_sheet', legacy_reorder, service_reorder),
    ('sheet_field', legacy_sheet_field, service_sheet_field),
    ('project_settings', legacy_project_settings, service_project_settings),
    ('loadprofiles', legacy_loadprofiles, service_loadprofiles),
    ('library_apply', legacy_library, service_library),
    ('link_references', legacy_link, service_link),
    ('protection_parameters', legacy_protection, service_protection),
]


@pytest.mark.parametrize('name, legacy_action, service_action', CASES, ids=[c[0] for c in CASES])
def test_service_command_matches_legacy_action(runtime, name, legacy_action, service_action):
    legacy = Legacy(MULTISHEET)
    initial = legacy.stored()
    runtime.call('project.open', {'path': MULTISHEET})
    assert service_stored(runtime) == initial

    legacy_action(legacy)
    assert legacy.stack.undocount() == 1, 'legacy action is not one undo entry'
    legacy_label = legacy.stack.undotext()[len('Undo '):]
    edited = legacy.stored()
    assert edited != initial

    reference = Legacy(MULTISHEET)   # fresh legacy copy for the service-side lookups
    result = service_action(runtime, reference)
    assert result['label'] == legacy_label
    history = runtime.call('history.state')
    assert history['undo_count'] == 1
    assert history['undo_text'] == 'Undo ' + legacy_label
    assert service_stored(runtime) == edited

    undone = runtime.call('history.undo')
    assert undone['label'] == 'Undo ' + legacy_label
    assert service_stored(runtime) == initial
    runtime.call('history.redo')
    assert service_stored(runtime) == edited
    # Not compared: the legacy undo itself (deleting element 0 and undoing
    # re-appends it at the end, insert_element_at_index treats 0 as append)


def test_move_is_one_entry_and_keeps_order(runtime):
    """Changed (documented): the legacy drag deletes the element and inserts
    a copy at the end of the list (two undo entries); ``drawing.move``
    moves in place as one entry ``Move element(s)``."""
    runtime.call('project.open', {'path': MULTISHEET})
    sheet = runtime.call('drawing.sheet', {'sheet': sheet_uid(runtime, 0)})
    target = sheet['elements'][1]
    result = runtime.call('drawing.move', {'uids': [target['uid']], 'dx': 32, 'dy': 16})
    assert result['label'] == 'Move element(s)'
    after = runtime.call('drawing.sheet', {'sheet': sheet_uid(runtime, 0)})
    assert [e['uid'] for e in after['elements']] == [e['uid'] for e in sheet['elements']]
    moved = after['elements'][1]
    assert (moved['x'], moved['y']) == (target['x'] + 32, target['y'] + 16)
    assert runtime.call('history.state')['undo_count'] == 1
    runtime.call('history.undo')
    again = runtime.call('drawing.sheet', {'sheet': sheet_uid(runtime, 0)})
    assert (again['elements'][1]['x'], again['elements'][1]['y']) == (target['x'], target['y'])
