"""Command contract, sessions and persistence through the services (M4)"""

import json
import os
import zipfile

import pytest

from gelectrical import persistence
from gelectrical.model.drawing import DrawingModel
from gelectrical.model.project import ProjectModel
from modern.backend.protocol import ServiceError

from conftest import MULTISHEET, SAMPLE, first_sheet, strip_uids


def stored(runtime, session=None):
    """The document as it would be written to the file (JSON values)"""
    def read():
        from modern.backend.document import storage_model
        settings, pages = storage_model(runtime.get_session(session).project)
        return json.loads(json.dumps({'settings': settings, 'pages': dict(pages)}))
    return runtime.run_on_owner(read).result()


def error_of(func, *args, **kwargs):
    with pytest.raises(ServiceError) as info:
        func(*args, **kwargs)
    return info.value


# -- identity ------------------------------------------------------------------

def test_uids_are_unique_and_survive_save_and_reopen(runtime, tmp_path):
    runtime.call('project.open', {'path': MULTISHEET})
    state = runtime.call('project.state')
    uids = [s['uid'] for s in state['sheets']]
    for sheet in state['sheets']:
        uids += [e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet['uid']})['elements']]
    assert len(uids) == len(set(uids))
    target = str(tmp_path / 'saved.gepro')
    runtime.call('project.save_as', {'path': target})
    runtime.call('project.open', {'path': target})
    state = runtime.call('project.state')
    again = [s['uid'] for s in state['sheets']]
    for sheet in state['sheets']:
        again += [e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet['uid']})['elements']]
    assert again == uids


def test_uids_stay_stable_across_deletes_and_undo(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    sheet = first_sheet(runtime)
    before = [e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet})['elements']]
    runtime.call('drawing.delete', {'uids': [before[0]]})
    after = [e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet})['elements']]
    assert after == before[1:]
    runtime.call('history.undo')
    assert [e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet})['elements']] == before


# -- command contract -------------------------------------------------------------

def test_command_increments_revision_marks_dirty_and_emits_event(runtime, events):
    runtime.call('project.open', {'path': MULTISHEET})
    state = runtime.call('project.state')
    assert not state['dirty']
    events.clear()
    uid = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements'][0]['uid']
    result = runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'G-1'}})
    assert result['revision'] == state['revision'] + 1
    assert result['changes'] == [{'kind': 'element', 'uids': [uid]}]
    assert runtime.call('project.state')['dirty']
    changed = [e for e in events if e['event'] == 'changed']
    assert changed[-1]['revision'] == result['revision'] and changed[-1]['changes'] == result['changes']
    runtime.call('history.undo')
    assert not runtime.call('project.state')['dirty']   # back at the saved state


def test_validation_error_changes_nothing(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    initial = stored(runtime)
    revision = runtime.call('project.state')['revision']
    elements = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements']
    uid = elements[0]['uid']
    error = error_of(runtime.call, 'drawing.set_fields', {'uids': [uid], 'values': {'ref': 'X', 'no_field': 1}})
    assert error.code == 'VALIDATION_ERROR' and error.field == 'values.no_field'
    error = error_of(runtime.call, 'drawing.set_fields', {'uids': [uid], 'values': {'ref': 12}})
    assert error.code == 'VALIDATION_ERROR'
    error = error_of(runtime.call, 'drawing.delete', {'uids': ['00000000-0000-4000-8000-000000000000']})
    assert error.code == 'NOT_FOUND'
    error = error_of(runtime.call, 'drawing.delete', {'uids': 'not-a-list'})
    assert error.code == 'INVALID_REQUEST'
    error = error_of(runtime.call, 'drawing.delete', {'uids': [uid], 'unexpected': 1})
    assert error.code == 'INVALID_REQUEST'
    assert stored(runtime) == initial
    assert runtime.call('project.state')['revision'] == revision
    assert runtime.call('history.state')['undo_count'] == 0


def test_arithmetic_entry_uses_safe_expressions(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    sheet = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime), 'detail': True})
    cable = next(e for e in sheet['elements'] if e['code'] == 'element_line_cable')
    schema = {f['code']: f for f in cable['field_schema']}
    code = next(c for c, f in schema.items() if f['type'] == 'float' and f['editable'] and f['enabled']
                and not f['selection_list'])
    runtime.call('drawing.set_fields', {'uids': [cable['uid']], 'values': {code: '2*(3+4)'}})
    assert runtime.call('drawing.element', {'uid': cable['uid']})['fields'][code] == 14.0
    error = error_of(runtime.call, 'drawing.set_fields',
                     {'uids': [cable['uid']], 'values': {code: '__import__("os").getcwd()'}})
    assert error.code == 'VALIDATION_ERROR'


