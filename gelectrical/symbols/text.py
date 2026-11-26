#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# text
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

"""Text measurement and drawing for schematic symbols.

Two interchangeable backends implement :class:`TextBackend`:

* :class:`CairoTextBackend` (default, headless): Cairo "toy" text API. No
  PyGObject; fonts are resolved by Cairo's font backend (fontconfig on Linux).
* ``gelectrical.gtk.pango_text.PangoTextBackend``: PangoCairo, installed by the
  legacy GTK application so that its screen, print and PDF output stay as
  before.

Extents (``measure_text``) are computed on an identity-scaled context, so
element geometry does not depend on the zoom level or the output surface.
Font sizes are in points at 96 dpi like Pango (size 7 = 9.33 drawing units).
The decision and the measured differences are recorded in
docs/architecture/backend.md ("Headless text metrics").
"""

import cairo

# Pango resolves point sizes at 96 dpi on Cairo contexts
POINTS_TO_UNITS = 96/72
# Numeric weight from which the bold face is used (Pango.Weight.BOLD)
BOLD_WEIGHT = 700


class TextBackend:
    """Interface of a text backend"""

    name = 'abstract'

    def measure_text(self, text, fontname, fontsize, fontweight):
        """Return the logical (width, height) of ``text`` in drawing units"""
        raise NotImplementedError

    def draw_text(self, context, text, x, y, color, fontname, fontsize, fontweight, alignment):
        """Draw ``text`` with its top-left (alignment 'left'), top-centre or
        top-right corner at (x, y); return (x0, y0, width, height)"""
        raise NotImplementedError


class CairoTextBackend(TextBackend):
    """Text with the Cairo toy font API (no PyGObject)"""

    name = 'cairo'

    def __init__(self):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
        self._measure_context = cairo.Context(surface)
        self._cache = dict()

    @staticmethod
    def _select_font(context, fontname, fontsize, fontweight):
        weight = cairo.FONT_WEIGHT_BOLD if fontweight >= BOLD_WEIGHT else cairo.FONT_WEIGHT_NORMAL
        context.select_font_face(fontname, cairo.FONT_SLANT_NORMAL, weight)
        context.set_font_size(fontsize*POINTS_TO_UNITS)

    def _line_metrics(self, context, lines):
        ascent, descent, _height, _max_x, _max_y = context.font_extents()
        widths = [context.text_extents(line).x_advance for line in lines]
        return ascent, ascent + descent, widths

    def measure_text(self, text, fontname, fontsize, fontweight):
        key = (text, fontname, fontsize, fontweight)
        if key not in self._cache:
            context = self._measure_context
            context.save()
            self._select_font(context, fontname, fontsize, fontweight)
            lines = text.split('\n')
            _ascent, line_height, widths = self._line_metrics(context, lines)
            context.restore()
            self._cache[key] = (max(widths), line_height*len(lines))
        return self._cache[key]

    def draw_text(self, context, text, x, y, color, fontname, fontsize, fontweight, alignment):
        from .render import set_source_color
        (w, h) = self.measure_text(text, fontname, fontsize, fontweight)
        if alignment == 'center':
            dx = -w/2
        elif alignment == 'right':
            dx = -w
        else:
            dx = 0
        context.save()
        set_source_color(context, color)
        self._select_font(context, fontname, fontsize, fontweight)
        lines = text.split('\n')
        # Line advance and widths from the measuring context (scale independent)
        self._measure_context.save()
        self._select_font(self._measure_context, fontname, fontsize, fontweight)
        ascent, line_height, widths = self._line_metrics(self._measure_context, lines)
        self._measure_context.restore()
        for line_no, (line, width) in enumerate(zip(lines, widths)):
            # Lines are aligned inside the block like Pango layout alignment
            if alignment == 'center':
                line_dx = (w - width)/2
            elif alignment == 'right':
                line_dx = w - width
            else:
                line_dx = 0
            context.move_to(x + dx + line_dx, y + ascent + line_no*line_height)
            context.show_text(line)
        context.new_path()
        context.restore()
        return (x+dx, y, w, h)


_backend = None


def get_text_backend():
    """Return the active text backend (Cairo unless an application set one)"""
    global _backend
    if _backend is None:
        _backend = CairoTextBackend()
    return _backend

def set_text_backend(backend):
    """Install ``backend`` for all later measurement and drawing"""
    global _backend
    _backend = backend

def measure_text(text, fontname, fontsize, fontweight):
    return get_text_backend().measure_text(text, fontname, fontsize, fontweight)
