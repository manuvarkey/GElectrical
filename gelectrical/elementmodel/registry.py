#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# registry
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

"""Element registry: the single ``code -> class`` map of placeable elements.

Replaces the dictionary built inside the GTK main window (D14). The order is
the legacy registration order (palette and renumbering iterate it).
``element_async_motor`` (``generator.Motor``) stays unregistered as before.
"""

from ..core import constants
from . import (switch, busbar, grid, transformer, load, line, impedance, shunt, ward,
               generator, reference, displayelements, elementassembly, wire)

_ELEMENT_CLASSES = (
    switch.Switch,
    switch.Fuse,
    switch.CircuitBreaker,
    switch.Contactor,
    switch.ChangeOver,
    busbar.BusBar,
    grid.Grid,
    reference.Reference,
    reference.ReferenceBox,
    transformer.Transformer,
    transformer.Transformer3w,
    load.Load,
    load.AsymmetricLoad,
    load.SinglePhaseLoad,
    line.Line,
    line.LTCableIEC,
    line.LTCableCustom,
    line.BusTrunking,
    impedance.Impedance,
    impedance.Inductance,
    shunt.ShuntCapacitor,
    generator.Generator,
    load.Motor3ph,
    load.Motor1ph,
    displayelements.DisplayElementNode,
    generator.StaticGenerator,
    generator.SinglePhaseStaticGenerator,
    ward.Ward,
    ward.XWard,
    shunt.Shunt,
    displayelements.DisplayElementText,
)

ELEMENT_MODELS = {cls.code: cls for cls in _ELEMENT_CLASSES}

# Structural element classes created by the drawing model, not from the palette
STRUCTURAL_MODELS = {elementassembly.ElementAssembly.code: elementassembly.ElementAssembly,
                     wire.Wire.code: wire.Wire}


def get_element_models():
    """Return a new ``code -> class`` dictionary of registered elements"""
    return dict(ELEMENT_MODELS)

def get_element_class(code):
    """Class for ``code`` (registered or structural); KeyError if unknown"""
    if code in ELEMENT_MODELS:
        return ELEMENT_MODELS[code]
    return STRUCTURAL_MODELS[code]

def palette_entries(advanced_mode=False):
    """(code, name, group, icon, tooltip) of elements shown in the palette"""
    entries = []
    for code, model in ELEMENT_MODELS.items():
        if advanced_mode is False and code in constants.ADVANCED_ELEMENTS:
            continue
        if model.group and model.name and model.icon:
            entries.append((code, model.name, model.group, model.icon, model.tooltip))
    return entries

def is_advanced(code):
    return code in constants.ADVANCED_ELEMENTS
