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


class Wire(ElementModel):
    """Class for rendering wire elements"""
    def __init__(self, points=None):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_wire'
        self.name = 'Wire'
        self.icon = misc.abs_path('icons', 'wire.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = []
        self.fields = dict()
        self.text_model = []
        self.schem_model = []
        # Data
        self.points = None
        # Initialise
        if points:
            self.update_points(points, init=True)
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        
        # Render
        self.render_model(context, self.schem_model)
        self.render_text(context, self.text_model)
        # Post processing
        self.modify_extends()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        ports = tuple(tuple(x) for x in self.get_ports_global())
        p0 = code + ':0'
        nodes = ((p0, ports),)
        return nodes
        
    def get_power_model(self, code):
        """Return pandapower model for analysis"""
        power_model = tuple()
        return power_model
        
    def update_points(self, points=None, init=False):
        """Update given points to wire element"""
        
        def local(port):  # convert to local coordinates
            x = (port[0] - self.x)/misc.M
            y = (port[1] - self.y)/misc.M
            return (x,y)
                
        if points:
            self.points = points
            
        if len(self.points) > 1:
            # Set dimenstions
            (x, y, self.model_width, self.model_height) = misc.rect_from_points(*self.points)
            if init:
                self.x = x
                self.y = y
            # Set ports
            self.ports = []
            self.ports.append(local(self.points[0]))
            self.ports.append(local(self.points[-1]))
        
            # Set models
            self.fields = dict()
            self.text_model = []
            self.schem_model = []
            prev_point = local(self.points[0])
            for i, point in enumerate(self.points[1:]):
                point_local = local(point)
                self.fields['text'+str(i+1)] = self.get_field_dict('str', 'Text '+str(i+1), '', '')
                midx = (point_local[0] + prev_point[0])/2 + 0.1
                midy = (point_local[1] + prev_point[1])/2 + 0.1
                self.text_model.append([(midx,midy), "${text" + str(i+1) + "}", True])
                self.schem_model.append(['LINE', prev_point, point_local, []])
                prev_point = point_local
    
    def move(self, dx, dy):
        """Move element coordinates"""
        self.x = self.x + dx
        self.y = self.y + dy
        for slno, point in enumerate(self.points):
            self.points[slno] = (point[0] + dx, point[1] + dy)
        self.update_points()
    
    def get_model(self):
        """Get storage model"""
        # Get reference for child
        return {'code': self.code,
                'x': self.x,
                'y': self.y,
                'orientation': self.orientation,
                'ports': copy.deepcopy(self.ports),
                'fields': misc.get_fields_trunc(self.fields),
                'points': copy.deepcopy(self.points)}
    
    def set_model(self, model, gid=None):
        """Set storage model"""
        if model['code'] == self.code:
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            self.fields = misc.update_fields(self.fields, model['fields'])
            self.gid = gid
            points = copy.deepcopy(model['points'])
            if points:
                self.update_points(points)