def test_injected_failure_rolls_back_completely(runtime, monkeypatch):
    """A failure in the middle of an engine operation leaves no partial
    change: delete on two sheets fails after the first sheet was changed"""
    runtime.call('project.open', {'path': MULTISHEET})
    initial = stored(runtime)
    state = runtime.call('project.state')
    uids = [runtime.call('drawing.sheet', {'sheet': s['uid']})['elements'][0]['uid'] for s in state['sheets'][:2]]
    original = DrawingModel.delete_rows
    calls = []

    def failing(self, rows):
        calls.append(rows)
        if len(calls) == 2:
            raise RuntimeError('injected failure')
        return original(self, rows)

    monkeypatch.setattr(DrawingModel, 'delete_rows', failing)
    with pytest.raises(RuntimeError):
        runtime.call('drawing.delete', {'uids': uids})
    monkeypatch.setattr(DrawingModel, 'delete_rows', original)
    assert len(calls) == 2
    assert stored(runtime) == initial
    assert runtime.call('project.state')['revision'] == state['revision']
    assert runtime.call('history.state')['undo_count'] == 0
    # The session keeps working
    result = runtime.call('drawing.delete', {'uids': uids})
    assert result['label'] == "Delete draw elements at '[0]'"


def test_preview_returns_changes_without_committing(runtime, events):
    runtime.call('project.open', {'path': MULTISHEET})
    initial = stored(runtime)
    revision = runtime.call('project.state')['revision']
    events.clear()
    result = runtime.call('drawing.insert', {'sheet': first_sheet(runtime), 'code': 'element_load',
                                             'x': 4000, 'y': 4000, 'preview': True})
    assert result['preview'] is True
    assert result['label'] == 'Insert element(s) at None'
    assert result['changes'][0]['kind'] == 'element_added'
    assert stored(runtime) == initial
    assert runtime.call('project.state')['revision'] == revision
    assert runtime.call('history.state')['undo_count'] == 0
    assert not [e for e in events if e['event'] == 'changed']


def test_stale_revision_is_rejected(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    revision = runtime.call('project.state')['revision']
    uid = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements'][0]['uid']
    runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'A'}, 'if_revision': revision})
    error = error_of(runtime.call, 'drawing.set_fields',
                     {'uids': [uid], 'values': {'ref': 'B'}, 'if_revision': revision})
    assert error.code == 'STALE_REVISION'
    assert error.details == {'revision': revision + 1}
    assert runtime.call('drawing.element', {'uid': uid})['fields']['ref'] == 'A'


def test_no_change_records_no_history(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    element = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements'][0]
    result = runtime.call('drawing.set_fields', {'uids': [element['uid']], 'values': {'ref': element['fields']['ref']}})
    assert result['changes'] == [] and result['label'] is None
    assert runtime.call('history.state')['undo_count'] == 0


def test_undo_redo_sequence_restores_each_state(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    sheet = first_sheet(runtime)
    states = [stored(runtime)]
    uid = runtime.call('drawing.sheet', {'sheet': sheet})['elements'][0]['uid']
    runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'S1'}})
    states.append(stored(runtime))
    runtime.call('drawing.insert', {'sheet': sheet, 'code': 'element_load', 'x': 4000, 'y': 4000})
    states.append(stored(runtime))
    runtime.call('drawing.add_sheet', {})
    states.append(stored(runtime))
    runtime.call('drawing.renumber', {'mode': 'All'})
    states.append(stored(runtime))
    for expected in reversed(states[:-1]):
        runtime.call('history.undo')
        assert stored(runtime) == expected
    for expected in states[1:]:
        runtime.call('history.redo')
        assert stored(runtime) == expected
    runtime.call('history.undo')
    runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'NEW'}})
    assert runtime.call('history.state')['can_redo'] is False


