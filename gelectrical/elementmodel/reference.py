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
        self.ports = [(2.5,0), (2.5,5)]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference Code', '', '?'),
                       'sheet':    self.get_field_dict('str', 'Sheet Reference', '', '1/A1'),
                       'title':     self.get_field_dict('str', 'Title', '', ''),
                       'sub_title':     self.get_field_dict('str', 'Sub Title', '', ''),}
        self.text_model = [[(2.5,2.5-misc.SCHEM_FONT_SPACING/misc.M), "${ref}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(2.5,2.5+(misc.SCHEM_FONT_SPACING-misc.SCHEM_FONT_SIZE)/misc.M), "${sheet}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(6,2.5-misc.SCHEM_FONT_SPACING/misc.M), "${title}", True],
                           [(6,2.5+(misc.SCHEM_FONT_SPACING-misc.SCHEM_FONT_SIZE)/misc.M), "${sub_title}", True]]
    
    def render_element(self, context):
        """Render element to context"""
        self.render_text(context, self.text_model)
        (tx1, ty1, tw1, th1) = self.text_extends[2]
        (tx2, ty2, tw2, th2) = self.text_extends[3]
        width = max(tw1, tw2)
        self.schem_model = [ 
                             ['CIRCLE', (2.5,2.5), 2.5, False, []],
                             ['LINE',(0,2.5),(6 + width/misc.M,2.5), []],
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

