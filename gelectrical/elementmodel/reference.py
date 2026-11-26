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


class Reference(ElementModel):
    """Class for rendering cross reference elements"""

    code = 'element_reference'
    name = 'Cross Reference'
    group = 'Miscellaneous'
    icon = abs_path('icons', 'reference.svg')
    tooltip = """<b>Cross Reference</b>

Cross reference elements allows connecting different parts of the scheme within/ across sheets.

Use the <b>Link</b> toolbar function to link cross reference elements.
"""

    def __init__(self, **kwargs):
        # Global
        ElementModel.__init__(self, (0,0), **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [(3,0), (3,6)]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference Code', '', 'CR?'),
                       'sheet':    self.get_field_dict('str', 'Sheet Reference', '', '1'),
                       'title':     self.get_field_dict('str', 'Title', '', ''),
                       'sub_title':     self.get_field_dict('str', 'Sub Title', '', ''),}
        self.text_model = [[(3,3-style.SCHEM_FONT_SPACING/constants.M), "${ref}", True, style.SCHEM_FONT_SIZE, constants.SCHEM_FONT_WEIGHT, 'center'],
                           [(3,3+(style.SCHEM_FONT_SPACING-style.SCHEM_FONT_SIZE)/constants.M), "${sheet}", True, style.SCHEM_FONT_SIZE, constants.SCHEM_FONT_WEIGHT, 'center'],
                           [(7,3-style.SCHEM_FONT_SPACING/constants.M), "${title}", True],
                           [(7,3+(style.SCHEM_FONT_SPACING-style.SCHEM_FONT_SIZE)/constants.M), "${sub_title}", True]]
        self.assign_tootltips()
    
    def get_symbol_layers(self):
        """Labels first; the reference line follows the title width"""
        text_extends = self.get_text_extents(self.text_model)
        (tx1, ty1, tw1, th1) = text_extends[2]
        (tx2, ty2, tw2, th2) = text_extends[3]
        width = max(tw1, tw2)
        #self.schem_model = [ 
                             #['CIRCLE', (3,3), 3, False, []],
                             #['LINE', (0,3),(7 + width/constants.M,3), []],
                           #]
        if self.fields['title']['value'] or self.fields['sub_title']['value']:
            xe = 7 + width/constants.M
        else:
            xe = 6
        self.schem_model = [ 
                             ['LINE', (3,0),(6,3), []],
                             ['LINE', (3,0),(0,3), []],
                             ['LINE', (3,6),(0,3), []],
                             ['LINE', (3,6),(6,3), []],
                             ['LINE', (0,3),(xe,3), []],
                           ]
        return [('text', self.text_model, None), ('schem', self.schem_model, None)]
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        ports = tuple(tuple(x) for x in self.get_ports_global())
        ports = ports + ((self.fields['ref']['value'],),)
        p0 = code + ':0'
        nodes = ((p0, ports),)
        return nodes
        


class ReferenceBox(Reference):
    """Class for rendering cross reference elements"""

    code = 'element_reference_box'
    name = 'Cross Reference'
    group = 'Miscellaneous'
    icon = abs_path('icons', 'reference_box.svg')
    tooltip = """<b>Cross Reference</b>

Cross reference elements allows connecting different parts of the scheme within/ across sheets.

Use the <b>Link</b> toolbar function to link cross reference elements.
"""

    def __init__(self, **kwargs):
        # Global
        Reference.__init__(self, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.fields = {'ref':       self.get_field_dict('str', 'Reference Code', '', 'CR?'),
                       'sheet':     self.get_field_dict('str', 'Sheet Reference', '', '1'),
                       'title':     self.get_field_dict('str', 'Title', '', ''),
                       'sub_title': self.get_field_dict('str', 'Sub Title', '', ''),
                       'width':   self.get_field_dict('int', 'Bay Width', 'pt', 12)}
        self.set_model_from_param()
        self.assign_tootltips()        
        
    def get_symbol_layers(self):
        self.set_model_from_param()
        return [('text', self.text_model, None), ('schem', self.schem_model, None)]
        
    # Private functions
    
    def set_model_from_param(self):
        width = self.fields['width']['value']
        h1 = 2
        h2 = 0
        h3 = 0
        if self.fields['title']['value']:
            h2 = h1
        if self.fields['sub_title']['value']:
            h2 = h1
            h3 = h1
        height = h1 + h2 + h3
        self.ports = [(width/2,0), (width/2,height)]
        self.schem_model = [['RECT', (0,0), width, height, False, []],
                            ['LINE',(width/2, 0), (width/2, h1), []]]
        self.text_model = [[(width/4, h1 - style.SCHEM_FONT_SPACING/constants.M), "${ref}", True, style.SCHEM_FONT_SIZE, constants.SCHEM_FONT_WEIGHT, 'center'],
                           [(3*width/4, h1 - style.SCHEM_FONT_SPACING/constants.M), "${sheet}", True, style.SCHEM_FONT_SIZE, constants.SCHEM_FONT_WEIGHT, 'center']]
        if self.fields['title']['value'] or self.fields['sub_title']['value']:
            self.schem_model.append(['LINE',(0,h1), (width, h1), []])
            self.text_model.append([(0.5, (h1+h2) - style.SCHEM_FONT_SPACING/constants.M), "${title}", True])
        if self.fields['sub_title']['value']:
            self.schem_model.append(['LINE',(0, h1+h2), (width, h1+h2), []])
            self.text_model.append([(0.5, height - style.SCHEM_FONT_SPACING/constants.M), "${sub_title}", True])
            