def test_history_is_bounded(events):
    from modern.backend.runtime import Runtime
    from modern.backend.services.settings import SettingsStore
    import conftest
    rt = Runtime(emit=events.append, settings=SettingsStore(conftest._DATA_DIR, persist=False), history_limit=3)
    try:
        uid = rt.call('drawing.insert', {'sheet': first_sheet(rt), 'code': 'element_load', 'x': 100, 'y': 100})['value']['uids'][0]
        for n in range(6):
            rt.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'L%d' % n}})
        assert rt.call('history.state')['undo_count'] == 3
    finally:
        rt.close()


# -- sessions -------------------------------------------------------------------------

def test_sessions_are_isolated(runtime):
    runtime.call('session.create', {'session': 'second'})
    runtime.call('project.open', {'path': MULTISHEET})
    runtime.call('project.open', {'path': MULTISHEET}, session='second')
    runtime.call('project.set_settings', {'values': {'Information': {'project_name': 'Only main'}}})
    second = runtime.call('project.settings', session='second')
    assert second['pages']['Information']['values']['project_name'] != 'Only main'
    assert runtime.call('history.state', session='second')['undo_count'] == 0
    uid = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements'][0]['uid']
    # Identifiers belong to their session's document
    other = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime, 'second')}, session='second')
    assert uid not in [e['uid'] for e in other['elements']]
    sessions = runtime.call('session.list')
    assert [s['session'] for s in sessions['sessions']] == ['main', 'second']
    runtime.call('session.close', {'session': 'second'})
    assert error_of(runtime.call, 'project.state', session='second').code == 'NOT_FOUND'


def test_new_projects_do_not_share_defaults(runtime):
    runtime.call('session.create', {'session': 'b'})
    runtime.call('project.set_settings', {'values': {'Simulation': {'grid_frequency': 60}}})
    assert runtime.call('project.settings', session='b')['pages']['Simulation']['values']['grid_frequency'] == 50


# -- persistence -----------------------------------------------------------------------

def test_saved_file_opens_in_legacy_loader_with_same_model(runtime, tmp_path):
    runtime.call('project.open', {'path': SAMPLE})
    target = str(tmp_path / 'modern.gepro')
    runtime.call('project.save_as', {'path': target})
    with zipfile.ZipFile(target) as archive:
        document = json.loads(archive.read('document.json'))
        page = json.loads(archive.read('proj_drawing_page_0.json'))
    assert document['_file_version'] == 'GELECTRICAL_FILE_REFERENCE_VER_0'
    assert document['app']['saved_by'] == 'modern'
    assert 'uid' in page[1] and all('uid' in e for e in page[1]['elements'])
    assemblies = [e for e in page[1]['elements'] if e['code'] == 'element_assembly']
    assert assemblies and all(len(a['children_uids']) == len(a['children_codes']) for a in assemblies)
    # Legacy loader (the GTK app uses the same engine call)
    original, reloaded = ProjectModel(), ProjectModel()
    persistence.load_project(original, SAMPLE)
    persistence.load_project(reloaded, target)
    a_settings, a_pages = original.get_model()
    b_settings, b_pages = reloaded.get_model()
    assert strip_uids(b_settings) == strip_uids(a_settings)
    assert strip_uids(dict(b_pages)) == strip_uids(dict(a_pages))


def test_save_is_atomic_and_keeps_backup(runtime, tmp_path, monkeypatch):
    runtime.call('project.open', {'path': MULTISHEET})
    target = str(tmp_path / 'p.gepro')
    runtime.call('project.save_as', {'path': target})
    assert not runtime.call('project.state')['dirty']
    first = open(target, 'rb').read()
    uid = runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements'][0]['uid']
    runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'SAVED-2'}})
    runtime.call('project.save')
    assert open(target + '.bak', 'rb').read() == first
    second = open(target, 'rb').read()
    runtime.call('drawing.set_fields', {'uids': [uid], 'values': {'ref': 'SAVED-3'}})

    def broken_replace(src, dst):
        raise OSError('disk full')
    monkeypatch.setattr(os, 'replace', broken_replace)
    error = error_of(runtime.call, 'project.save')
    assert error.code == 'FILE_ERROR'
    monkeypatch.undo()
    assert open(target, 'rb').read() == second
    assert runtime.call('project.state')['dirty']
    assert [f for f in os.listdir(tmp_path) if f.endswith('.tmp')] == []


