# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Element catalogue: element types, palette groups and field schemas,
generated from the element classes (single source of field definitions)"""

from gelectrical.core.fields import new_project_settings
from gelectrical.elementmodel import registry as element_registry

from .. import dto
from ..protocol import not_found
from ..registry import runtime_method
from .common import require_bool, require_str

_CACHE = {}


def _element_type(code):
    if code not in _CACHE:
        cls = element_registry.get_element_class(code)
        if code in element_registry.STRUCTURAL_MODELS:
            element = cls()
        else:
            element = cls(project_settings=new_project_settings())
        _CACHE[code] = dto.element_type(code, cls, element)
    return _CACHE[code]


@runtime_method('catalog.element_types')
def element_types(ctx, advanced=False):
    """Placeable element types in palette order (advanced elements on request)"""
    require_bool(advanced, 'advanced')
    palette = element_registry.palette_entries(advanced_mode=advanced)
    groups = []
    for code, name, group, icon, tooltip in palette:
        if group not in groups:
            groups.append(group)
    return {'groups': groups, 'types': [_element_type(code) for code, *_ in palette]}


@runtime_method('catalog.element_type')
def element_type(ctx, code):
    """One element type with field schemas and ports"""
    require_str(code, 'code', allow_empty=False, max_length=100)
    try:
        return _element_type(code)
    except KeyError:
        raise not_found('Unknown element type %r' % code, field='code') from None
