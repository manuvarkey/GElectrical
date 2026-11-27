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
from ..core.geometry import rect_overlaps, region_extents
from ..core.fields import get_fields_trunc
from ..core.paths import abs_path
from .element import ElementModel

# Get logger object
log = logging.getLogger(__name__) 


class ElementAssembly(ElementModel):
    """Class for rendering element assemblies"""

    code = 'element_assembly'
    name = 'Assembly'
    group = ''
    icon = abs_path('icons', 'assembly.svg')

    def __init__(self, children_codes=None, children=None, **kwargs):
        # Global
        ElementModel.__init__(self, (0,0), **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [[0,0]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'A?'),
                       'name':    self.get_field_dict('str', 'Name', '', 'ASSEMBLY'),
                       'text1':    self.get_field_dict('str', 'Text 1', '', ''),
                       'text2':    self.get_field_dict('str', 'Text 2', '', ''),
                       'text3':    self.get_field_dict('str', 'Text 3', '', '')}
        self.text_model = []
        self.schem_model = []
        # Additional Data
        self.element_rect_width = 50
        self.element_rect_height = 50
        self.children_codes = []
        # State variables
        
        if children and children_codes:
            self.set_children(children_codes, children)
        
          
    def get_symbol_layers(self):
        """Labels first; the frame width follows the widest label"""
        self.text_model = [[(self.element_rect_width/constants.M + 1, (style.SCHEM_FONT_SPACING - style.SCHEM_FONT_SIZE)/constants.M), "${name}, ${ref}", True],
                           [(self.element_rect_width/constants.M + 1, None), "${text1}", True],
                           [(self.element_rect_width/constants.M + 1, None), "${text2}", True],
                           [(self.element_rect_width/constants.M + 1, None), "${text3}", True]]
        text_extends = self.get_text_extents(self.text_model)
        (tx0, ty0, tw0, th0) = text_extends[0]
        (tx1, ty1, tw1, th1) = text_extends[1]
        (tx2, ty2, tw2, th2) = text_extends[2]
        (tx3, ty3, tw3, th3) = text_extends[3]
        tw = max(tw0, tw1, tw2, tw3)
        self.schem_model = [['RECT',(0, 0), 
                             (self.element_rect_width + tw)/constants.M + 2, 
                             self.element_rect_height/constants.M, 
                             False, constants.GROUP_DRAW_PATTERN, 'thin']]
        return [('text', self.text_model, None), ('schem', self.schem_model, None)]
        
    def check_overlap(self, rect):
        """Overload for limiting overlap to unused area"""
        # Modify extends
        (x, y, width, height) = self.get_dimensions()
        x += (self.element_rect_width + 10)
        width -= self.element_rect_width
        return rect_overlaps((x, y, width, height), rect)
        
    def get_model(self):
        """Get storage model"""
        # Get reference for child
        return {'code': self.code,
                'x': self.x,
                'y': self.y,
                'orientation': self.orientation,
                'ports': copy.deepcopy(self.ports),
                'fields': get_fields_trunc(self.fields),
                'element_rect_width': self.element_rect_width,
                'element_rect_height': self.element_rect_height,
                'children_codes': self.children_codes}
    
    def set_model(self, model, gid=None):
        """Set storage model"""
        if model['code'] == self.code:
            ElementModel.set_model(self, model, gid)
            self.element_rect_width = model['element_rect_width']
            self.element_rect_height = model['element_rect_height']
            self.children_codes = model['children_codes']
        
    def set_children(self, children_codes, children=None):
        """Setup model"""
        self.children_codes = children_codes
        if children:
            rects = []
            for child in children:
                rects.append(child.get_dimensions())
            (rx, ry, rwidth, rheight) = region_extents(rects)
            self.x = rx - 10
            self.y = ry - 10
            self.element_rect_width = rwidth + 20
            self.element_rect_height = rheight + 20
            self.extents_stale = True
            
    def delete_child(self, child_code):
        """Setup model"""
        if child_code in self.children_codes:
            self.children_codes.remove(child_code)
            
    def add_child(self, child_code):
        """Setup model"""
        self.children_codes.append(child_code)
        
    def get_children(self):
        return self.children_codes
        
        
