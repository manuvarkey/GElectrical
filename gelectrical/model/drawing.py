#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# drawing
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
from .. import misc, undo
from ..undo import undoable

# Get logger object
log = logging.getLogger(__name__)


class DrawingModel:
    """Class for modelling a drawing"""
    
    def __init__(self, parent, program_state, program_settings):
        # Data
        self.fields = {'name':          misc.get_field_dict('str', 'Sheet Name', '', 'Sheet', status_inactivate=False),
                       'page_size':     misc.get_field_dict('str', 'Page Size', '', 'A3', status_inactivate=False, selection_list=list(misc.paper_sizes.keys())),
                       'page_width':    misc.get_field_dict('float', 'Page Width', 'points', 1000, status_inactivate=True, decimal=0),
                       'page_height':   misc.get_field_dict('float', 'Page Height', 'points', 1000, status_inactivate=True, decimal=0),
                       'title':         misc.get_field_dict('str', 'Title', '', 'TITLE', status_inactivate=False),
                       'drawing_no':    misc.get_field_dict('str', 'Drawing Number', '', 'PROJECT/ELEC/SLD/1', status_inactivate=False),
                       'sheet_no':      misc.get_field_dict('str', 'Sheet No.', '', '1/1', status_inactivate=False),
                       'type':          misc.get_field_dict('str', 'Document Type', '', 'Electrical Schematic', status_inactivate=False),
                       'status':        misc.get_field_dict('str', 'Document Status.', '', 'DRAFT', status_inactivate=False),
                       'rev':           misc.get_field_dict('str', 'Revision', '', 'A', status_inactivate=False),
                       'date_of_issue': misc.get_field_dict('str', 'Date of Issue', '', '2000-00-00', status_inactivate=False),}
        (width, height) = misc.paper_sizes[self.fields['page_size']['value']]
        self.fields['page_width']['value'] = width/misc.POINT_TO_MM
        self.fields['page_height']['value'] = height/misc.POINT_TO_MM
        self.template = Template(width, height)
        self.title_block = TitleBlock()
        self.elements = []
        
        # State variables
        self.parent = parent
        self.program_state = program_state
        self.program_settings = program_settings
        self.grid_width = misc.GRID_WIDTH
        self.element_models = self.program_state['element_models']
        self.floating_model = None
        self.wire_points = []
        self.selected_ports = []
        self.selected_port_color = misc.COLOR_SELECTED
        
        # Initialisation
        self.update_title_block()
        
    ## Export/Import functions
    
    def export_drawing(self, context):
        self.draw_model(context, select=False)
    
    def get_model(self):
        """Get storage model"""
        element_models = []
        for element in self.elements:
            element_models.append(element.get_model())
        model = dict()
        model['fields'] = self.fields
        model['elements'] = element_models
        return ['DrawingModel', model]
            
    def set_model(self, model):
        """Set storage model"""
        self.elements = []
        if model[0] == 'DrawingModel':
            for base_model in model[1]['elements']:
                code = base_model['code']
                if code == 'element_assembly':
                    element = ElementAssembly()
                elif code == 'element_wire':
                    element = Wire()
                else:
                    element = self.program_state['element_models'][code]()
                element.set_model(base_model)
                self.elements.append(element)
            self.fields = model[1]['fields']
            if self.fields['page_size']['value'] != 'Custom':
                (width, height) = misc.paper_sizes[self.fields['page_size']['value']]
                self.fields['page_width']['value'] = width/misc.POINT_TO_MM
                self.fields['page_height']['value'] = height/misc.POINT_TO_MM
                self.template = Template(width, height)
            else:
                self.template = Template(self.fields['page_width']['value'], self.fields['page_height']['value'])
            self.update_title_block()
            self.grid_width = misc.GRID_WIDTH
            self.floating_model = None
            self.wire_points = []
            self.selected_ports = []
            self.selected_port_color = misc.COLOR_SELECTED
        
    ## Query Functions
    
    def get_page_field(self, code):
        if code in self.fields:
            return self.fields[code]
    
    def get_selected(self):
        selected = []
        for element in self.elements:
            if element.get_selection() is True:
                selected.append(element)
        return selected
    
    def get_selected_codes(self):
        selected = []
        for slno, element in enumerate(self.elements):
            if element.get_selection() is True:
                selected.append(slno)
        return selected
    
    def get_grid_point(self, x, y):
        x = round(x/self.grid_width, 0)*self.grid_width
        y = round(y/self.grid_width, 0)*self.grid_width
        return x,y
    
    def get_port_around_coordinate(self, x, y, w=misc.SELECT_PORT_RECT, h=misc.SELECT_PORT_RECT):
        """Draw the selected schematic model"""
        w = int(w)
        h = int(h)
        x = int(x-w/2)
        y = int(y-h/2)
        for element in self.elements:
            # Form selection rectangle
            rect = cairo.RectangleInt(x, y, w, h)
            # Check for overlap
            port = element.check_overlap_ports(rect)
            if port:
                return port
        
    ## Modify Functions
    
    @undoable
    def update_page_field(self, field_code, value):
        value_old = self.fields[field_code]['value']
        self.fields[field_code]['value'] = value
        
        (width, height) = misc.paper_sizes[self.fields['page_size']['value']]
        self.fields['page_width']['value'] = width/misc.POINT_TO_MM
        self.fields['page_height']['value'] = height/misc.POINT_TO_MM
        
        self.template.set_dimensions(width, height)
        self.update_title_block()
        self.parent.update_tabs()  # Update tabs
        
        yield "Update page field"
        # Undo action
        self.update_page_field(field_code, value_old)
    
    @undoable            
    def update_element_at_index(self, element, index):
        old_element = self.elements[index]
        self.elements[index] = element
            
        yield "Update draw element at '{}'".format(index)
        # Undo action
        self.update_element_at_index(old_element, index)
            
    @undoable            
    def insert_element_at_index(self, element, index=None):
        if index:
            self.elements.insert(index, element)
            insert_index = index
        else:
            self.elements.append(element)
            insert_index = len(self.elements) - 1
            
        yield "Add draw element at '{}'".format(insert_index)
        # Undo action
        self.delete_rows([insert_index])
                
    @undoable
    def delete_rows(self, rows):
        old_rows = []
        rows.sort(reverse=True)
        for index in rows:
            old_element = self.elements.pop(index)
            old_rows.append((index, old_element))
            
        yield "Delete draw elements at '{}'".format(rows)
        # Undo action
        for index, old_element in old_rows:
            self.insert_element_at_index(old_element, index)
                
    def add_element(self, x, y, code, grid_constraint=False, select=False):
        if code is not None:
            if grid_constraint:  # Modify x,y to correspond to grid
                x,y = self.get_grid_point(x,y)
            model = self.element_models[code]
            element = model((x, y))
            if select:
                element.set_selection(True)
            self.insert_element_at_index(element)
            
    def deselect_all(self):
        for element in self.elements:
            element.set_selection(False)
        self.selected_ports = []
        self.selected_port_color = misc.COLOR_SELECTED
            
    def select_all(self):
        for element in self.elements:
            element.set_selection(True)
            
    def select_ports(self, nodes, color=misc.COLOR_SELECTED):
        """Add selection nodes"""
        self.selected_ports = nodes
        self.selected_port_color = color
            
    def update_select(self, x, y, w=0, h=0, retain_selection=True):
        selected = False
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        for element in self.elements:
            # Form selection rectangle
            rect = cairo.RectangleInt(x, y, w, h)
            # Check for selection
            if element.check_overlap(rect):
                if element.get_selection() == True:
                    element.set_selection(False)
                    selected = True
                else:
                    element.set_selection(True)
                    selected = True
            elif retain_selection is False:
                element.set_selection(False)
        return selected
    
    def update_title_block(self):
        title_fields = dict()
        title_fields['page_width'] = self.fields['page_width']
        title_fields['page_height'] = self.fields['page_height']
        title_fields['title'] = self.fields['title']
        title_fields['drawing_no'] = self.fields['drawing_no']
        title_fields['type'] = self.fields['type']
        title_fields['status'] = self.fields['status']
        title_fields['sheet_no'] = self.fields['sheet_no']
        title_fields['rev'] = self.fields['rev']
        title_fields['date_of_issue'] = self.fields['date_of_issue']
        title_fields['project_name'] = self.parent.fields['project_name']
        title_fields['drawing_field_dept'] = self.parent.fields['drawing_field_dept']
        title_fields['drawing_field_techref'] = self.parent.fields['drawing_field_techref']
        title_fields['drawing_field_created'] = self.parent.fields['drawing_field_created']
        title_fields['drawing_field_approved'] = self.parent.fields['drawing_field_approved']
        title_fields['drawing_field_lang'] = self.parent.fields['drawing_field_lang']
        title_fields['drawing_field_address'] = self.parent.fields['drawing_field_address']
        self.title_block.set_fields(title_fields)
    
    def add_assembly_from_selection(self):
        selected = self.get_selected()
        if selected:
            # Update elements
            for element in selected:
                if isinstance(element, ElementAssembly) and len(selected) > 1:
                    index = self.elements.index(element)
                    selected.remove(element)
                    assembly = ElementAssembly(selected)
                    self.update_element_at_index(assembly, index)
                    return
            # For new items
            assembly = ElementAssembly(selected)
            self.insert_element_at_index(assembly)
        
    def delete_selected_rows(self):
        selected = self.get_selected_codes()
        self.delete_rows(selected)
            
    ## Floating model functions
    
    def set_floating_model_from_code(self, code):
        """Add a floating model"""
        if code is not None:
            model = self.element_models[code]
            element = model()
            self.floating_model = ElementGroup()
            self.floating_model.add_elements([element])
        return element
            
    def add_floating_model(self, elements):
        """Add a floating model"""
        self.floating_model = ElementGroup()
        self.floating_model.add_elements(elements)
        
    def rotate_floating_model(self):
        if self.floating_model:
            self.floating_model.rotate_model()
                
    def modify_fm_attachment_port(self):
        if self.floating_model:
            self.floating_model.modify_attachment_port()
        
    def reset_floating_model(self):
        """Reset floating model"""
        self.floating_model = None
        
    def make_floating_model_permenant(self, port=None):
        if self.floating_model:
            if port:
                x = port[0]
                y = port[1]
                self.floating_model.set_coordinates(x,y)
            for element in self.floating_model.elements:
                self.insert_element_at_index(copy.deepcopy(element))
            
    ## Wire functions
    
    def add_wire_point(self, x, y, grid_constraint=True):
        if grid_constraint:  # Modify x,y to correspond to grid
            x,y = self.get_grid_point(x,y)
        self.wire_points.append((x,y))
        
    def get_num_wire_points(self):
        return len(self.wire_points)
        
    def reset_wire_points(self):
        self.wire_points = []
        
    def make_wire_permenant(self, x, y, grid_constraint=True):
        self.add_wire_point(x, y, grid_constraint)
        if len(self.wire_points) > 1:
            self.insert_element_at_index(Wire(self.wire_points))
        self.reset_wire_points()
    
    ## Draw functions
    
    def draw_gridlines(self, context):
        """Draw grid lines"""
        page_width = self.fields['page_width']['value']
        page_height = self.fields['page_height']['value']
        grid_width = self.grid_width
        
        context.save()
        (r,g,b,a) = misc.hex2rgb(misc.COLOR_GRID)
        context.set_source_rgba(r, g, b, a)
        context.set_line_width(0.5)
        for x in range(0, int(page_width), int(grid_width)):
            for y in range(0, int(page_height), int(grid_width)):
                # Draw horizontal lines
                context.move_to(0, y)
                context.line_to(page_width, y)
            # Draw vertical ines
            context.move_to(x, 0)
            context.line_to(x, page_height)
        context.stroke()
        context.restore()
        
    def draw_model(self, context, select=False):
        """Draw the schematic model"""
        self.title_block.draw(context)
        self.template.draw(context)
        for element in self.elements:
            element.draw(context, select)
        self.draw_selected_ports(context)
            
    def draw_selected_ports(self, context):
        for port in self.selected_ports:
            misc.draw_rectangle(context,
                                port[0] - misc.SELECT_PORT_RECT/2, 
                                port[1] - misc.SELECT_PORT_RECT/2,
                                misc.SELECT_PORT_RECT,
                                misc.SELECT_PORT_RECT,
                                color=self.selected_port_color, 
                                stroke_width=misc.STROKE_WIDTH_SELECTED)
        
    def draw_floating_model(self, context, x, y, grid_constraint=True):
        """Draw the selected schematic model"""
        if self.floating_model is not None:
            if grid_constraint:  # Modify x,y to correspond to grid
                x,y = self.get_grid_point(x,y)
            # Modify coordinates for attachment point
            self.floating_model.set_coordinates(x,y)
            for element in self.floating_model.elements:
                element.draw(context)
            
    def draw_wire(self, context, x, y, grid_constraint=True, color=misc.COLOR_NORMAL):
        """Draw the saved wire"""
        if self.wire_points:
            # Draw wire
            if len(self.wire_points) > 1:
                element = Wire(self.wire_points)
                element.draw(context)
            # Draw leading line
            if grid_constraint:  # Modify x,y to correspond to grid
                x,y = self.get_grid_point(x,y)
            misc.draw_line(context, *self.wire_points[-1], x, y, 
                           color = color, 
                           dash_pattern = misc.WIRE_ADD_DRAW_PATTERN, 
                           stroke_width = misc.STROKE_WIDTH_NORMAL)

            
