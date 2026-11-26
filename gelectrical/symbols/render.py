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
