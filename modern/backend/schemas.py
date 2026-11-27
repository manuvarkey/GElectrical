# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""JSON Schemas (draft 2020-12 subset) of the protocol envelope and DTOs.

``python -m modern.backend --write-schemas modern/backend/schemas`` writes one
file per schema; ``tests/services/test_schemas.py`` checks that the committed
files are current and that DTOs produced by the services conform. Only the
keywords ``type``, ``properties``, ``required``, ``items``,
``additionalProperties``, ``enum``, ``$ref`` and ``anyOf`` are used.
"""

import json
import os

from .protocol import ERROR_CODES, EVENTS

ID = 'https://gelectrical.kavilgroup/schemas/'


def _nullable(schema):
    return {'anyOf': [schema, {'type': 'null'}]}


def _obj(properties, required=None, additional=True):
    schema = {'type': 'object', 'properties': properties}
    if required:
        schema['required'] = list(required)
    if not additional:
        schema['additionalProperties'] = False
    return schema


STR = {'type': 'string'}
INT = {'type': 'integer'}
NUM = {'type': 'number'}
BOOL = {'type': 'boolean'}
ANY = {}
UID = {'type': 'string'}
POINT = {'type': 'array', 'items': NUM}

FIELD_SCHEMA = _obj({
    'code': STR, 'type': STR, 'caption': STR, 'unit': _nullable(STR), 'decimal': _nullable(INT),
    'max_chars': _nullable(INT), 'selection_list': _nullable({'type': 'array'}),
    'selection_images': _nullable({'type': 'array'}), 'enabled': BOOL, 'editable': BOOL,
    'floating': BOOL, 'alter_structure': BOOL, 'click_to_edit_message': _nullable(STR), 'tooltip': STR,
}, required=('code', 'type', 'caption', 'enabled', 'editable'))

ELEMENT_TYPE = _obj({
    'code': STR, 'name': STR, 'group': _nullable(STR), 'icon': _nullable(STR), 'tooltip': STR,
    'advanced': BOOL, 'ports': {'type': 'array', 'items': POINT},
    'fields': {'type': 'array', 'items': {'$ref': 'FieldSchema.json'}},
}, required=('code', 'name', 'ports', 'fields'))

ELEMENT = _obj({
    'uid': UID, 'code': STR, 'name': STR, 'sheet_uid': UID, 'x': NUM, 'y': NUM,
    'orientation': {'enum': ['vertical', 'horizontal']},
    'ports': {'type': 'array', 'items': POINT}, 'fields': {'type': 'object'},
    'field_state': {'type': 'object'}, 'field_schema': {'type': 'array', 'items': {'$ref': 'FieldSchema.json'}},
    'points': {'type': 'array', 'items': POINT}, 'children': {'type': 'array', 'items': UID},
    'bounds': {'type': 'array', 'items': INT}, 'database': BOOL,
}, required=('uid', 'code', 'sheet_uid', 'x', 'y', 'orientation', 'ports', 'fields'))

SHEET = _obj({
    'uid': UID, 'index': INT, 'name': STR, 'sheet_no': STR, 'fields': {'type': 'object'},
    'field_schema': {'type': 'array', 'items': {'$ref': 'FieldSchema.json'}},
    'page': _obj({'width': NUM, 'height': NUM, 'grid': NUM}),
    'elements': {'type': 'array', 'items': {'$ref': 'Element.json'}},
}, required=('uid', 'index', 'name', 'sheet_no'))

RESULT_FIELD = _obj({
    'code': STR, 'caption': STR, 'unit': _nullable(STR), 'type': _nullable(STR), 'value': ANY,
    'decimal': _nullable(INT),
}, required=('code', 'caption', 'value'))

MESSAGE = _obj({
    'category': STR, 'severity': {'enum': ['error', 'warning', 'info']}, 'text': STR,
    'uids': {'type': 'array', 'items': UID}, 'nodes': {'type': 'array', 'items': STR},
}, required=('category', 'severity', 'text', 'uids', 'nodes'))

CHANGE = _obj({'kind': {'enum': ['document', 'project', 'loadprofiles', 'sheet', 'sheet_removed',
                                 'element_added', 'element', 'element_removed', 'analysis', 'saved']},
               'uids': {'type': 'array', 'items': UID}}, required=('kind',))

COMMAND_RESULT = _obj({
    'value': ANY, 'changes': {'type': 'array', 'items': {'$ref': 'Change.json'}},
    'label': _nullable(STR), 'revision': INT, 'preview': BOOL,
}, required=('value', 'changes', 'label', 'revision', 'preview'), additional=False)

ERROR = _obj({'code': {'enum': list(ERROR_CODES)}, 'message': STR, 'field': STR, 'details': ANY},
             required=('code', 'message'), additional=False)

REQUEST = _obj({'id': STR, 'session': STR, 'method': STR, 'params': {'type': 'object'}},
               required=('id', 'method'), additional=False)

RESPONSE = {'anyOf': [
    _obj({'id': STR, 'result': ANY}, required=('id', 'result'), additional=False),
    _obj({'id': _nullable(STR), 'error': {'$ref': 'Error.json'}}, required=('id', 'error'), additional=False),
]}

EVENT = _obj({'event': {'enum': list(EVENTS)}, 'session': STR, 'revision': INT,
              'changes': {'type': 'array', 'items': {'$ref': 'Change.json'}}, 'source': STR,
              'dirty': BOOL, 'job': STR, 'kind': STR, 'stage': STR, 'fraction': NUM,
              'message': STR, 'status': STR, 'error': {'$ref': 'Error.json'}},
             required=('event',))

SCHEMAS = {
    'FieldSchema': FIELD_SCHEMA,
    'ElementType': ELEMENT_TYPE,
    'Element': ELEMENT,
    'Sheet': SHEET,
    'ResultField': RESULT_FIELD,
    'Message': MESSAGE,
    'Change': CHANGE,
    'CommandResult': COMMAND_RESULT,
    'Error': ERROR,
    'Request': REQUEST,
    'Response': RESPONSE,
    'Event': EVENT,
}


def documents():
    """``{file name: schema document}``"""
    out = {}
    for name, schema in SCHEMAS.items():
        doc = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$id': ID + name + '.json',
               'title': name}
        doc.update(schema)
        out[name + '.json'] = doc
    return out


def render(document):
    return json.dumps(document, indent=2, sort_keys=True) + '\n'


def write_schemas(folder):
    os.makedirs(folder, exist_ok=True)
    for filename, doc in documents().items():
        with open(os.path.join(folder, filename), 'w', encoding='utf-8', newline='\n') as fp:
            fp.write(render(doc))
    return sorted(documents())
