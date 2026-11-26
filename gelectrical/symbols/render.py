#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# render
#
#  Copyright 2014 Manu Varkey <manuvarkey@gmail.com>
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

"""Cairo drawing primitives for schematic symbols (headless: pycairo only)."""

import math

from ..core.constants import STROKE_WIDTH_NORMAL, SCHEM_FONT_WEIGHT
from ..core.style import COLOR_NORMAL, hex2rgb
from .text import get_text_backend


def set_source_color(context, color):
    (r,g,b,a) = hex2rgb(color)
    context.set_source_rgba(r, g, b, a)

def draw_rectangle(context, x, y, w, h, radius=0, color=COLOR_NORMAL, line_style='solid', dash_pattern=[10,10], stroke_width=STROKE_WIDTH_NORMAL, fill=False):
    (r,g,b,a) = hex2rgb(color)
    context.save()
    context.set_source_rgba(r, g, b, a)
    context.set_line_width(stroke_width)
    if line_style == 'solid':
        context.arc(x+radius, y+radius, radius, math.pi, 3*math.pi/2)
        context.arc(x+w-radius, y+radius, radius, 3*math.pi/2, 0)
        context.arc(x+w-radius, y+h-radius, radius, 0, math.pi/2)
        context.arc(x+radius, y+h-radius, radius, math.pi/2, math.pi)
        context.close_path()
        if fill:
            context.fill()
        else:
            context.stroke()
    elif line_style == 'dashed':
        context.set_dash(dash_pattern)
        context.arc(x+radius, y+radius, radius, math.pi, 3*math.pi/2)
        context.arc(x+w-radius, y+radius, radius, 3*math.pi/2, 0)
        context.arc(x+w-radius, y+h-radius, radius, 0, math.pi/2)
        context.arc(x+radius, y+h-radius, radius, math.pi/2, math.pi)
        context.close_path()
        context.stroke()
    context.restore()
    
def draw_line(context, x0, y0, x1, y1, color=COLOR_NORMAL, dash_pattern=[], stroke_width=STROKE_WIDTH_NORMAL):
    (r,g,b,a) = hex2rgb(color)
    context.save()
    context.set_source_rgba(r, g, b, a)
    context.set_line_width(stroke_width)
    context.set_dash(dash_pattern)
    context.move_to(x0,y0)
    context.line_to(x1,y1)
    context.stroke()
    context.restore()

def draw_text(context, text, x, y, color=COLOR_NORMAL, fontname='Sans', fontsize=12, fontweight=SCHEM_FONT_WEIGHT, alignment='left'):
    """Draw text with the active text backend; return (x0, y0, width, height)"""
    return get_text_backend().draw_text(context, text, x, y, color, fontname, fontsize, fontweight, alignment)


# Element rendering

def _set_line_width(context, width_code):
    from ..core import constants
    if width_code == 'thin':
        context.set_line_width(constants.STROKE_WIDTH_THIN)
    elif width_code == 'thick':
        context.set_line_width(constants.STROKE_WIDTH_THICK)
    elif width_code == 'thicker':
        context.set_line_width(constants.STROKE_WIDTH_EXTRATHICK)
    else:
        context.set_line_width(constants.STROKE_WIDTH_NORMAL)

def _element_transform(context, element):
    import cairo
    context.translate(element.x, element.y)
    if element.orientation == 'horizontal':
        matrix = cairo.Matrix(0, -1, 1, 0, 0, 0)
        context.transform(matrix)

