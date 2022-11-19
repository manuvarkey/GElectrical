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


class DisplayElementNode(ElementModel):
    """Class for rendering cross reference elements"""
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_display_node'
        self.name = 'Node Display Element'
        self.group = ''
        self.icon = ''
        self.model_width = 0
        self.model_height = 0
        self.ports = [(1,1)]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference Code', '', '45')}
        self.text_model = [[(1,1-misc.SCHEM_FONT_SPACING/misc.M/2), "${ref}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],]
        self.schem_model = [['RECT', (0,0), 2,2, True, []],]
    
    def render_element(self, context):
        """Render element to context"""
        self.draw_schem_color = misc.COLOR_OVERLAY
        self.render_model(context, self.schem_model)
        self.draw_schem_color = misc.COLOR_NORMAL
        self.render_text(context, self.text_model)
        # Post processing
        self.modify_extends()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        nodes = tuple()
        return nodes
        
    def get_power_model(self, code):
        """Return pandapower model for analysis"""
        power_model = tuple()
        return power_model
        