class ElementGroup:
    """Group of drawing elements"""
    
    def __init__(self, cordinates=(0,0)):
        # Data
        self.x = int(cordinates[0])
        self.y = int(cordinates[1])
        self.elements = []
        self.attachment_point_element = None
        self.attachment_point_port = None
        
    def add_elements(self, elements):
        if elements:
            self.elements = elements
            self.attachment_point_element = 0
            self.attachment_point_port = 0
            attachment_port_global = self.elements[0].get_ports_global()[0]
            dx = -attachment_port_global[0]
            dy = -attachment_port_global[1]
            for element in self.elements:
                element.x += dx
                element.y += dy
            self.set_coordinates(self.x, self.y)
        
    def rotate_model(self):
        if len(self.elements) == 1:
            self.elements[0].orientation = 'vertical' if self.elements[0].orientation == 'horizontal' else 'horizontal'
            attachment_port_global = self.elements[0].get_ports_global()[0]
            dx = self.x-attachment_port_global[0]
            dy = self.y-attachment_port_global[1]
            self.elements[0].x += dx
            self.elements[0].y += dy
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
                element.x += dx
                element.y += dy
                    
    def set_coordinates(self, x, y):
        dx = x - self.x
        dy = y - self.y
        self.x = x
        self.y = y
        if self.attachment_point_element is not None:
            for element in self.elements:
                element.x += dx
                element.y += dy


