# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Protection curves of elements and protection parameter changes.

The coordination data set of the legacy view (curves scaled to the voltage
of a power flow, node fault currents, disconnection time marker) and the
settings spreadsheet export arrive with milestone M11 (D03-D06)."""

import copy

from gelectrical.core import constants
from gelectrical.core.fields import get_fields_from_params, update_params_from_fields
from gelectrical.core.undoable import get_undoable_set_field, group

from ..protocol import json_safe, validation
from ..registry import query, command
from .common import find_element, find_elements, require_choice, require_values, validate_field_value

CURVES = ('pcurve_l', 'pcurve_g', 'dcurve')
_MODEL_ATTRIBUTES = {'pcurve_l': 'line_protection_model', 'pcurve_g': 'ground_protection_model',
                     'dcurve': 'damage_model'}


def element_curves(element):
    curves = {}
    for code, attribute in _MODEL_ATTRIBUTES.items():
        model = getattr(element, attribute, None)
        if code in element.fields and model is not None:
            evaluated = model.get_evaluated(element.fields)
            curves[code] = evaluated.get_graph_model() if evaluated else None
    return curves


@query('protection.curves')
def curves(ctx, uids):
    """Evaluated protection and damage curves (unscaled) of elements"""
    out = []
    for page, index, drawing_model, element in find_elements(ctx.project, uids):
        out.append({'uid': element.uid, 'code': element.code,
                    'protection': element.code in constants.PROTECTION_ELEMENT_CODES,
                    'damage': element.code in constants.DAMAGE_ELEMENT_CODES,
                    'curves': element_curves(element)})
    return json_safe(out)


@command('protection.set_parameters')
def set_parameters(ctx, uid, curve, parameters):
    """Change parameters of an element's protection or damage curve (one undo entry)"""
    page, index, drawing_model, element = find_element(ctx.project, uid)
    require_choice(curve, CURVES, 'curve')
    require_values(parameters, 'parameters')
    value = element.fields.get(curve, {}).get('value')
    if not isinstance(value, dict) or 'parameters' not in value:
        raise validation('Element has no %s parameters' % curve, field='curve')
    data_new = copy.deepcopy(value)
    fields = get_fields_from_params(data_new['parameters'])
    for code, item in parameters.items():
        fields[code]['value'] = validate_field_value(fields, code, item, 'parameters')
    update_params_from_fields(data_new['parameters'], fields)
    setter = get_undoable_set_field(ctx.session.stack, None, element)
    with group(ctx.session, 'Update protection parameters - ' + element.name):
        setter(curve, data_new)
    return {'uid': uid, 'curve': curve}
