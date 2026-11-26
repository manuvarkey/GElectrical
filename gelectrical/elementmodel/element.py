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

# local files import
from ..core import constants, style
from ..core.fields import get_field_dict, get_fields_trunc
from ..core.geometry import rect_overlaps, rect_contains_point
from .tooltips import tooltips

# Get logger object
log = logging.getLogger(__name__) 


class ElementModel:
    """Base class for all drawing elements"""
    tooltip = ''
    element_tooltips = tooltips
    timestamp = 0
    # True when model_width/model_height are set by the element itself
    fixed_extents = False
    
    def __init__(self, cordinates=(0,0), **kwargs):
        # Data
        self.x = int(cordinates[0])
        self.y = int(cordinates[1])
        self.database_path = None
        self.orientation = 'vertical'
        self.ports = []
        self.fields = dict()
        self.kwargs = kwargs
        
        # State data
        self.res_fields = dict()
        self.gid = None
        self.gid_assembly = None
        
        # Model parameters
        self.text_model = None
        self.schem_model = None
        self.model_width = 0
        self.model_height = 0
        # State variables
        self.selected = False
        self.model_loading = False  # Flag set during model loading stage
        self.selected_color = style.COLOR_SELECTED
        self.draw_schem_color = style.COLOR_NORMAL
        self.text_extends = []
        self.schem_extends = []
        self.extents_stale = True  # Extents not computed since last change
    
    def set_text_field_value(self, code, value):
        if code in self.fields:
            self.fields[code]['value'] = value
            self.extents_stale = True
            
    def get_text_field(self, code):
        if code in self.fields:
            return self.fields[code]
        
    def get_res_field(self, code):
        if code in self.res_fields:
            return self.res_fields[code]

    def draw(self, context, select=False, override_color=None):
        """Draw the schematic model (rendering lives in gelectrical.symbols)"""
        from ..symbols.render import draw_element
        draw_element(context, self, select, override_color)
    
    def check_overlap(self, rect):
        """Check whether the passed rectangle (x, y, w, h) is within element limits"""
        return rect_overlaps(self.get_dimensions(), rect)
        
    def check_overlap_ports(self, rect):
        """Check whether the passed rectangle (x, y, w, h) contains a port"""
        ports = self.get_ports_global()
        for port in ports:
            x = int(port[0])
            y = int(port[1])
            if rect_contains_point(rect, x, y):
                return (x,y)
        return False
            
    def get_dimensions(self):
        """Get dimensions (computes the symbol extents if not current)"""
        if self.extents_stale:
            self.layout()
        if self.orientation == 'vertical':
            rect = (int(self.x), 
                    int(self.y), 
                    int(self.model_width), 
                    int(self.model_height))
        elif self.orientation == 'horizontal': 
            rect = (int(self.x), 
                    int(self.y-self.model_width), 
                    int(self.model_height), 
                    int(self.model_width))
        return rect
    
    def set_coordinates(self, x, y):
        """Set element coordinates"""
        dx = x - self.x
        dy = y - self.y
        self.move(dx, dy)
    
    def move(self, dx, dy):
        """Move element coordinates"""
        self.x += dx
        self.y += dy
    
    def get_ports(self):
        if self.orientation == 'vertical':
            ports_v = []
            for port in self.ports:
                ports_v.append([int(port[0]*constants.M), int(port[1]*constants.M)])
            return ports_v
        elif self.orientation == 'horizontal':
            ports_h = []
            for port in self.ports:
                ports_h.append([int(port[1]*constants.M), -int(port[0]*constants.M)])
            return ports_h
        
    def get_ports_global(self):
        if self.orientation == 'vertical':
            ports_v = []
            for port in self.ports:
                ports_v.append([int(self.x + port[0]*constants.M), int(self.y + port[1]*constants.M)])
            return ports_v
        elif self.orientation == 'horizontal':
            ports_h = []
            for port in self.ports:
                ports_h.append([int(self.x + port[1]*constants.M), int(self.y - port[0]*constants.M)])
            return ports_h
        
    def get_model(self):
        """Get storage model"""
        # Get reference for child
        return {'code': self.code,
                'x': self.x,
                'y': self.y,
                'orientation': self.orientation,
                'ports': copy.deepcopy(self.ports),
                'fields': get_fields_trunc(self.fields)}
    
    def get_power_model(self, code, mode=constants.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        power_model = tuple()
        return power_model

    def set_model_cleanup(self):
        # Function called after model loading
        pass

    def set_model(self, model, gid=None):
        """Set storage model"""
        if model['code'] == self.code:
            self.model_loading = True
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            for code in self.fields:
                if code in model['fields']:
                    self.set_text_field_value(code, model['fields'][code]['value'])
            self.gid = gid
            self.model_loading = False
            self.set_model_cleanup()
            self.extents_stale = True
            
    def set_gid(self, gid):
        self.gid = gid
    
    def get_gid(self):
        return self.gid
    
    def set_gid_assembly(self, gid):
        self.gid_assembly = gid
    
    def get_gid_assembly(self):
        return self.gid_assembly
            
    def get_selection(self):
        """Get selection"""
        return self.selected
    
    def set_selection(self, select=True, color=style.COLOR_SELECTED):
        """Set selection"""
        self.selected = select
        self.selected_timestamp = ElementModel.timestamp
        ElementModel.timestamp += 1
        self.selected_color = color
        
    def set_draw_color(self, color=style.COLOR_SELECTED):
        """Set draw color"""
        self.draw_schem_color = color
        
    def reset_draw_color(self):
        self.draw_schem_color = style.COLOR_NORMAL
        
    ## Private Functions
    
    def get_field_dict(self, *args, **kwargs):
        # Update any defaults
        if 'status_inactivate' not in kwargs:
            kwargs['status_inactivate'] = False
        # Get field dict
        field_dict = get_field_dict(*args, **kwargs)
        return field_dict
    
    def get_field_value_dict(self):
        values = dict()
        for code in self.fields:
            values[code] = self.fields[code]['value']
        return values
    
    ## Symbol interface (geometry and rendering in gelectrical.symbols)
    
    def update_symbol(self):
        """Update symbol data (schem_model, text_model, ports) from fields"""
        pass
    
    def symbol_active(self):
        """False when the symbol is drawn in the inactive colour"""
        return True
    
    def get_symbol_layers(self):
        """Ordered symbol layers [(kind, model, color), ...] where kind is
        'schem' or 'text' and color None means the element draw colour"""
        self.update_symbol()
        color = None if self.symbol_active() else style.COLOR_INACTIVE
        return [('schem', self.schem_model, color), ('text', self.text_model, color)]
    
    def get_text_extents(self, text_model):
        """Extents (x, y, w, h) of the labels of ``text_model``"""
        from ..symbols.geometry import text_extents
        return text_extents(self, text_model)
    
    def layout(self):
        """Compute schem_extends, text_extends and the model size"""
        from ..symbols.geometry import layout_element
        layout_element(self)
    
    def modify_extends(self):
        """Recompute the model size (kept for compatibility)"""
        self.layout()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        #
        # Nodes tuple definition reference
        #
        # nodes = (('code:p', ((x0, y0), (<page>, x1, y1), ... ),  ; <> value for cross referencing
        #                ...                                       ; List out ports forming same node in graph
        #         )                                                ; code makes ports unique accross project
        #
        nodes = tuple()
        return nodes
        
    def get_sysdesign_model(self, code):
        """Return system design model for analysis"""
        #
        # System design model tuple definition reference
        #
        # sysdesign_model = (('code:p0', 'code:p1', sysdesign_model),
        #                           ...  )
        #
        # sysdesign_model = (('model_code', ('code:p0', 'code:p1' ... ), model_dict),  ; dict of parameter arguments for system design element creation
        #                ... )
        #
        sysdesign_model = tuple()
        return sysdesign_model
        
    def get_power_model(self, code, mode=constants.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        #
        # Powermodel tuple definition reference
        #
        # power_model = [('code:p0', 'code:p1', sysdesign_model),
        #             ...
        #         ]
        #
        # power_model = (('model_code', ('code:p0', 'code:p1' ... ), model_dict),  ; dict of parameter arguments for pandapower element creation
        #                ... )
        #
        power_model = tuple()
        return power_model
    
    def assign_tootltips(self):
        if self.code in self.element_tooltips:
            code_tooltips = self.element_tooltips[self.code]
            for code, field in self.fields.items():
                if code in code_tooltips:
                    field['tooltip'] = code_tooltips[code]


class ElementGroup:
    """Group of drawing elements"""
    
    def __init__(self, cordinates=(0,0)):
        # Data
        self.x = int(cordinates[0])
        self.y = int(cordinates[1])
        self.elements = []
        self.assembly_dict = dict()
        self.attachment_point_element = None
        self.attachment_point_port = None
        
    def add_elements(self, elements, assembly_dict=None):
        if elements:
            self.elements = elements
            self.assembly_dict = assembly_dict
            self.attachment_point_element = 0
            self.attachment_point_port = 0
            attachment_port_global = self.elements[0].get_ports_global()[0]
            dx = -attachment_port_global[0]
            dy = -attachment_port_global[1]
            for element in self.elements:
                element.move(dx, dy)
            self.set_coordinates(self.x, self.y)
        
    def rotate_model(self):
        if len(self.elements) == 1:
            self.elements[0].orientation = 'vertical' if self.elements[0].orientation == 'horizontal' else 'horizontal'
            attachment_port_global = self.elements[0].get_ports_global()[0]
            dx = self.x-attachment_port_global[0]
            dy = self.y-attachment_port_global[1]
            self.elements[0].move(dx, dy)
            return True
        else:
            return False
                
    def modify_attachment_port(self):
        # Rotate attachment point
        if self.attachment_point_element is not None:
            element_ports = self.elements[self.attachment_point_element].get_ports()
            self.attachment_point_port += 1
            if self.attachment_point_port > len(element_ports) - 1:
                self.attachment_point_element += 1
                self.attachment_point_port = 0
                if self.attachment_point_element > len(self.elements) - 1:
                    self.attachment_point_element = 0
            attachment_port_global = self.elements[self.attachment_point_element].get_ports_global()[self.attachment_point_port]
            dx = self.x-attachment_port_global[0]
            dy = self.y-attachment_port_global[1]
            for element in self.elements:
                element.move(dx, dy)
                    
    def set_coordinates(self, x, y):
        dx = x - self.x
        dy = y - self.y
        self.x = x
        self.y = y
        if self.attachment_point_element is not None:
            for element in self.elements:
                element.move(dx, dy)