class ElementModel:
    """Base class for all drawing elements"""
    
    def __init__(self, cordinates=(0,0)):
        # Data
        self.x = int(cordinates[0])
        self.y = int(cordinates[1])
        self.code = ''
        self.database_path = None
        self.orientation = 'vertical'
        self.ports = []
        self.fields = dict()
        
        # State data
        self.res_fields = dict()
        
        # Model parameters
        self.name = ''
        self.icon = ''
        self.text_model = None
        self.schem_model = None
        self.model_width = 0
        self.model_height = 0
        # State variables
        self.selected = False
        self.selected_color = misc.COLOR_SELECTED
        self.draw_schem_color = misc.COLOR_NORMAL
        self.text_extends = []
        self.schem_extends = []
    
    @undoable
    def set_text_field_value(self, code, value):
        if self.fields and code in self.fields:
            oldval = self.fields[code]['value']
            self.fields[code]['value'] = value
            yield "Modify '{}' element field from '{}' to '{}'".format(self.name, oldval, value)
            # Undo action
            self.fields[code]['value'] = oldval
            
    def get_text_field(self, code):
        if self.fields and code in self.fields:
            return self.fields[code]
        
    def get_res_field(self, code):
        if self.res_fields and code in self.res_fields:
            return self.res_fields[code]

    def draw(self, context, select=False):
        """Draw the schematic model"""
        self.render_element(context)
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
                'fields': copy.deepcopy(self.fields)}
    
    def set_model(self, model):
        """Set storage model"""
        if model['code'] == self.code:
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            self.fields = copy.deepcopy(model['fields'])
            
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
    
    def get_field_dict(self, field_type, caption, unit, value, max_chars=None, 
                       validation_func=None, selection_list=None, decimal=6, 
                       status_floating=False, status_live=True,
                       inactivate=False,
                       click_to_edit_message=None,
                       alter_structure=False):
        field_dict = dict()
        field_dict['type'] = field_type
        field_dict['caption'] = caption
        field_dict['unit'] = unit
        field_dict['value'] = value
        field_dict['max_chars'] = max_chars
        field_dict['validation_func'] = validation_func
        field_dict['selection_list'] = selection_list
        field_dict['decimal'] = decimal
        field_dict['status_floating'] = status_floating
        field_dict['status_enable'] = status_live
        field_dict['status_inactivate'] = inactivate
        field_dict['click_to_edit_message'] = click_to_edit_message
        field_dict['alter_structure'] = alter_structure
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
        
    def get_power_model(self, code):
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
        
