# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Data transfer objects (docs/architecture/backend.md section 8).

Every DTO is derived from the engine's own field dictionaries and element
classes; nothing here restates engineering rules. JSON Schemas of these
shapes are in :mod:`modern.backend.schemas`.
"""

import os

from gelectrical.core import constants

from .document import stored_elements
from .protocol import json_safe

FIELD_TYPES = ('int', 'float', 'str', 'multiline_str', 'bool', 'font', 'graph', 'data', 'path', 'heading')


def field_schema(code, field):
    """FieldSchema of one engine field dictionary"""
    images = field.get('selection_image_list')
    return json_safe({
        'code': code,
        'type': field.get('type'),
        'caption': field.get('caption', ''),
        'unit': field.get('unit', ''),
        'decimal': field.get('decimal'),
        'max_chars': field.get('max_chars'),
        'selection_list': _selection_list(field.get('selection_list')),
        'selection_images': [os.path.basename(i) if isinstance(i, str) else None for i in images] if images else None,
        'enabled': bool(field.get('status_enable', True)),
        'editable': not field.get('status_inactivate', False),
        'floating': bool(field.get('status_floating', False)),
        'alter_structure': bool(field.get('alter_structure', False)),
        'click_to_edit_message': field.get('click_to_edit_message'),
        'tooltip': field.get('tooltip', '') or '',
    })


def _selection_list(selection_list):
    if selection_list is None:
        return None
    if isinstance(selection_list, dict):
        # Load profiles: uid -> [title, graph]
        return [{'value': key, 'caption': value[0] if isinstance(value, (list, tuple)) and value else str(key)}
                for key, value in selection_list.items()]
    return list(selection_list)


def fields_schema(fields):
    return [field_schema(code, field) for code, field in fields.items()]


def field_values(fields):
    return json_safe({code: field['value'] for code, field in fields.items()})


def field_state(fields):
    """Derived per-field state that changes with values"""
    state = {}
    for code, field in fields.items():
        state[code] = {'enabled': bool(field.get('status_enable', True)),
                       'editable': not field.get('status_inactivate', False),
                       'selection_list': _selection_list(field.get('selection_list'))}
    return json_safe(state)


def element_type(code, cls, element):
    """Element type from its class and a fresh instance"""
    return json_safe({
        'code': code,
        'name': getattr(cls, 'name', code),
        'group': getattr(cls, 'group', None),
        'icon': os.path.basename(cls.icon) if getattr(cls, 'icon', None) else None,
        'tooltip': getattr(cls, 'tooltip', '') or '',
        'advanced': code in constants.ADVANCED_ELEMENTS,
        'ports': element.get_ports(),
        'fields': fields_schema(element.fields),
    })


def element(element, sheet_uid, uid_by_index=None, detail=False):
    """Element DTO; ``detail`` adds field schemas and label lines"""
    data = {
        'uid': element.uid,
        'code': element.code,
        'name': getattr(element, 'name', element.code),
        'sheet_uid': sheet_uid,
        'x': element.x,
        'y': element.y,
        'orientation': element.orientation,
        'ports': element.get_ports_global(),
        'fields': field_values(element.fields),
    }
    if element.code == 'element_wire':
        data['points'] = json_safe(element.points)
    if element.code == 'element_assembly' and uid_by_index is not None:
        data['children'] = [uid_by_index[index] for _page, index in element.get_children()
                            if 0 <= index < len(uid_by_index)]
    rect = element.get_dimensions()
    data['bounds'] = [int(v) for v in rect]
    if detail:
        data['field_schema'] = fields_schema(element.fields)
        data['database'] = bool(getattr(element, 'database_path', None))
    else:
        data['field_state'] = field_state(element.fields)
    return json_safe(data)


def sheet_summary(drawing_model, index):
    return {'uid': drawing_model.uid, 'index': index,
            'name': drawing_model.fields['name']['value'],
            'sheet_no': drawing_model.fields['sheet_no']['value']}


def sheet(drawing_model, index, detail=False):
    elements = stored_elements(drawing_model)
    uid_by_index = [e.uid for e in elements]
    data = sheet_summary(drawing_model, index)
    data['fields'] = field_values(drawing_model.fields)
    data['field_schema'] = fields_schema(drawing_model.fields)
    data['page'] = {'width': drawing_model.fields['page_width']['value'],
                    'height': drawing_model.fields['page_height']['value'],
                    'grid': drawing_model.grid_width}
    data['elements'] = [element(e, drawing_model.uid, uid_by_index, detail) for e in elements]
    return json_safe(data)


def result_fields(res_fields):
    """Result field records, captions and units from ``res_fields``"""
    out = []
    for code, field in res_fields.items():
        record = {'code': code, 'caption': field.get('caption', ''), 'unit': field.get('unit', ''),
                  'type': field.get('type'), 'value': field.get('value'), 'decimal': field.get('decimal')}
        out.append(record)
    return json_safe(out)


def message_list(results, key_to_uid, node_key):
    """Diagnostics / rules check messages (MessageView format) as
    ``[{category, severity, text, uids, nodes}]``. ``key_to_uid`` maps
    ``(page, index)`` to element uids; ``node_key`` maps global node numbers
    to node keys."""
    messages = []
    if not results:
        return messages
    for category, items in results.items():
        for item in items:
            head = item[0]
            if isinstance(head, dict):
                severity = head.get('type', 'info')
                text = head.get('message', '')
            else:
                severity = 'info'
                text = head
            uids, nodes = [], []
            for kind, ids in (item[1] if len(item) > 1 and item[1] else []):
                if kind == 'node':
                    nodes += [node_key(n) for n in ids]
                else:
                    for key in ids:
                        uid = key_to_uid.get(tuple(key))
                        if uid:
                            uids.append(uid)
            messages.append({'category': category, 'severity': severity, 'text': text,
                             'uids': uids, 'nodes': nodes})
    return json_safe(messages)