def test_open_errors_are_reported(runtime, tmp_path):
    bad = tmp_path / 'bad.gepro'
    bad.write_bytes(b'not a zip')
    error = error_of(runtime.call, 'project.open', {'path': str(bad)})
    assert error.code == 'FILE_ERROR' and 'Error opening file' in error.message
    error = error_of(runtime.call, 'project.open', {'path': str(tmp_path / 'missing.gepro')})
    assert error.code == 'FILE_ERROR'
    # The open document is unchanged
    assert runtime.call('project.state')['path'] is None


def test_save_without_path_needs_save_as(runtime):
    assert error_of(runtime.call, 'project.save').code == 'VALIDATION_ERROR'


# -- catalogue, library, load profiles, protection ----------------------------------------

def test_catalog_types_come_from_element_classes(runtime):
    catalog = runtime.call('catalog.element_types')
    codes = [t['code'] for t in catalog['types']]
    assert 'element_load' in codes and 'element_display_node' not in codes
    load = runtime.call('catalog.element_type', {'code': 'element_load'})
    assert {'ref', 'load_profile'} <= {f['code'] for f in load['fields']}
    assert len(runtime.call('catalog.element_types', {'advanced': True})['types']) >= len(codes)
    assert error_of(runtime.call, 'catalog.element_type', {'code': 'nope'}).code == 'NOT_FOUND'


def test_library_catalogue_and_item(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    cable = next(e for e in runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements']
                 if e['code'] == 'element_line_cable')
    catalogue = runtime.call('library.catalogue', {'uid': cable['uid']})
    assert catalogue['database'] == 'cable_iec.csv' and catalogue['categories']
    category = catalogue['categories'][0]
    item = runtime.call('library.item', {'uid': cable['uid'], 'category': category['category'],
                                          'item': category['items'][0]})
    assert item['values']
    found = runtime.call('library.catalogue', {'uid': cable['uid'], 'search': category['items'][0]})
    assert any(category['items'][0] in c['items'] for c in found['categories'])


def test_loadprofiles_validation(runtime):
    profiles = runtime.call('loadprofiles.get')
    bad = {'p': ['Bad', [{'mode': 1, 'title': 'x', 'xval': [0, 1], 'yval': [1]}]]}
    assert error_of(runtime.call, 'loadprofiles.set', {'profiles': bad}).code == 'VALIDATION_ERROR'
    assert runtime.call('loadprofiles.get') == profiles


def test_protection_curves(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    breaker = next(e for e in runtime.call('drawing.sheet', {'sheet': first_sheet(runtime)})['elements']
                   if e['code'] == 'element_circuitbreaker')
    curves = runtime.call('protection.curves', {'uids': [breaker['uid']]})
    assert curves[0]['protection'] and curves[0]['curves']['pcurve_l']


def test_connectivity_nodes_use_uids(runtime):
    runtime.call('project.open', {'path': MULTISHEET})
    nodes = runtime.call('drawing.connectivity')['nodes']
    uids = set()
    for sheet in runtime.call('project.state')['sheets']:
        uids |= {e['uid'] for e in runtime.call('drawing.sheet', {'sheet': sheet['uid']})['elements']}
    assert nodes and all(member[0] in uids for node in nodes for member in node['members'])
    assert len({node['key'] for node in nodes}) == len(nodes)


def test_program_settings_roundtrip(tmp_path):
    from modern.backend.services.settings import SettingsStore
    store = SettingsStore(str(tmp_path))
    store.update({'Defaults': {'drawing_field_dept': 'Electrical'}})
    assert SettingsStore(str(tmp_path)).values['Defaults']['drawing_field_dept']['value'] == 'Electrical'
    with pytest.raises(ServiceError):
        store.update({'Paths': {'library_path': '/elsewhere'}})   # read-only field
