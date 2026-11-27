#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# constants
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

"""Engine constants: program identity, element-code groups, units, paper sizes,
analysis modes, graph types and file version.

Immutable values only. Process-wide drawing style (colours, fonts) that the
GTK application changes at start-up lives in :mod:`gelectrical.core.style`.
"""

# Program name
PROGRAM_NAME = 'GElectrical'
PROGRAM_AUTHOR = 'kavilgroup'
PROGRAM_VER = '1'
APPID = "com.kavilgroup.gelectrical"
# Error codes used for displaying info in main window
ERROR = -1
WARNING = -2
OK = 0
INFO = 0
# Default stroke widths
STROKE_WIDTH_NORMAL = 0.5/0.3527
STROKE_WIDTH_THIN = 0.25/0.3527
STROKE_WIDTH_THICK = 0.7/0.3527
STROKE_WIDTH_EXTRATHICK = 1.4/0.3527
STROKE_WIDTH_GRID = 1
STROKE_WIDTH_SELECTED = 3
STROKE_WIDTH_SELECTION_BAND = 2
RECTANGLE_RADIUS = 5
# Timeout for killing Latex subprocess
PROCESS_TIMEOUT = 300 # 5 minutes
# Timeout of auto hiding message
MESSAGE_TIMEOUT = 10
# String used for checking file version
PROJECT_FILE_VER = 'GELECTRICAL_FILE_REFERENCE_VER_0'
# Default settings
PAGE_WIDTH = 420  # for A3
PAGE_HEIGHT = 297  # for A3
GRID_WIDTH = 16
SELECT_PORT_RECT = 16
# Font weights (numeric values of Pango.Weight.MEDIUM and Pango.Weight.HEAVY)
SCHEM_FONT_WEIGHT = 500
SCHEM_FONT_WEIGHT_BOLD = 900
SELECT_DRAW_PATTERN = (30,10)
WIRE_ADD_DRAW_PATTERN = (5,5)
GROUP_DRAW_PATTERN = (20,5,5,5)
FIELD_CAPTION_WIDTH = 100
FIELD_DIALOG_CAPTION_WIDTH = 300
FIELD_UNIT_WIDTH = 25
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 900
# Status codes for drawing view
MODE_DEFAULT = 0
MODE_SELECTION = 1
MODE_INSERT = 2
MODE_ADD_WIRE = 3
# Graph codes
## graph types
GRAPH_DATATYPE_FREE = 0
GRAPH_DATATYPE_PROFILE = 1
GRAPH_DATATYPE_POLYGON= 2
GRAPH_DATATYPE_MARKER = 3
## graph settings
GRAPH_LOAD_TIME_LIMITS = (0,23,1)
GRAPH_LOAD_CURRENT_LIMITS = (0,1.5,0.05)
GRAPH_PROT_TIME_LIMITS = (0.01,3600,60,'log')
GRAPH_PROT_CURRENT_LIMITS = (1,100e3,100,'log')
GRAPH_PROT_CURRENT_LIMITS_G = (0.01,10e3,100,'log')
GRAPH_COLORS = ('#ef2929', '#F7BD03', '#729fcf', '#a40000', '#CF9033', '#204a87', '#4e9a06', '#ce5c00')
# Power model types
POWER_MODEL_POWERFLOW = 0
POWER_MODEL_LINEFAULT = 1
POWER_MODEL_GROUNDFAULT = 2
# Classification of elements
ADVANCED_ELEMENTS = ('element_asymmetric_load', 'element_ward', 'element_xward',
                     'element_transformer3w', 'element_impedance', 'element_shunt')
REFERENCE_CODES = ('element_reference', 'element_reference_box')
LOADPROFILE_CODES = ('element_load', 'element_asymmetric_load', 'element_single_phase_load', 
                     'element_staticgenerator', 'element_single_phase_staticgenerator', 'element_async_motor',
                     'element_async_motor_3ph', 'element_async_motor_1ph')
LINE_ELEMENT_CODES = ('element_line', 'element_line_cable', 'element_line_custom', 'element_line_bus')
TRAFO_ELEMENT_CODES = ('element_transformer', 'element_transformer3w')
MOTOR_ELEMENT_CODES = ('element_async_motor_3ph', 'element_async_motor_1ph')
LOAD_ELEMENT_CODES = ('element_load', 'element_asymmetric_load', 'element_single_phase_load', 'element_async_motor_3ph', 'element_async_motor_1ph')
SWITCH_ELEMENT_CODES = ('element_switch', 'element_circuitbreaker', 'element_fuse', 'element_contactor')
PROTECTION_ELEMENT_CODES = ('element_circuitbreaker', 'element_fuse', 'element_contactor')
DAMAGE_ELEMENT_CODES = ('element_async_motor_3ph', 'element_async_motor_1ph','element_line','element_line_cable','element_line_custom', 'element_line_bus','element_transformer')
SUPPLY_ELEMENT_CODES = ('element_grid', 'element_generator', 'element_staticgenerator', 'element_single_phase_staticgenerator')
DISPLAY_ELEMENT_CODES = ('element_display_node', )
NON_ELEMENT_CODES  = (*REFERENCE_CODES, *DISPLAY_ELEMENT_CODES, 'element_display_text', 'element_wire', 'element_assembly')
# Defaults (template; use default_load_profile() for a project's own copy)
DEFAULT_LOAD_PROFILE = {'load_prof_1': ['Flat', [{'mode':GRAPH_DATATYPE_PROFILE, 'title':'Default', 'xval':[0,23], 'yval':[1,1]}]],}
# Constants
PI = 3.141593
M = 8  # Multiplier to be used in drawings
POINT_TO_MM = 0.3527
# Paper sizes in mm, (width, height, (width fold marks), (height fold marks))
paper_sizes = {'A4 Landscape': (297, 210),
               'A4 Portrait': (210, 297),
               'A3': (420, 297),
               'A2': (594, 420),
               'A1': (841, 594),
               'A0': (1189, 841), }
# Field sources used by report tables
ELEMENT_FIELD = 0
ELEMENT_RESULT = 1
ELEMENT_PLACEHOLDER = 2


def default_load_profile():
    """Return a new copy of the default load profiles (no shared state, D4)."""
    import copy
    return copy.deepcopy(DEFAULT_LOAD_PROFILE)
