#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pango_text
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

"""PangoCairo text backend for the legacy GTK UI.

Drawing is the pre-M2 ``misc.draw_text`` unchanged, so screen, print and
PDF output of the GTK application keep their appearance. Geometry queries measure
on an identity-scaled context; while rendering, text is measured on the
output context as before (see :mod:`gelectrical.symbols.text`).
"""

import cairo
import gi
gi.require_version('Pango', '1.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Pango, PangoCairo

from ..core.style import hex2rgb
from ..symbols.text import TextBackend


class PangoTextBackend(TextBackend):
    """Text with PangoCairo"""

    name = 'pango'

    def __init__(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        self._measure_context = cairo.Context(surface)
        self._cache = dict()

    @staticmethod
    def _layout(context, text, fontname, fontsize, fontweight):
        layout = PangoCairo.create_layout(context)
        font = Pango.FontDescription(fontname + " " + str(fontsize))
        font.set_weight(fontweight)
        layout.set_font_description(font)
        layout.set_text(text)
        return layout

    def measure_text(self, text, fontname, fontsize, fontweight, context=None):
        if context is not None:
            # Rendering: measure on the output context (pre-M2 behaviour)
            layout = self._layout(context, text, fontname, fontsize, fontweight)
            (width, height) = layout.get_size()
            return (Pango.units_to_double(width), Pango.units_to_double(height))
        key = (text, fontname, fontsize, fontweight)
        if key not in self._cache:
            layout = self._layout(self._measure_context, text, fontname, fontsize, fontweight)
            (width, height) = layout.get_size()
            self._cache[key] = (Pango.units_to_double(width), Pango.units_to_double(height))
        return self._cache[key]

    def draw_text(self, context, text, x, y, color, fontname, fontsize, fontweight, alignment):
        """Draw text using Pango"""
        context.save()
        context.translate(x,y)
        (r,g,b,a) = hex2rgb(color)
        context.set_source_rgba(r, g, b, a)
        layout = self._layout(context, text, fontname, fontsize, fontweight)
        # Modify coordinates for alignment
        (width, height) = layout.get_size()
        w = Pango.units_to_double(width)
        h = Pango.units_to_double(height)
        if alignment == 'center': 
            layout.set_alignment(Pango.Alignment.CENTER)
            dx = -w/2
        elif alignment == 'right':
            layout.set_alignment(Pango.Alignment.RIGHT)
            dx = -w
        else:
            layout.set_alignment(Pango.Alignment.LEFT)
            dx = 0
        context.translate(dx,0)
        PangoCairo.show_layout(context, layout)
        context.restore()

        return (x+dx, y, w, h)
