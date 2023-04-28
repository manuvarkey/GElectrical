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
        self.text_model = [[(1,1-misc.SCHEM_FONT_SPACING/misc.M/2), "${ref}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],]
        self.schem_model = [['RECT', (0,0), 2,2, True, []],]
    
    def render_element(self, context):
        """Render element to context"""
        self.render_model(context, self.schem_model, color=misc.COLOR_OVERLAY_BG)
        self.render_text(context, self.text_model, color=misc.COLOR_OVERLAY_TEXT)
        # Post processing
        self.modify_extends()


class DisplayElementText(ElementModel):
    """Class for rendering cross reference elements"""
    
    code = 'element_display_text'
    name = 'Text Display Element'
    group = 'Miscellaneous'
    icon = misc.abs_path('icons', 'display-text.svg')
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
        self.text_model = [[(0.5,0.5), "${text}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'left'],]
        self.schem_model = []
    
    def render_element(self, context):
        """Render element to context"""
        self.render_model(context, self.schem_model)
        self.render_text(context, self.text_model)
        if self.fields['border']['value'] or self.fields['background']['value']:
            self.modify_extends()
            width = self.model_width + 1*misc.M
            height = self.model_height + 1*misc.M
            if self.fields['background']['value']:
                schem_model_border = [['RECT', (0,0), width/misc.M, height/misc.M, True, []]]
                self.render_model(context, schem_model_border, color=misc.COLOR_OVERLAY_BG)
            if self.fields['border']['value']:
                schem_model_border = [['RECT', (0,0), width/misc.M, height/misc.M, False, [], 'thin']]
                self.render_model(context, schem_model_border)
            
        # Post processing
        self.modify_extends()


        