class ElementAssembly(ElementModel):
    """Class for rendering element assemblies"""
    def __init__(self, children=None):
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
        self.element_rect_width = None
        self.element_rect_height = None
        # State variables
        
        if children:
            self.set_children(children)
        
          
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
                'element_rect_height': self.element_rect_height}
    
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
        
    def set_children(self, children):
        # Setup model
        rects = []
        for child in set(children):
            rects.append(cairo.RectangleInt(*child.get_dimensions()))
        element_region = cairo.Region(rects)
        element_rect = element_region.get_extents()
        self.x = element_rect.x - 10
        self.y = element_rect.y - 10
        self.element_rect_width = element_rect.width + 20
        self.element_rect_height = element_rect.height + 20
        
        
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
            self.update_points(points)
    
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
        
    def update_points(self, points):
        self.points = points
        if len(self.points) > 1:
            # Set dimenstions
            (self.x, self.y, self.model_width, self.model_height) = misc.rect_from_points(*self.points)
            def local(port):  # convert to local coordinates
                x = (port[0] - self.x)/misc.M
                y = (port[1] - self.y)/misc.M
                return (x,y)
            
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
    
    def get_model(self):
        """Get storage model"""
        # Get reference for child
        return {'code': self.code,
                'x': self.x,
                'y': self.y,
                'orientation': self.orientation,
                'ports': copy.deepcopy(self.ports),
                'fields': copy.deepcopy(self.fields),
                'points': copy.deepcopy(self.points)}
    
    def set_model(self, model):
        """Set storage model"""
        if model['code'] == self.code:
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            self.fields = copy.deepcopy(model['fields'])
            points = copy.deepcopy(model['points'])
            if points:
                self.update_points(points)


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


