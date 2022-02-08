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


class Reference(ElementModel):
    """Class for rendering cross reference elements"""
    def __init__(self):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_reference'
        self.name = 'Cross Reference'
        self.group = 'Miscellaneous'
        self.icon = misc.abs_path('icons', 'reference.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [(3,0), (3,6)]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference Code', '', '?'),
                       'sheet':    self.get_field_dict('str', 'Sheet Reference', '', '1'),
                       'title':     self.get_field_dict('str', 'Title', '', ''),
                       'sub_title':     self.get_field_dict('str', 'Sub Title', '', ''),}
        self.text_model = [[(3,3-misc.SCHEM_FONT_SPACING/misc.M), "${ref}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(3,3+(misc.SCHEM_FONT_SPACING-misc.SCHEM_FONT_SIZE)/misc.M), "${sheet}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(7,3-misc.SCHEM_FONT_SPACING/misc.M), "${title}", True],
                           [(7,3+(misc.SCHEM_FONT_SPACING-misc.SCHEM_FONT_SIZE)/misc.M), "${sub_title}", True]]
    
    def render_element(self, context):
        """Render element to context"""
        self.render_text(context, self.text_model)
        (tx1, ty1, tw1, th1) = self.text_extends[2]
        (tx2, ty2, tw2, th2) = self.text_extends[3]
        width = max(tw1, tw2)
        #self.schem_model = [ 
                             #['CIRCLE', (3,3), 3, False, []],
                             #['LINE', (0,3),(7 + width/misc.M,3), []],
                           #]
        if self.fields['title']['value'] or self.fields['sub_title']['value']:
            xe = 7 + width/misc.M
        else:
            xe = 6
        self.schem_model = [ 
                             ['LINE', (3,0),(6,3), []],
                             ['LINE', (3,0),(0,3), []],
                             ['LINE', (3,6),(0,3), []],
                             ['LINE', (3,6),(6,3), []],
                             ['LINE', (0,3),(xe,3), []],
                           ]
        self.render_model(context, self.schem_model)
        # Post processing
        self.modify_extends()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        ports = tuple(tuple(x) for x in self.get_ports_global())
        ports = ports + ((self.fields['ref']['value'],),)
        p0 = code + ':0'
        nodes = ((p0, ports),)
        return nodes
        
    def get_power_model(self, code):
        """Return pandapower model for analysis"""
        power_model = tuple()
        return power_model


class ReferenceBox(Reference):
    """Class for rendering cross reference elements"""
    def __init__(self):
        # Global
        Reference.__init__(self)
        self.code = 'element_reference_box'
        self.name = 'Cross Reference'
        self.group = 'Miscellaneous'
        self.icon = misc.abs_path('icons', 'reference_box.svg')
        self.model_width = 0
        self.model_height = 0
        self.fields = {'ref':       self.get_field_dict('str', 'Reference Code', '', '?'),
                       'sheet':     self.get_field_dict('str', 'Sheet Reference', '', '1'),
                       'title':     self.get_field_dict('str', 'Title', '', ''),
                       'sub_title': self.get_field_dict('str', 'Sub Title', '', ''),
                       'width':   self.get_field_dict('int', 'Bay Width', 'pt', 12)}
        self.set_model_from_param()
        
        
    def render_element(self, context):
        """Render element to context"""
        self.set_model_from_param()
        self.render_text(context, self.text_model)
        self.render_model(context, self.schem_model)
        # Post processing
        self.modify_extends()
        
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
        self.text_model = [[(width/4, h1 - misc.SCHEM_FONT_SPACING/misc.M), "${ref}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(3*width/4, h1 - misc.SCHEM_FONT_SPACING/misc.M), "${sheet}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center']]
        if self.fields['title']['value'] or self.fields['sub_title']['value']:
            self.schem_model.append(['LINE',(0,h1), (width, h1), []])
            self.text_model.append([(0.5, (h1+h2) - misc.SCHEM_FONT_SPACING/misc.M), "${title}", True])
        if self.fields['sub_title']['value']:
            self.schem_model.append(['LINE',(0, h1+h2), (width, h1+h2), []])
            self.text_model.append([(0.5, height - misc.SCHEM_FONT_SPACING/misc.M), "${sub_title}", True])
            
