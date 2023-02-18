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

# Get logger object
log = logging.getLogger(__name__) 


class ElementModel:
    """Base class for all drawing elements"""
    
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
        self.selected_color = misc.COLOR_SELECTED
        self.draw_schem_color = misc.COLOR_NORMAL
        self.text_extends = []
        self.schem_extends = []
    
    def set_text_field_value(self, code, value):
        if code in self.fields:
            self.fields[code]['value'] = value
            
    def get_text_field(self, code):
        if code in self.fields:
            return self.fields[code]
        
    def get_res_field(self, code):
        if code in self.res_fields:
            return self.res_fields[code]

    def draw(self, context, select=False, override_color=None):
        """Draw the schematic model"""
        default_color = self.draw_schem_color
        if override_color:
            self.draw_schem_color = override_color
        self.render_element(context)
        self.draw_schem_color = default_color
        if select == True and self.selected == True:
            (x, y, width, height) = self.get_dimensions()
            misc.draw_rectangle(context,
                                self.x,
                                self.y,
                                width,
                                height,
                                radius=misc.RECTANGLE_RADIUS,
                                color=self.selected_color,
                                stroke_width=misc.STROKE_WIDTH_SELECTED,
                                line_style='dashed',
                                dash_pattern=[20,5])
    
    def check_overlap(self, rect):
        """Check whether the passed rectangle is within element limits"""
        element_region = cairo.Region(cairo.RectangleInt(*self.get_dimensions()))
        if element_region.contains_rectangle(rect) in (cairo.RegionOverlap.IN, cairo.RegionOverlap.PART):
            return True
        else:
            return False
        
    def check_overlap_ports(self, rect):
        """Check whether the passed rectangle is contains points"""
        ports = self.get_ports_global()
        source_region = cairo.Region(rect)
        for port in ports:
            x = int(port[0])
            y = int(port[1])
            if source_region.contains_point(x,y):
                return (x,y)
        return False
            
    def get_dimensions(self):
        """Get dimensions"""
        if self.orientation == 'vertical':
            rect = (int(self.x), 
                    int(self.y), 
                    int(self.model_width), 
                    int(self.model_height))
        elif self.orientation == 'horizontal': 
            rect = (int(self.x), 
                    int(self.y), 
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
                ports_v.append([int(port[0]*misc.M), int(port[1]*misc.M)])
            return ports_v
        elif self.orientation == 'horizontal':
            ports_h = []
            for port in self.ports:
                ports_h.append([int(port[1]*misc.M), int(self.model_width-port[0]*misc.M)])
            return ports_h
        
    def get_ports_global(self):
        if self.orientation == 'vertical':
            ports_v = []
            for port in self.ports:
                ports_v.append([int(self.x + port[0]*misc.M), int(self.y + port[1]*misc.M)])
            return ports_v
        elif self.orientation == 'horizontal':
            ports_h = []
            for port in self.ports:
                ports_h.append([int(self.x + port[1]*misc.M), int(self.y + self.model_width-port[0]*misc.M)])
            return ports_h
        
    def get_model(self):
        """Get storage model"""
        # Get reference for child
        return {'code': self.code,
                'x': self.x,
                'y': self.y,
                'orientation': self.orientation,
                'ports': copy.deepcopy(self.ports),
                'fields': misc.get_fields_trunc(self.fields)}
    
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
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
    
    def set_selection(self, select=True, color=misc.COLOR_SELECTED):
        """Set selection"""
        self.selected = select
        self.selected_color = color
        
    def set_draw_color(self, color=misc.COLOR_SELECTED):
        """Set draw color"""
        self.draw_schem_color = color
        
    def reset_draw_color(self):
        self.draw_schem_color = misc.COLOR_NORMAL
        
    ## Private Functions
    
    def get_field_dict(self, *args, **kwargs):
        # Update any defaults
        if 'status_inactivate' not in kwargs:
            kwargs['status_inactivate'] = False
        # Get field dict
        field_dict = misc.get_field_dict(*args, **kwargs)
        return field_dict
    
    def get_field_value_dict(self):
        values = dict()
        for code in self.fields:
            values[code] = self.fields[code]['value']
        return values
    
    def modify_extends(self):
        element_region = cairo.Region(cairo.RectangleInt(*self.get_dimensions()))
        rects = []
        # Calculate extends
        # Additional pixel added for rounding error and for preventing zero dimensions
        for port in self.ports:
            rects.append(cairo.RectangleInt(*misc.rect_from_points((0,0), (misc.M*port[0], misc.M*port[1]))))
        for x,y,w,h in self.schem_extends:
            rects.append(cairo.RectangleInt(int(x), int(y), int(w)+1, int(h)+1))
        for x,y,w,h in self.text_extends:
            rects.append(cairo.RectangleInt(int(x), int(y), int(w)+1, int(h)+1))
        # Modify extends
        element_region = cairo.Region(rects)
        master_rect = element_region.get_extents()
        self.model_width = master_rect.width
        self.model_height = master_rect.height
    
    def render_model(self, context, schem_model, color=None):
        #
        # Schem model reference
        #
        # Use lengths and coordinates as multiples of misc.M, angles in degrees
        #
        # [['LINE',(x0,y0),(x1,y1), (d1,d2,...), <'normal'/'thick'/'thin'>],
        #  ['CURVE',(x0,y0),(x1,y2),(x3,y3),(x4,y4), (d1,d2,...), <'normal'/'thick'/'thin'>],
        #  ['ARC', (x0,y0), r, t0, t1, (d1,d2,...), <'normal'/'thick'/'thin'>],
        #  ['CIRCLE', (x0,y0), r, True/False, (d1,d2,...), <'normal'/'thick'/'thin'>],
        #  ['RECT', (x0,y0), w, h, True/False, (d1,d2,...), <'normal'/'thick'/'thin'>],
        #  ['PATH', (x0,y0), True/False, (d1,d2,...), 'normal'/'thick'/'thin', [['LINE', (dx1,dy1)],
        #                                                                       ['CURVE', (dx0,dy0),(dx1,dy1),(dx2,dy2)],
        #                                                                       ['ARC', (x0,y0), r, t0, t1]
        #  ]
        #       ...
        # ]
        #
        
        # Setup
        if not color:
            color = self.draw_schem_color
        context.save()
        (r,g,b,a) = misc.hex2rgb(color)
        context.set_source_rgba(r, g, b, a)
        context.set_line_width(misc.STROKE_WIDTH_NORMAL)
        context.set_line_cap(cairo.LINE_CAP_ROUND)
        context.translate(self.x, self.y)
        if self.orientation == 'vertical':
            pass
        elif self.orientation == 'horizontal':
            matrix = cairo.Matrix(0, -1, 1, 0, 0, self.model_width)
            context.transform (matrix)
        self.schem_extends = []
        M = lambda x: [i*misc.M for i in x]
        # Render
        for item in schem_model:
            if item[0] == 'LINE':
                if len(item) == 4 or item[4] == 'normal':
                    context.set_line_width(misc.STROKE_WIDTH_NORMAL)
                elif item[4] == 'thin':
                    context.set_line_width(misc.STROKE_WIDTH_THIN)
                elif item[4] == 'thick':
                    context.set_line_width(misc.STROKE_WIDTH_THICK)
                elif item[4] == 'thicker':
                    context.set_line_width(misc.STROKE_WIDTH_EXTRATHICK)
                context.set_dash(item[3])
                context.move_to(*M(item[1]))
                context.line_to(*M(item[2]))
                context.stroke()
                self.schem_extends.append(misc.rect_from_points(M(item[1]), M(item[2])))
            elif item[0] == 'CURVE':
                if len(item) == 6 or item[6] == 'normal':
                    context.set_line_width(misc.STROKE_WIDTH_NORMAL)
                elif item[6] == 'thin':
                    context.set_line_width(misc.STROKE_WIDTH_THIN)
                elif item[6] == 'thick':
                    context.set_line_width(misc.STROKE_WIDTH_THICK)
                elif item[6] == 'thicker':
                    context.set_line_width(misc.STROKE_WIDTH_EXTRATHICK)
                context.set_dash(item[5])
                context.move_to(*M(item[1]))
                context.curve_to(*M(item[2]), *M(item[3]), *M(item[4]))
                context.stroke()
                self.schem_extends.append(misc.rect_from_points(M(item[1]), M(item[2]), M(item[3]), M(item[4])))
            elif item[0] == 'ARC':
                if len(item) == 6 or item[6] == 'normal':
                    context.set_line_width(misc.STROKE_WIDTH_NORMAL)
                elif item[6] == 'thin':
                    context.set_line_width(misc.STROKE_WIDTH_THIN)
                elif item[6] == 'thick':
                    context.set_line_width(misc.STROKE_WIDTH_THICK)
                elif item[6] == 'thicker':
                    context.set_line_width(misc.STROKE_WIDTH_EXTRATHICK)
                context.set_dash(item[5])
                context.arc(*M(item[1]), misc.M*item[2], item[3]*misc.PI/180, item[4]*misc.PI/180)
                context.stroke()
                self.schem_extends.append(misc.rect_from_points( \
                                           (M(item[1])[0]+misc.M*item[2]*cos(item[3]*misc.PI/180), 
                                            M(item[1])[1]+misc.M*item[2]*sin(item[3]*misc.PI/180)),
                                           (M(item[1])[0]+misc.M*item[2]*cos(item[4]*misc.PI/180), 
                                            M(item[1])[1]+misc.M*item[2]*sin(item[4]*misc.PI/180)),
                                            ))
            elif item[0] == 'CIRCLE':
                if len(item) == 5 or item[5] == 'normal':
                    context.set_line_width(misc.STROKE_WIDTH_NORMAL)
                elif item[5] == 'thin':
                    context.set_line_width(misc.STROKE_WIDTH_THIN)
                elif item[5] == 'thick':
                    context.set_line_width(misc.STROKE_WIDTH_THICK)
                elif item[5] == 'thicker':
                    context.set_line_width(misc.STROKE_WIDTH_EXTRATHICK)
                context.set_dash(item[4])
                context.arc(*M(item[1]), misc.M*item[2], 0, 2*misc.PI)
                context.close_path()
                if item[3]:
                    context.fill()
                else:
                    context.stroke()
                self.schem_extends.append((M(item[1])[0]-misc.M*item[2], 
                                           M(item[1])[1]-misc.M*item[2],
                                           2*misc.M*item[2], 
                                           2*misc.M*item[2]))
            elif item[0] == 'RECT':
                if len(item) == 6 or item[6] == 'normal':
                    context.set_line_width(misc.STROKE_WIDTH_NORMAL)
                elif item[6] == 'thin':
                    context.set_line_width(misc.STROKE_WIDTH_THIN)
                elif item[6] == 'thick':
                    context.set_line_width(misc.STROKE_WIDTH_THICK)
                elif item[6] == 'thicker':
                    context.set_line_width(misc.STROKE_WIDTH_EXTRATHICK)
                context.set_dash(item[5])
                context.rectangle(*M(item[1]), misc.M*item[2], misc.M*item[3])
                if item[4]:
                    context.fill()
                else:
                    context.stroke()
                self.schem_extends.append((*M(item[1]), misc.M*item[2], misc.M*item[3]))
            elif item[0] == 'PATH':
                if item[4] == 'normal':
                    context.set_line_width(misc.STROKE_WIDTH_NORMAL)
                elif item[4] == 'thin':
                    context.set_line_width(misc.STROKE_WIDTH_THIN)
                elif item[4] == 'thick':
                    context.set_line_width(misc.STROKE_WIDTH_THICK)
                elif item[4] == 'thicker':
                    context.set_line_width(misc.STROKE_WIDTH_EXTRATHICK)
                context.set_dash(item[3])
                context.move_to(*M(item[1]))
                for subitem in item[5]:
                    if subitem[0] == 'LINE':
                        context.rel_line_to(*M(subitem[1]))
                        self.schem_extends.append(misc.rect_from_points(M(item[1]), M(subitem[1])))
                    elif subitem[0] == 'CURVE':
                        context.rel_curve_to(*M(subitem[1]), *M(subitem[2]), *M(subitem[3]))
                        self.schem_extends.append(misc.rect_from_points(M(item[1]), M(subitem[1]), M(subitem[2]), M(subitem[3])))
                    elif subitem[0] == 'ARC':
                        context.arc(*M(subitem[1]), misc.M*subitem[2], subitem[3]*misc.PI/180, subitem[4]*misc.PI/180)
                        self.schem_extends.append(misc.rect_from_points( \
                                           (M(subitem[1])[0]+misc.M*subitem[2]*cos(subitem[3]*misc.PI/180), 
                                            M(subitem[1])[1]+misc.M*subitem[2]*sin(subitem[3]*misc.PI/180)),
                                           (M(subitem[1])[0]+misc.M*subitem[2]*cos(subitem[4]*misc.PI/180), 
                                            M(subitem[1])[1]+misc.M*subitem[2]*sin(subitem[4]*misc.PI/180)),
                                            ))
                if item[2]:
                    context.close_path()
                    context.fill()
                else:
                    context.stroke()
        # Cleanup
        context.restore()
    
    def render_text(self, context, text_model, color=None):
        #
        # Text field definition reference
        #
        # { 'field': dict(),
        #    ...
        # }
        #
        # dict = {'type': 'str/float/int/str_list/float_list/int_list',
        #         'caption': 'caption',
        #         'unit': 'unit',
        #         'value': 'value',
        #         'max_chars: x',
        #         'validation_func: func',
        #         'selection_list: [x0, x1, x2, ...]',
        #         'allow_custom_value: True/False'
        #        }
        # OR
        # Use convinence function self.field_definition_dict(type, caption, unit, value, ...)
        #
        
        #
        # Text model reference
        #
        # Use coordinates as multiples of misc.M, angles in degrees
        # Use None for y value for auto-increment
        # Use Mako template for Expr
        #
        # [[(x,y), Expr, display True/False],
        #    ...
        # ]
        #
        
        # Setup
        if not color:
            color = self.draw_schem_color
        context.save()
        context.translate(self.x, self.y)
        if self.orientation == 'vertical':
            pass
        elif self.orientation == 'horizontal':
            matrix = cairo.Matrix(0, -1, 1, 0, 0, self.model_width)
            context.transform (matrix)
        self.text_extends = []
        # Render
        model_width_start = self.model_width
        y_calc = 0
        for model in text_model:
            size = misc.SCHEM_FONT_SIZE
            weight = misc.SCHEM_FONT_WEIGHT
            alignment = 'left'
            if len(model) == 3:
                ((x,y), expr, display_value) = model
            elif len(model) == 4:
                ((x,y), expr, display_value, size) = model
            elif len(model) == 5:
                ((x,y), expr, display_value, size, weight) = model
            else:
                ((x,y), expr, display_value, size, weight, alignment) = model
            if display_value:
                y_calc = misc.M*y if y is not None else y_calc + misc.SCHEM_FONT_SPACING  # calculate y_calc (set or auto increment)
                template = ExprTemplate(expr)
                text = template.render(**self.get_field_value_dict())
                (x,y,w,h) = misc.draw_text(context, text, misc.M*x, y_calc, color=color, 
                                           fontname=misc.SCHEM_FONT_FACE, 
                                           fontsize=size, fontweight=weight,
                                           alignment=alignment)
                self.text_extends.append((x, y, w, h))
        # Cleanup
        context.restore()
        
    ## Mandatory functions
    
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
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
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
