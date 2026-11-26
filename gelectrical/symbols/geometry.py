#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# geometry
#
#  Copyright 2020 Manu Varkey <manuvarkey@gmail.com>
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

"""Symbol geometry: schematic and text extents of elements, without drawing.

Coordinates in ``schem_model`` and ``text_model`` are multiples of ``M``
(drawing units, angles in degrees); extents are element-local rectangles
(x, y, w, h) before rotation. Text sizes come from the active text backend
(:mod:`gelectrical.symbols.text`), measured on an identity-scaled context.

Schematic model reference::

    [['LINE',(x0,y0),(x1,y1), (d1,d2,...), <'normal'/'thick'/'thin'>],
     ['CURVE',(x0,y0),(x1,y2),(x3,y3),(x4,y4), (d1,d2,...), <'normal'/'thick'/'thin'>],
     ['ARC', (x0,y0), r, t0, t1, (d1,d2,...), <'normal'/'thick'/'thin'>],
     ['CIRCLE', (x0,y0), r, True/False, (d1,d2,...), <'normal'/'thick'/'thin'>],
     ['RECT', (x0,y0), w, h, True/False, (d1,d2,...), <'normal'/'thick'/'thin'>],
     ['PATH', (x0,y0), True/False, (d1,d2,...), 'normal'/'thick'/'thin', [['LINE', (dx1,dy1)],
                                                                          ['CURVE', (dx0,dy0),(dx1,dy1),(dx2,dy2)],
                                                                          ['ARC', (x0,y0), r, t0, t1]]],
      ...]

Text model reference (``None`` as y: one line below the previous text)::

    [[(x,y), Expr, display True/False, [size, [weight, [alignment]]]],
      ...]
"""

from math import sin, cos

from ..core import constants, style
from ..core.geometry import rect_from_points, region_extents
from .formatter import format_label
from .text import measure_text


def schem_extents(schem_model):
    """Extents of every item of a schematic model (as the legacy renderer)"""
    M = constants.M
    PI = constants.PI
    Ms = lambda x: [i*M for i in x]
    extents = []
    for item in schem_model:
        if item[0] == 'LINE':
            extents.append(rect_from_points(Ms(item[1]), Ms(item[2])))
        elif item[0] == 'CURVE':
            extents.append(rect_from_points(Ms(item[1]), Ms(item[2]), Ms(item[3]), Ms(item[4])))
        elif item[0] == 'ARC':
            extents.append(rect_from_points(
                (Ms(item[1])[0]+M*item[2]*cos(item[3]*PI/180), Ms(item[1])[1]+M*item[2]*sin(item[3]*PI/180)),
                (Ms(item[1])[0]+M*item[2]*cos(item[4]*PI/180), Ms(item[1])[1]+M*item[2]*sin(item[4]*PI/180))))
        elif item[0] == 'CIRCLE':
            extents.append((Ms(item[1])[0]-M*item[2], Ms(item[1])[1]-M*item[2], 2*M*item[2], 2*M*item[2]))
        elif item[0] == 'RECT':
            extents.append((*Ms(item[1]), M*item[2], M*item[3]))
        elif item[0] == 'PATH':
            for subitem in item[5]:
                if subitem[0] == 'LINE':
                    extents.append(rect_from_points(Ms(item[1]), Ms(subitem[1])))
                elif subitem[0] == 'CURVE':
                    extents.append(rect_from_points(Ms(item[1]), Ms(subitem[1]), Ms(subitem[2]), Ms(subitem[3])))
                elif subitem[0] == 'ARC':
                    extents.append(rect_from_points(
                        (Ms(subitem[1])[0]+M*subitem[2]*cos(subitem[3]*PI/180), Ms(subitem[1])[1]+M*subitem[2]*sin(subitem[3]*PI/180)),
                        (Ms(subitem[1])[0]+M*subitem[2]*cos(subitem[4]*PI/180), Ms(subitem[1])[1]+M*subitem[2]*sin(subitem[4]*PI/180))))
    return extents


def text_items(element, text_model):
    """Placed labels of a text model: list of dicts with the drawing position
    (x, y, alignment), font, the formatted text and its extents (x0, y0, w, h)"""
    items = []
    values = element.get_field_value_dict()
    y_calc = 0
    for model in text_model:
        size = style.SCHEM_FONT_SIZE
        weight = constants.SCHEM_FONT_WEIGHT
        alignment = 'left'
        if len(model) == 3:
            ((x,y), expr, display_value) = model
        elif len(model) == 4:
            ((x,y), expr, display_value, size) = model
        elif len(model) == 5:
            ((x,y), expr, display_value, size, weight) = model
        else:
            ((x,y), expr, display_value, size, weight, alignment) = model
        if display_value:
            y_calc = constants.M*y if y is not None else y_calc + style.SCHEM_FONT_SPACING  # calculate y_calc (set or auto increment)
            text = format_label(expr, values)
            (w, h) = measure_text(text, style.SCHEM_FONT_FACE, size, weight)
            if alignment == 'center':
                dx = -w/2
            elif alignment == 'right':
                dx = -w
            else:
                dx = 0
            items.append({'text': text, 'x': constants.M*x, 'y': y_calc, 'size': size,
                          'weight': weight, 'alignment': alignment,
                          'extents': (constants.M*x + dx, y_calc, w, h)})
    return items


def text_extents(element, text_model):
    return [item['extents'] for item in text_items(element, text_model)]


def model_size(element, schem_extends, text_extends):
    """(width, height) of an element from its ports and extents (legacy
    ``modify_extends``: one unit is added to every extent for rounding)"""
    M = constants.M
    rects = []
    for port in element.ports:
        rects.append(rect_from_points((0,0), (M*port[0], M*port[1])))
    for x,y,w,h in schem_extends:
        rects.append((int(x), int(y), int(w)+1, int(h)+1))
    for x,y,w,h in text_extends:
        rects.append((int(x), int(y), int(w)+1, int(h)+1))
    (_x, _y, width, height) = region_extents(rects)
    return width, height


def layout_layers(element, layers):
    """Extents of drawn symbol layers. Like the legacy renderer, each
    'schem' layer replaces the schematic extents and each 'text' layer the
    text extents; returns (schem_extends, text_extends)."""
    schem_extends = []
    text_extends = []
    for kind, model, _color in layers:
        if kind == 'schem':
            schem_extends = schem_extents(model)
        elif kind == 'text':
            text_extends = text_extents(element, model)
    return schem_extends, text_extends


def layout_element(element):
    """Compute and store the extents and size of ``element``"""
    layers = element.get_symbol_layers()
    schem_extends, text_extends = layout_layers(element, layers)
    element.schem_extends = schem_extends
    element.text_extends = text_extends
    if not element.fixed_extents:
        element.model_width, element.model_height = model_size(element, schem_extends, text_extends)
    element.extents_stale = False
    return layers