class Template(ElementModel):
    """Class for rendering cross reference elements"""
    def __init__(self, width=misc.PAGE_WIDTH, height=misc.PAGE_HEIGHT):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_template'
        self.name = 'Template'
        self.group = 'Miscellaneous'
        self.icon = None
        self.ports = []
        self.fields = dict()
        
        self.border_left = 15/misc.POINT_TO_MM/misc.M
        self.border_right = 5/misc.POINT_TO_MM/misc.M
        self.border_top = 5/misc.POINT_TO_MM/misc.M
        self.border_bottom = 5/misc.POINT_TO_MM/misc.M
        self.border_width = 5/misc.POINT_TO_MM/misc.M
        self.set_dimensions(width, height)
        
    def set_dimensions(self, width=misc.PAGE_WIDTH, height=misc.PAGE_HEIGHT):
        # Set page dimensions
        self.model_width = width/misc.POINT_TO_MM/misc.M
        self.model_height = height/misc.POINT_TO_MM/misc.M
        # Set drawing area dimentions
        drawing_width = self.model_width - self.border_left - self.border_right - 2*self.border_width
        drawing_height = self.model_height - self.border_top - self.border_bottom - 2*self.border_width
        # Reference system dimentions
        horizontal_ref_nos = 2*round(drawing_width/2/(50/misc.POINT_TO_MM/misc.M))
        vertical_ref_nos = 2*round(drawing_height/2/(50/misc.POINT_TO_MM/misc.M))
        horizontal_ref_length = drawing_width/horizontal_ref_nos
        vertical_ref_length = drawing_height/vertical_ref_nos
        D = self.border_width/2 - misc.SCHEM_FONT_SIZE/ misc.M/2
        # Helper functions
        def line(x, y, length, orientation):
            if orientation == 'horizontal':
                return ['LINE',(x, y), (x+length, y), []]
            else:
                return ['LINE',(x, y), (x, y+length), []]
        
        self.text_model = []
        self.schem_model = [ 
                             # Outer border
                             ['RECT',(self.border_left, self.border_top), 
                              self.model_width - self.border_left - self.border_right,
                              self.model_height - self.border_top - self.border_bottom,
                              False, []],
                             # Inner border
                             ['RECT',(self.border_left + self.border_width, self.border_top + self.border_width), 
                              drawing_width, drawing_height,
                              False, [], 'thick'],
                             # Cut mark rectangle 1
                             ['RECT',(0,0), self.border_width, 2*self.border_width, True, []],
                             ['RECT',(0,0), 2*self.border_width, self.border_width, True, []],
                             # Cut mark rectangle 2
                             ['RECT',(0,self.model_height-self.border_width), 2*self.border_width, self.border_width, True, []],
                             ['RECT',(0,self.model_height-2*self.border_width), self.border_width, 2*self.border_width, True, []],
                             # Cut mark rectangle 2
                             ['RECT',(self.model_width-self.border_width,0), self.border_width, 2*self.border_width, True, []],
                             ['RECT',(self.model_width-2*self.border_width,0), 2*self.border_width, self.border_width, True, []],
                             # Cut mark rectangle 2
                             ['RECT',(self.model_width-self.border_width,self.model_height-2*self.border_width), self.border_width, 2*self.border_width, True, []],
                             ['RECT',(self.model_width-2*self.border_width,self.model_height-self.border_width), 2*self.border_width, self.border_width, True, []],
                             # Centre lines
                             line(self.border_left+self.border_width+drawing_width/2, self.border_top+self.border_width, self.border_width, 'vertical'),
                             line(self.border_left+self.border_width+drawing_width/2, self.border_top+drawing_height, self.border_width, 'vertical'),
                             line(self.border_left+self.border_width, self.border_top+self.border_width+drawing_height/2, self.border_width, 'horizontal'),
                             line(self.border_left+drawing_width, self.border_top+self.border_width+drawing_height/2, self.border_width, 'horizontal'),
                           ]
        # Draw reference lines and text
        for refno in range(1, horizontal_ref_nos+1):
            x = self.border_left + self.border_width + horizontal_ref_length * refno
            y1 = self.border_top
            y2 = self.border_top + self.border_width + drawing_height
            if refno < horizontal_ref_nos:
                self.schem_model.append(line(x, y1, self.border_width, 'vertical'))
                self.schem_model.append(line(x, y2, self.border_width, 'vertical'))
            self.text_model.append([(x-horizontal_ref_length/2,y1+ D), str(refno), True])
            self.text_model.append([(x-horizontal_ref_length/2,y2+ D), str(refno), True])
        ignored_count = 0
        for refno in range(1, vertical_ref_nos+1):
            y = self.border_top + self.border_width + vertical_ref_length * refno
            x1 = self.border_left
            x2 = self.border_left + self.border_width + drawing_width
            refcode = chr(refno+64+ignored_count)
            if refcode in ('I','O'):
                ignored_count += 1
                refcode = chr(refno+64+ignored_count)
            if refno < vertical_ref_nos:
                self.schem_model.append(line(x1, y, self.border_width, 'horizontal'))
                self.schem_model.append(line(x2, y, self.border_width, 'horizontal'))
            self.text_model.append([(x1+self.border_width/3,y-vertical_ref_length/2), refcode, True])
            self.text_model.append([(x2+self.border_width/3,y-vertical_ref_length/2), refcode, True])
            
    def modify_extends(self):
        pass
            
