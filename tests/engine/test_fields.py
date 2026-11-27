"""core.fields (M2): field dictionaries, truncation, update, defaults."""

from gelectrical.core import fields


def test_get_field_dict_keys_and_defaults():
    f = fields.get_field_dict('float', 'Length', 'km', 1.5, decimal=3)
    assert f['type'] == 'float' and f['value'] == 1.5 and f['decimal'] == 3
    assert f['status_enable'] is True and f['status_inactivate'] is True
    assert set(f) == {'type', 'caption', 'unit', 'value', 'max_chars', 'validation_func',
                      'selection_list', 'selection_image_list', 'decimal', 'status_enable',
                      'status_inactivate', 'status_floating', 'click_to_edit_message',
                      'alter_structure', 'alter_values_dict', 'tooltip'}


def test_alter_values_dict_not_shared():
    """D15: no shared mutable default between fields"""
    a = fields.get_field_dict('str', 'A', '', '')
    b = fields.get_field_dict('str', 'B', '', '')
    assert a['alter_values_dict'] == {} and a['alter_values_dict'] is not b['alter_values_dict']


def test_set_field_selection_list():
    flds = {'x': fields.get_field_dict('str', 'X', '', 'c')}
    modified = {}
    fields.set_field_selection_list(flds, 'x', ['a', 'b'], modified)
    assert flds['x']['value'] == 'a' and modified == {'x': 'c'}
    fields.set_field_selection_list(flds, 'x', ['a', 'b'])
    assert flds['x']['value'] == 'a'
    fields.set_field_selection_list(flds, 'x', None)
    assert flds['x']['selection_list'] is None


def test_trunc_and_update_roundtrip():
    ref = {'a': fields.get_field_dict('float', 'A', '', 1.0),
           'b': fields.get_field_dict('str', 'B', '', 'x')}
    stored = fields.get_fields_trunc(ref)
    assert stored == {'a': {'value': 1.0, 'type': 'float'}, 'b': {'value': 'x', 'type': 'str'}}
    stored['a']['value'] = 2.0
    stored['b']['type'] = 'int'      # type mismatch: ignored
    stored['c'] = {'value': 1, 'type': 'int'}  # unknown: ignored
    updated = fields.update_fields(ref, stored)
    assert updated['a']['value'] == 2.0 and updated['b']['value'] == 'x' and 'c' not in updated
    assert ref['a']['value'] == 1.0  # reference not modified


def test_update_fields_dict():
    ref = fields.new_project_settings()
    stored = fields.get_fields_dict_trunc(ref)
    stored['Information']['project_name']['value'] = 'P1'
    updated = fields.update_fields_dict(ref, stored)
    assert updated['Information']['project_name']['value'] == 'P1'


def test_new_project_settings_are_independent():
    """D4: each project gets its own copy of the defaults"""
    a = fields.new_project_settings()
    b = fields.new_project_settings()
    a['Information']['project_name']['value'] = 'CHANGED'
    assert b['Information']['project_name']['value'] == 'PROJECT'
    assert fields.default_project_settings['Information']['project_name']['value'] == 'PROJECT'


def test_get_fields_from_params_validation():
    params = {'k': ['Gain', '', 1.0, None, 'tip', (2, 0, 10)],
              's': ['Mode', '', 'A', ['A', 'B'], '', 'str', False]}
    flds = fields.get_fields_from_params(params, modify_code='p_')
    assert flds['p_k']['validation_func']('12.345') == 10
    assert flds['p_k']['validation_func']('2.345') == 2.35
    assert flds['p_s']['type'] == 'str' and flds['p_s']['status_enable'] is False


def test_field_dict_wrapper():
    store = {'a': fields.get_field_dict('int', 'A', '', 3)}
    fd = fields.FieldDict(store)
    assert fd.a == 3 and fd['a'] == 3
    fd['a'] = 4
    assert store['a']['value'] == 4 and len(fd) == 1
