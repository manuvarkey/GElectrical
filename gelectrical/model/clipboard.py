#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# clipboard
#
#  Copyright 2026 Manu Varkey <manuvarkey@gmail.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

"""Copy and paste of drawing elements as a versioned JSON payload (D2,
ADR 0011). Replaces the pickle payload of the legacy clipboard.

Payload (version 1)::

    {"format": "gelectrical-elements", "version": 1,
     "elements": [<element.get_model()>, ...],
     "assemblies": {"<index of assembly>": [<index of child>, ...]}}

Element models are the stored models of ``.gepro`` drawings. Pasted text is
validated here; elements are then created through
``DrawingModel.new_element_from_model`` exactly as when loading a project.
"""

import json
import numbers

CLIPBOARD_FORMAT = 'gelectrical-elements'
CLIPBOARD_VERSION = 1
MAX_TEXT_LENGTH = 50 * 1024 * 1024
MAX_ELEMENTS = 10000
ORIENTATIONS = ('horizontal', 'vertical')


class ClipboardError(ValueError):
    """Clipboard text is not a valid element payload"""


def encode_elements(elements, assembly_dict=None):
    """Clipboard text for ``elements`` (as returned by
    ``DrawingModel.get_selected(assembly_info=True)``)"""
    payload = {'format': CLIPBOARD_FORMAT,
               'version': CLIPBOARD_VERSION,
               'elements': [element.get_model() for element in elements],
               'assemblies': {str(key): list(value) for key, value in (assembly_dict or {}).items()}}
    return json.dumps(payload)


def _is_number(value):
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def _check_point_list(value, name):
    if not isinstance(value, list):
        raise ClipboardError('%s must be a list' % name)
    for point in value:
        if not (isinstance(point, list) and len(point) == 2 and all(_is_number(x) for x in point)):
            raise ClipboardError('%s must contain (x, y) number pairs' % name)


def _check_element(model, codes):
    if not isinstance(model, dict):
        raise ClipboardError('Element model must be an object')
    code = model.get('code')
    if not isinstance(code, str) or code not in codes:
        raise ClipboardError('Unknown element code %r' % (code,))
    for key in ('x', 'y'):
        if not _is_number(model.get(key)):
            raise ClipboardError('Element %s: %s must be a number' % (code, key))
    if model.get('orientation') not in ORIENTATIONS:
        raise ClipboardError('Element %s: invalid orientation' % code)
    _check_point_list(model.get('ports'), 'Element %s: ports' % code)
    fields = model.get('fields')
    if not isinstance(fields, dict):
        raise ClipboardError('Element %s: fields must be an object' % code)
    for field_code, field in fields.items():
        if not (isinstance(field, dict) and 'value' in field and isinstance(field.get('type'), str)):
            raise ClipboardError('Element %s: invalid field %r' % (code, field_code))
    if code == 'element_wire':
        _check_point_list(model.get('points'), 'Wire points')
    elif code == 'element_assembly':
        for key in ('element_rect_width', 'element_rect_height'):
            if not _is_number(model.get(key)):
                raise ClipboardError('Assembly: %s must be a number' % key)
        children = model.get('children_codes')
        if not (isinstance(children, list) and all(
                isinstance(child, list) and len(child) == 2
                and all(isinstance(x, int) and not isinstance(x, bool) for x in child)
                for child in children)):
            raise ClipboardError('Assembly: invalid children')


def decode_elements(text, codes):
    """Validate clipboard ``text``; returns ``(element_models, assembly_dict)``.

    ``codes``: element codes that may be pasted. Raises
    :class:`ClipboardError` for anything that is not a valid payload."""
    if not isinstance(text, str) or len(text) > MAX_TEXT_LENGTH:
        raise ClipboardError('No element data in clipboard')
    try:
        payload = json.loads(text)
    except (ValueError, RecursionError):
        raise ClipboardError('No element data in clipboard') from None
    if not isinstance(payload, dict) or payload.get('format') != CLIPBOARD_FORMAT:
        raise ClipboardError('No element data in clipboard')
    if payload.get('version') != CLIPBOARD_VERSION:
        raise ClipboardError('Unsupported clipboard version %r' % (payload.get('version'),))
    models = payload.get('elements')
    if not isinstance(models, list) or not models or len(models) > MAX_ELEMENTS:
        raise ClipboardError('Clipboard must contain 1 to %d elements' % MAX_ELEMENTS)
    for model in models:
        _check_element(model, codes)
    assemblies = payload.get('assemblies', {})
    if not isinstance(assemblies, dict):
        raise ClipboardError('Invalid assembly data')
    assembly_dict = {}
    for key, children in assemblies.items():
        try:
            index = int(key)
        except ValueError:
            raise ClipboardError('Invalid assembly index %r' % key) from None
        if not 0 <= index < len(models) or models[index]['code'] != 'element_assembly':
            raise ClipboardError('Assembly index %r is not an assembly' % key)
        if not (isinstance(children, list) and all(
                isinstance(child, int) and not isinstance(child, bool)
                and 0 <= child < len(models) for child in children)):
            raise ClipboardError('Invalid assembly children for %r' % key)
        assembly_dict[index] = children
    # Every pasted assembly needs its (possibly empty) children list
    for index, model in enumerate(models):
        if model['code'] == 'element_assembly':
            assembly_dict.setdefault(index, [])
    return models, assembly_dict