class TitleBlock(ElementModel):
    """Class for rendering cross reference elements"""
    def __init__(self):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_template'
        self.name = 'Template'
        self.group = 'Miscellaneous'
        self.icon = None
        self.ports = []
        self.fields = dict()
        
        F = 1/misc.POINT_TO_MM/misc.M
        D = 1*F
        T = misc.SCHEM_FONT_SIZE/misc.M + 2*D
        self.model_width = 180*F
        self.model_height = 36*F
        self.schem_model = [['RECT',(0,0), self.model_width, self.model_height, False, []],
                            # Vertical lines
                            ['LINE',(73*F, 0), (73*F, 36*F), []],
                            ['LINE',(130*F, 9*F), (130*F, 36*F), []],
                            ['LINE',(28*F, 0), (28*F, 9*F), []],
                            ['LINE',(118*F, 0), (118*F, 9*F), []],
                            ['LINE',(163*F, 0), (163*F, 9*F), []],
                            ['LINE',(137*F, 27*F), (137*F, 36*F), []],
                            ['LINE',(160*F, 27*F), (160*F, 36*F), []],
                            ['LINE',(170*F, 27*F), (170*F, 36*F), []],
                            # Horizontal lines
                            ['LINE',(0, 9*F), (180*F, 9*F), []],
                            ['LINE',(73*F, 18*F), (180*F, 18*F), []],
                            ['LINE',(130*F, 27*F), (180*F, 27*F), []], ]
        self.text_model = [[(D, D), 'Responsible dept.', True, misc.TITLE_FONT_SIZE_SMALL], 
                           [(28*F+D, D), 'Technical reference', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(73*F+D, D), 'Created by', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(118*F+D, D), 'Approved by', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(73*F+D, 9*F+D), 'Document Type', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(73*F+D, 18*F+D), 'Title, Supplementary Title', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(130*F+D, 9*F+D), 'Document Status', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(130*F+D, 27*F+D), 'Rev.', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(137*F+D, 27*F+D), 'Date of issue', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(160*F+D, 27*F+D), 'Lang.', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(170*F+D, 27*F+D), 'Sheet', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(D, 9*F-T), '${drawing_field_dept}', True, misc.TITLE_FONT_SIZE], 
                           [(28*F+D, 9*F-T), '${drawing_field_techref}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 9*F-T), '${drawing_field_created}', True, misc.TITLE_FONT_SIZE],
                           [(118*F+D, 9*F-T), '${drawing_field_approved}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 18*F-T), '${type}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 27*F-T), '${project_name}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 27*F+D), '${title}', True, misc.TITLE_FONT_SIZE],
                           [(130*F+D, 18*F-T), '${status}', True, misc.TITLE_FONT_SIZE],
                           [(130*F+D, 36*F-T), '${rev}', True, misc.TITLE_FONT_SIZE],
                           [(137*F+D, 36*F-T), '${date_of_issue}', True, misc.TITLE_FONT_SIZE],
                           [(160*F+D, 36*F-T), '${drawing_field_lang}', True, misc.TITLE_FONT_SIZE],
                           [(170*F+D, 36*F-T), '${sheet_no}', True, misc.TITLE_FONT_SIZE],
                           [(73*F/2, 18*F-T), '${drawing_field_address}', True, misc.TITLE_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(130*F+50*F/2, 22.5*F-0.5*T), '${drawing_no}', True, misc.TITLE_FONT_SIZE, misc.SCHEM_FONT_WEIGHT_BOLD, 'center'], ]
    
    def set_fields(self, fields):
        self.fields = fields
        # Set page dimensions
        border_right = 5/misc.POINT_TO_MM/misc.M
        border_bottom = 5/misc.POINT_TO_MM/misc.M
        border_width = 5/misc.POINT_TO_MM/misc.M
        
        self.x = (self.fields['page_width']['value']/misc.M - border_right - border_width - self.model_width)*misc.M
        self.y = (self.fields['page_height']['value']/misc.M - border_bottom - border_width - self.model_height)*misc.M
        
    def modify_extends(self):
        pass
