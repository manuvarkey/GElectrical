#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
# 

import logging, copy
from math import sin, cos, acos, asin, exp, log, log10

# local files import
from ..core import constants, style
from ..core.paths import abs_path
from .element import ElementModel

# Get logger object
log = logging.getLogger(__name__) 


class DisplayElementNode(ElementModel):
    """Class for rendering cross reference elements"""

    code = 'element_display_node'
    name = 'Network Node'
    group = ''
    icon = ''
    
    def __init__(self, cordinates=(0,0), ref='', **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [(1,1)]
        self.fields = {'ref':     self.get_field_dict('str', 'Node ID', '', ref, status_inactivate=True)}
        self.text_model = [[(1,1-style.SCHEM_FONT_SPACING/constants.M/2), "${ref}", True, style.SCHEM_FONT_SIZE, constants.SCHEM_FONT_WEIGHT, 'center'],]
        self.schem_model = [['RECT', (0,0), 2,2, True, []],]
    
    def get_symbol_layers(self):
        return [('schem', self.schem_model, style.COLOR_OVERLAY_BG),
                ('text', self.text_model, style.COLOR_OVERLAY_TEXT)]


class DisplayElementText(ElementModel):
    """Class for rendering cross reference elements"""
    
    code = 'element_display_text'
    name = 'Text Display Element'
    group = 'Miscellaneous'
    icon = abs_path('icons', 'display-text.svg')
    tooltip = """<b>Text Display Element</b>"""
    
    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [(0,0)]
        self.fields = {'text'       : self.get_field_dict('multiline_str', 'Text', '', 'Notes:\n', status_floating=True),
                       'background' : self.get_field_dict('bool', 'Fill', '', True, status_floating=True),
                       'border'     : self.get_field_dict('bool', 'Border', '', False, status_floating=True)}
        self.text_model = [[(0.5,0.5), "${text}", True, style.SCHEM_FONT_SIZE, constants.SCHEM_FONT_WEIGHT, 'left'],]
        self.schem_model = []
    
    def get_symbol_layers(self):
        """Text, then optional background and border sized to the text"""
        from ..symbols.geometry import model_size, schem_extents
        layers = [('schem', self.schem_model, None), ('text', self.text_model, None)]
        if self.fields['border']['value'] or self.fields['background']['value']:
            model_width, model_height = model_size(self, schem_extents(self.schem_model),
                                                   self.get_text_extents(self.text_model))
            width = model_width + 1*constants.M
            height = model_height + 1*constants.M
            if self.fields['background']['value']:
                schem_model_border = [['RECT', (0,0), width/constants.M, height/constants.M, True, []]]
                layers.append(('schem', schem_model_border, style.COLOR_OVERLAY_BG))
            if self.fields['border']['value']:
                schem_model_border = [['RECT', (0,0), width/constants.M, height/constants.M, False, [], 'thin']]
                layers.append(('schem', schem_model_border, None))
        return layers


        
