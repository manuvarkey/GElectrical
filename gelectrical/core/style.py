#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# style
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

"""Process-wide drawing style: colours and fonts.

The legacy GTK application changes these values at start-up (dark theme,
font settings from the program settings). Engine code reads them at call
time through this module (``style.COLOR_NORMAL``), never by copying them.
Headless use keeps the defaults. Per-session styles arrive with the
application services (M4).
"""

# Default colors for models
COLOR_NORMAL = '#000000'
COLOR_INACTIVE = '#888a85'
COLOR_OVERLAY_BG = '#ad7fa880'
COLOR_OVERLAY_TEXT = '#00000080'
COLOR_GRID = '#00ff00FF'
COLOR_GRID_MINOR = '#00ff0020'
COLOR_SELECTED = '#729fcf'
COLOR_SELECTED_WARNING = '#cc0000'
COLOR_SELECTION_BAND = '#729fcf'
COLOR_PLOT_BG = '#FFFFFF'

# Fonts
SCHEM_FONT_FACE = 'osifont'
SCHEM_FONT_SIZE = 7  # Keep minimum of 7 point (x 0.3527 in mm)
TITLE_FONT_SIZE_SMALL = 6
TITLE_FONT_SIZE = 8
SCHEM_FONT_SPACING = 10
GRAPH_FONT_FACE = 'monospace'
GRAPH_FONT_SIZE = 10
REPORT_FONT_FACE = 'monospace'
REPORT_FONT_SIZE = 10
REPORT_GRAPH_FONT_FACE = 'monospace'
REPORT_GRAPH_FONT_SIZE = 10

# Names that may be changed at run time (forwarded live by gelectrical.misc)
MUTABLE_NAMES = ('COLOR_NORMAL', 'COLOR_INACTIVE', 'COLOR_OVERLAY_BG', 'COLOR_OVERLAY_TEXT',
                 'COLOR_GRID', 'COLOR_GRID_MINOR', 'COLOR_SELECTED', 'COLOR_SELECTED_WARNING',
                 'COLOR_SELECTION_BAND', 'COLOR_PLOT_BG',
                 'SCHEM_FONT_FACE', 'SCHEM_FONT_SIZE', 'TITLE_FONT_SIZE_SMALL', 'TITLE_FONT_SIZE',
                 'SCHEM_FONT_SPACING', 'GRAPH_FONT_FACE', 'GRAPH_FONT_SIZE', 'REPORT_FONT_FACE',
                 'REPORT_FONT_SIZE', 'REPORT_GRAPH_FONT_FACE', 'REPORT_GRAPH_FONT_SIZE')


def set_dark_mode_drawing_values():
    global COLOR_NORMAL, COLOR_OVERLAY_TEXT, COLOR_PLOT_BG
    COLOR_NORMAL = '#FFFFFF'
    COLOR_OVERLAY_TEXT = '#FFFFFF80'
    COLOR_PLOT_BG = '#000000'

def reset_dark_mode_drawing_values():
    global COLOR_NORMAL, COLOR_OVERLAY_TEXT, COLOR_PLOT_BG
    COLOR_NORMAL = '#000000'
    COLOR_OVERLAY_TEXT = '#00000080'
    COLOR_PLOT_BG = '#FFFFFF'

def check_dark_mode():
    return COLOR_NORMAL == '#FFFFFF'

def set_schematic_font(face, size):
    """Set the drawing font and the sizes derived from it."""
    global SCHEM_FONT_FACE, SCHEM_FONT_SIZE, TITLE_FONT_SIZE_SMALL, TITLE_FONT_SIZE, SCHEM_FONT_SPACING
    SCHEM_FONT_FACE = face
    SCHEM_FONT_SIZE = size
    TITLE_FONT_SIZE_SMALL = SCHEM_FONT_SIZE - 1
    TITLE_FONT_SIZE = SCHEM_FONT_SIZE + 1
    SCHEM_FONT_SPACING = int(SCHEM_FONT_SIZE * 1.5)

def rgb2hex(r,g,b,a=None):
    if a:
        return "#{:02x}{:02x}{:02x}{:02x}".format(int(r*255),int(g*255),int(b*255),int(a*255))
    else:
        return "#{:02x}{:02x}{:02x}".format(int(r*255),int(g*255),int(b*255))

def hex2rgb(hexcode):
    if len(hexcode) == 7:
        r = int(hexcode[1:3],16)/255 
        g = int(hexcode[3:5],16)/255
        b = int(hexcode[5:7],16)/255
        a = 1
    elif len(hexcode) == 9:
        r = int(hexcode[1:3],16)/255 
        g = int(hexcode[3:5],16)/255
        b = int(hexcode[5:7],16)/255
        a = int(hexcode[7:9],16)/255
    return (r, g, b, a)
