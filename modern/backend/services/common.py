# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Lookups and input validation shared by the services. Validation happens
before any change (command contract step 1)."""

import math
import numbers

from gelectrical.core.expressions import ExpressionError, evaluate_numeric
from gelectrical.core.ids import is_uid

from ..document import stored_elements
from ..protocol import invalid, not_found, validation


def require_uid(value, field='uid'):
    if not is_uid(value):
        raise invalid('Expected an identifier', field=field)
    return value


def require_uid_list(values, field='uids', allow_empty=False):
    if not isinstance(values, list) or (not values and not allow_empty):
        raise invalid('Expected a list of identifiers', field=field)
    for value in values:
        require_uid(value, field)
    if len(set(values)) != len(values):
        raise invalid('Duplicate identifiers', field=field)
    return values


def require_int(value, field, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        else:
            raise invalid('Expected an integer', field=field)
    value = int(value)
    if (minimum is not None and value < minimum) or (maximum is not None and value > maximum):
        raise validation('Value out of range', field=field)
    return value


def require_number(value, field):
    if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
        raise invalid('Expected a finite number', field=field)
    return value


def require_str(value, field, allow_empty=True, max_length=10_000):
    if not isinstance(value, str) or (not allow_empty and not value) or len(value) > max_length:
        raise invalid('Expected text', field=field)
    return value


def require_bool(value, field):
    if not isinstance(value, bool):
        raise invalid('Expected true or false', field=field)
    return value


def require_choice(value, choices, field):
    if value not in choices:
        raise validation('Expected one of: ' + ', '.join(map(str, choices)), field=field)
    return value


def require_point(value, field):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise invalid('Expected a point [x, y]', field=field)
    return [require_number(value[0], field), require_number(value[1], field)]


# -- document lookups ---------------------------------------------------------

def sheet_index(project, uid, field='sheet'):
    require_uid(uid, field)
    for index, drawing_model in enumerate(project.drawing_models):
        if getattr(drawing_model, 'uid', None) == uid:
            return index
    raise not_found('Unknown sheet', field=field)


def find_element(project, uid, field='uid'):
    """Return ``(page, index, drawing_model, element)`` for an element uid"""
    require_uid(uid, field)
    for page, drawing_model in enumerate(project.drawing_models):
        for index, element in enumerate(drawing_model.elements):
            if getattr(element, 'uid', None) == uid:
                return page, index, drawing_model, element
    raise not_found('Unknown element', field=field)


def find_elements(project, uids, field='uids', same_sheet=False):
    found = [find_element(project, uid, field) for uid in require_uid_list(uids, field)]
    if same_sheet and len({page for page, *_ in found}) > 1:
        raise validation('Elements must be on one sheet', field=field)
    return found


def key_to_uid(project):
    """``(page, index) -> uid`` of stored elements"""
    mapping = {}
    for page, drawing_model in enumerate(project.drawing_models):
        for index, element in enumerate(stored_elements(drawing_model)):
            mapping[(page, index)] = element.uid
    return mapping


# -- field values -------------------------------------------------------------

def validate_field_value(fields, code, value, field_name='values'):
    """Value for field ``code`` converted like the legacy field view: numbers
    or arithmetic text (``core.expressions.evaluate_numeric``) for numeric
    fields, ``float`` rounded to the field's decimals; selection lists
    enforced; hidden and read-only fields rejected."""
    path = '%s.%s' % (field_name, code)
    if code not in fields:
        raise validation('Unknown field %r' % code, field=path)
    field = fields[code]
    if not field.get('status_enable', True) or field.get('status_inactivate', False):
        raise validation('Field %r is not editable' % code, field=path)
    if field.get('validation_func'):
        try:
            value = field['validation_func'](value)
        except Exception as exc:
            raise validation('Invalid value for %r: %s' % (code, exc), field=path) from None
    field_type = field['type']
    if field_type in ('float', 'int'):
        if isinstance(value, str):
            try:
                value = evaluate_numeric(value)
            except ExpressionError as exc:
                raise validation('Invalid number for %r: %s' % (code, exc), field=path) from None
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
            raise validation('Expected a number for %r' % code, field=path)
        if field_type == 'float':
            value = round(float(value), field['decimal']) if field.get('decimal') is not None else float(value)
        else:
            value = int(value)
    elif field_type in ('str', 'multiline_str', 'font', 'path'):
        if not isinstance(value, str):
            raise validation('Expected text for %r' % code, field=path)
        if field.get('max_chars') and len(value) > field['max_chars']:
            raise validation('Text too long for %r' % code, field=path)
    elif field_type == 'bool':
        if not isinstance(value, bool):
            raise validation('Expected true or false for %r' % code, field=path)
    elif field_type in ('graph', 'data'):
        if value is not None and not isinstance(value, (dict, list)):
            raise validation('Expected structured data for %r' % code, field=path)
    selection_list = field.get('selection_list')
    if selection_list is not None and field_type not in ('graph', 'data'):
        if value not in selection_list:
            raise validation('Value for %r must be one of the selection list' % code, field=path)
    return value


def require_values(values, field='values'):
    if not isinstance(values, dict) or not values:
        raise invalid('Expected an object of field values', field=field)
    return values
