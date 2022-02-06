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
from mako.template import Template as ExprTemplate
from gi.repository import Gtk, Gdk
import cairo

# local files import
from .. import misc
from .element import ElementModel

# Get logger object
log = logging.getLogger(__name__) 


class ElementAssembly(ElementModel):
    """Class for rendering element assemblies"""
    def __init__(self, children_codes=None, children=None):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_assembly'
        self.name = 'Assembly'
        self.icon = misc.abs_path('icons', 'assembly.svg')
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
        
          
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        
        # Render text
        self.text_model = [[(self.element_rect_width/misc.M + 1, (misc.SCHEM_FONT_SPACING - misc.SCHEM_FONT_SIZE)/misc.M), "${name}, ${ref}", True],
                           [(self.element_rect_width/misc.M + 1, None), "${text1}", True],
                           [(self.element_rect_width/misc.M + 1, None), "${text2}", True],
                           [(self.element_rect_width/misc.M + 1, None), "${text3}", True]]
        self.render_text(context, self.text_model)
        # Render schem
        (tx, ty, tw, th) = self.text_extends[0]
        self.schem_model = [['RECT',(0, 0), 
                             (self.element_rect_width + tw)/misc.M + 2, 
                             self.element_rect_height/misc.M, 
                             False, misc.GROUP_DRAW_PATTERN, 'thin']]
        self.render_model(context, self.schem_model)
        
        # Post processing
        self.modify_extends()
        
    def check_overlap(self, rect):
        """Overload for limiting overlap to unused area"""
        # Modify extends
        assembly_rect = cairo.RectangleInt(*self.get_dimensions())
        assembly_rect.x += (self.element_rect_width + 10)
        assembly_rect.width -= self.element_rect_width
        element_region = cairo.Region(assembly_rect)
        if element_region.contains_rectangle(rect) in (cairo.RegionOverlap.IN, cairo.RegionOverlap.PART):
            return True
        else:
            return False
        
    def get_model(self):
        """Get storage model"""
        # Get reference for child
        return {'code': self.code,
                'x': self.x,
                'y': self.y,
                'orientation': self.orientation,
                'ports': copy.deepcopy(self.ports),
                'fields': copy.deepcopy(self.fields),
                'element_rect_width': self.element_rect_width,
                'element_rect_height': self.element_rect_height,
                'children_codes': self.element_rect_height,
                'children_codes': self.children_codes}
    
    def set_model(self, model):
        """Set storage model"""
        if model['code'] == self.code:
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            self.fields = copy.deepcopy(model['fields'])
            self.element_rect_width = model['element_rect_width']
            self.element_rect_height = model['element_rect_height']
            self.children_codes = model['children_codes']
        
    def set_children(self, children_codes, children=None):
        """Setup model"""
        
        self.children_codes = children_codes
        if children:
            rects = []
            for child in children:
                rects.append(cairo.RectangleInt(*child.get_dimensions()))
            element_region = cairo.Region(rects)
            element_rect = element_region.get_extents()
            self.x = element_rect.x - 10
            self.y = element_rect.y - 10
            self.element_rect_width = element_rect.width + 20
            self.element_rect_height = element_rect.height + 20
        
    def get_children(self):
        return self.children_codes
        
        