def render_schem(context, element, schem_model, color):
    """Draw a schematic model of ``element`` (see symbols.geometry)"""
    import cairo
    from ..core import constants
    M = constants.M
    PI = constants.PI
    Ms = lambda x: [i*M for i in x]
    context.save()
    set_source_color(context, color)
    context.set_line_width(constants.STROKE_WIDTH_NORMAL)
    context.set_line_cap(cairo.LINE_CAP_ROUND)
    _element_transform(context, element)
    for item in schem_model:
        if item[0] == 'LINE':
            _set_line_width(context, 'normal' if len(item) == 4 else item[4])
            context.set_dash(item[3])
            context.move_to(*Ms(item[1]))
            context.line_to(*Ms(item[2]))
            context.stroke()
        elif item[0] == 'CURVE':
            _set_line_width(context, 'normal' if len(item) == 6 else item[6])
            context.set_dash(item[5])
            context.move_to(*Ms(item[1]))
            context.curve_to(*Ms(item[2]), *Ms(item[3]), *Ms(item[4]))
            context.stroke()
        elif item[0] == 'ARC':
            _set_line_width(context, 'normal' if len(item) == 6 else item[6])
            context.set_dash(item[5])
            context.arc(*Ms(item[1]), M*item[2], item[3]*PI/180, item[4]*PI/180)
            context.stroke()
        elif item[0] == 'CIRCLE':
            _set_line_width(context, 'normal' if len(item) == 5 else item[5])
            context.set_dash(item[4])
            context.arc(*Ms(item[1]), M*item[2], 0, 2*PI)
            context.close_path()
            if item[3]:
                context.fill()
            else:
                context.stroke()
        elif item[0] == 'RECT':
            _set_line_width(context, 'normal' if len(item) == 6 else item[6])
            context.set_dash(item[5])
            context.rectangle(*Ms(item[1]), M*item[2], M*item[3])
            if item[4]:
                context.fill()
            else:
                context.stroke()
        elif item[0] == 'PATH':
            _set_line_width(context, item[4])
            context.set_dash(item[3])
            context.move_to(*Ms(item[1]))
            for subitem in item[5]:
                if subitem[0] == 'LINE':
                    context.rel_line_to(*Ms(subitem[1]))
                elif subitem[0] == 'CURVE':
                    context.rel_curve_to(*Ms(subitem[1]), *Ms(subitem[2]), *Ms(subitem[3]))
                elif subitem[0] == 'ARC':
                    context.arc(*Ms(subitem[1]), M*subitem[2], subitem[3]*PI/180, subitem[4]*PI/180)
            if item[2]:
                context.close_path()
                context.fill()
            else:
                context.stroke()
    context.restore()

def render_text(context, element, text_model, color):
    """Draw the labels of ``element``"""
    from ..core import style
    from .geometry import text_items
    context.save()
    _element_transform(context, element)
    for item in text_items(element, text_model):
        draw_text(context, item['text'], item['x'], item['y'], color=color,
                  fontname=style.SCHEM_FONT_FACE, fontsize=item['size'],
                  fontweight=item['weight'], alignment=item['alignment'])
    context.restore()

def render_element(context, element):
    """Draw the symbol layers of ``element`` and update its extents"""
    from .geometry import layout_layers, model_size
    from .text import measuring_on
    # Symbol data and extents, with text measured on the output context
    context.save()
    _element_transform(context, element)
    with measuring_on(context):
        layers = element.get_symbol_layers()
        schem_extends, text_extends = layout_layers(element, layers)
    context.restore()
    for kind, model, color in layers:
        if color is None:
            color = element.draw_schem_color
        if kind == 'schem':
            render_schem(context, element, model, color)
        elif kind == 'text':
            render_text(context, element, model, color)
    element.schem_extends = schem_extends
    element.text_extends = text_extends
    if not element.fixed_extents:
        element.model_width, element.model_height = model_size(element, schem_extends, text_extends)
    element.extents_stale = False

def draw_element(context, element, select=False, override_color=None):
    """Draw ``element``; with ``select``, outline it when selected"""
    from ..core import constants
    default_color = element.draw_schem_color
    if override_color:
        element.draw_schem_color = override_color
    render_element(context, element)
    element.draw_schem_color = default_color
    if select == True and element.selected == True:
        (x, y, width, height) = element.get_dimensions()
        draw_rectangle(context,
                       x-0.5*constants.M,
                       y-0.5*constants.M,
                       width+1*constants.M,
                       height+1*constants.M,
                       radius=constants.RECTANGLE_RADIUS,
                       color=element.selected_color,
                       stroke_width=constants.STROKE_WIDTH_SELECTED,
                       line_style='dashed',
                       dash_pattern=[20,5])
