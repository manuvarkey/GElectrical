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
from gi.repository import Gtk, Gdk
import cairo

# local files import
from .. import misc
from ..misc import undoable, group
from ..elementmodel.element import ElementModel, ElementGroup
from ..elementmodel.template import Template, TitleBlock
from ..elementmodel.elementassembly import ElementAssembly
from ..elementmodel.reference import Reference
from ..elementmodel.wire import Wire


# Get logger object
log = logging.getLogger(__name__)


class DrawingModel:
    """Class for modelling a drawing"""
    
    def __init__(self, parent, program_state):
        
        # State variables
        self.parent = parent
        self.program_state = program_state
        self.program_settings = program_state['program_settings_main']
        self.project_settings = program_state['project_settings']
        self.project_settings_main = program_state['project_settings_main']
        self.grid_width = misc.GRID_WIDTH
        self.element_models = self.program_state['element_models']
        self.floating_model = None
        self.wire_points = []
        self.selected_ports = []
        self.selected_port_color = misc.COLOR_SELECTED
        self.stack = program_state['stack']
        self.assembly_dict = dict()
        self.element_gid_mapping = dict()  # Element slno -> gid mapping
        self.element_gid_mapping_inv = dict()  # Element gid -> slno mapping
        self.gid = 0
        
        # Data
        self.fields = {'name':          misc.get_field_dict('str', 'Sheet Name', '', 'Sheet', status_inactivate=False),
                       'page_size':     misc.get_field_dict('str', 'Page Size', '', 'A3', status_inactivate=False, selection_list=list(misc.paper_sizes.keys())),
                       'page_width':    misc.get_field_dict('float', 'Page Width', 'points', 1000, status_inactivate=True, decimal=0),
                       'page_height':   misc.get_field_dict('float', 'Page Height', 'points', 1000, status_inactivate=True, decimal=0),
                       'title':         misc.get_field_dict('str', 'Title', '', 'TITLE', status_inactivate=False),
                       'drawing_no':    misc.get_field_dict('str', 'Drawing Number', '', 'PROJECT/ELEC/SLD/1', status_inactivate=False),
                       'sheet_no':      misc.get_field_dict('str', 'Sheet No.', '', '1', status_inactivate=False),
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
        # Flags
        self.models_drawn = False
        
        # Initialisation
        self.update_title_block()
        
    ## Export/Import functions
    
    def __getitem__(self, index):
        if len(self.elements) > index:
            return self.elements[index]
        
    def get_gid(self):
        self.gid += 1
        return self.gid
    
    def export_drawing(self, context):
        self.draw_model(context, select=False)
    
    def get_model(self):
        """Get storage model"""
        element_models = []
        for element in self.elements:
            if element.code not in misc.DISPLAY_ELEMENT_CODES:
                element_models.append(element.get_model())
        model = dict()
        model['fields'] = misc.get_fields_trunc(self.fields)
        model['elements'] = element_models
        return ['DrawingModel', model]
            
    def set_model(self, model, copy_elements=True):
        """Set storage model"""
        self.elements = []
        if model[0] == 'DrawingModel':
            if copy_elements:
                # Load elements
                for base_model in model[1]['elements']:
                    code = base_model['code']
                    if code == 'element_assembly':
                        element = ElementAssembly()
                    elif code == 'element_wire':
                        element = Wire()
                    else:
                        element = self.program_state['element_models'][code](project_settings=self.project_settings)
                        if code in misc.LOADPROFILE_CODES:
                            element.fields['load_profile']['selection_list'] = self.parent.loadprofiles
                    element.set_model(base_model, self.get_gid())
                    self.elements.append(element)
                    
                # Update gid_assembly for elements
                for el_no, element in enumerate(self.elements):
                    if element.code == 'element_assembly':
                        children_codes = element.get_children()
                        gid_assembly = element.get_gid()
                        for page, child_el_no in children_codes:
                            child_element = self.elements[child_el_no]
                            child_element.set_gid_assembly(gid_assembly)
                    
            self.fields = misc.update_fields(self.fields, model[1]['fields'])
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
            self.models_drawn = False
            
    ## Update functions
            
    def update_state_variables(self):
        """Update state variables for elements"""
        self.assembly_dict = dict()
        self.element_gid_mapping = dict()
        self.element_gid_mapping_inv = dict()
        
        # Populate state variables from elements
        for el_no, element in enumerate(self.elements):
            gid = element.get_gid()
            gid_assembly = element.get_gid_assembly()
            
            if gid_assembly:
                if gid_assembly in self.assembly_dict:
                    self.assembly_dict[gid_assembly].append(gid)
                else:
                    self.assembly_dict[gid_assembly] = [gid]

            self.element_gid_mapping[el_no] = gid
            self.element_gid_mapping_inv[gid] = el_no
            
    def update_elements(self):
        """Update elements after elements are drawn"""
        self.update_state_variables()
        page = self.parent.get_drawing_model_index(self)
        # Update elements from mapped data
        for el_no, element in enumerate(self.elements):
            code = element.code
            if code == 'element_assembly':
                children_codes_new = []
                children = []
                gid_assembly = self.element_gid_mapping[el_no]
                if gid_assembly in self.assembly_dict:
                    for gid in self.assembly_dict[gid_assembly]:
                        child_el_no = self.element_gid_mapping_inv[gid]
                        child = self.elements[child_el_no]
                        children_codes_new.append((page, child_el_no))
                        children.append(child)
                if self.models_drawn:
                    element.set_children(children_codes_new, children)
                else:
                    element.set_children(children_codes_new)
        
    def set_sheet_name(self, sheet_name):
        self.fields['name']['value'] = sheet_name
        
    ## Query Functions
    
    def get_sheet_name(self):
        return self.fields['name']['value']
    
    def get_page_field(self, code):
        if code in self.fields:
            return self.fields[code]
    
    def get_selected(self, assembly_info=False, codes=None):
        selected = []
        for element in self.elements:
            if element.get_selection() is True:
                if (codes and element.code in codes) or codes is None:
                    selected.append(element)
        if assembly_info:
            assembly_dict = dict()
            for slno, element in enumerate(selected):
                if element.code == 'element_assembly':
                    assembly_dict[slno] = []
                    children = element.get_children()
                    for k1, k2 in children:
                        child = self.elements[k2]
                        if child in selected:
                            child_index = selected.index(child)
                            assembly_dict[slno].append(child_index)
            return selected, assembly_dict
        else:
            return selected
    
    def get_selected_codes(self, codes=None):
        selected = []
        for slno, element in enumerate(self.elements):
            if element.get_selection() is True:
                if (codes and element.code in codes) or codes is None:
                    selected.append(slno)
        return selected
    
    def get_element_codes(self, codes=None):
        selected = []
        for slno, element in enumerate(self.elements):
            if (codes and element.code in codes) or codes is None:
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
        self.update_elements()
            
        yield "Update draw element at '{}'".format(index)
        # Undo action
        self.update_element_at_index(old_element, index)
        self.update_elements()
            
    @undoable            
    def insert_element_at_index(self, element, index=None):
        if index:
            self.elements.insert(index, element)
            insert_index = index
        else:
            self.elements.append(element)
            insert_index = len(self.elements) - 1
        self.update_elements()
            
        yield "Add draw element at '{}'".format(insert_index)
        # Undo action
        self.delete_rows([insert_index])
        self.update_elements()
                
    @undoable
    def delete_rows(self, rows):
        old_rows = []
        rows.sort(reverse=True)
        for index in rows:
            old_element = self.elements.pop(index)
            old_rows.append((index, old_element))
        self.update_elements()
        
        yield "Delete draw elements at '{}'".format(rows)
        # Undo action
        for index, old_element in old_rows:
            self.insert_element_at_index(old_element, index)
        self.update_elements()
            
                
    def add_element(self, x, y, code, grid_constraint=False, select=False):
        if code is not None:
            if grid_constraint:  # Modify x,y to correspond to grid
                x,y = self.get_grid_point(x,y)
            model = self.element_models[code]
            element = model((x, y), project_settings=self.project_settings)
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
            
    def update_select(self, x, y, w=0, h=0, retain_selection=True, whitelist=None):
        selected = False
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        rect = cairo.RectangleInt(x, y, w, h)  # selection rectangle
        for elno, element in enumerate(self.elements):
            if (whitelist and (elno in whitelist)) or whitelist is None:
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
        title_fields['project_name'] = self.project_settings_main['project_name']
        title_fields['drawing_field_dept'] = self.project_settings_main['drawing_field_dept']
        title_fields['drawing_field_techref'] = self.project_settings_main['drawing_field_techref']
        title_fields['drawing_field_created'] = self.project_settings_main['drawing_field_created']
        title_fields['drawing_field_approved'] = self.project_settings_main['drawing_field_approved']
        title_fields['drawing_field_lang'] = self.project_settings_main['drawing_field_lang']
        title_fields['drawing_field_address'] = self.project_settings_main['drawing_field_address']
        self.title_block.set_fields(title_fields)
    
    def add_assembly_from_selection(self):
        selected = self.get_selected()
        codes = self.get_selected_codes()
        drg_no = self.parent.get_drawing_model_index(self)
        element_codes = [(drg_no, code) for code in codes]
        if selected:
            # Update elements
            for code, element in zip(codes, selected):
                if isinstance(element, ElementAssembly) and len(selected) > 1:
                    index = self.elements.index(element)
                    selected.remove(element)
                    element_codes.remove((drg_no,index))
                    assembly = ElementAssembly(element_codes, selected)
                    gid_assembly = self.get_gid()
                    assembly.set_gid(gid_assembly)
                    # Update element assembly ids
                    for element in selected:
                        element.set_gid_assembly(gid_assembly)
                    self.update_element_at_index(assembly, index)
                    return
            # For new items
            assembly = ElementAssembly(element_codes, selected)
            gid_assembly = self.get_gid()
            assembly.set_gid(gid_assembly)
            # Update element assembly ids
            for element in selected:
                element.set_gid_assembly(gid_assembly)
            self.insert_element_at_index(assembly)
        
    def delete_selected_rows(self):
        selected = self.get_selected_codes()
        self.delete_rows(selected)

    def clear_results(self):
        rows = []
        for el_no, element in enumerate(self.elements):
            # If display element, delete element
            if element.code in misc.DISPLAY_ELEMENT_CODES:
                rows.append(el_no)
            # Else clear results
            else:
                element.res_fields = dict()
        self.delete_rows(rows)
            
    ## Floating model functions
    
    def set_floating_model_from_code(self, code):
        """Add a floating model"""
        if code is not None:
            model = self.element_models[code]
            element = model(project_settings=self.project_settings)
            element.set_gid(self.get_gid())
            self.floating_model = ElementGroup()
            self.floating_model.add_elements([element])
        return element
            
    def add_floating_model(self, elements, assembly_dict=None):
        """Add a floating model"""
        self.floating_model = ElementGroup()
        self.floating_model.add_elements(elements, assembly_dict)
        
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
            with group(self, 'Insert element(s) at ' + str(port)):
                elements_copy = []
                # Insert elements inside elementgroup
                for el_no, element in enumerate(self.floating_model.elements):
                    element_model = element.get_model()
                    code = element.code
                    if code == 'element_assembly':
                        element_copy = ElementAssembly()
                    elif code == 'element_wire':
                        element_copy = Wire()
                    else:
                        element_copy = self.element_models[code](project_settings=self.project_settings)
                    element_copy.set_model(element_model, self.get_gid())
                    if element_copy.code in misc.LOADPROFILE_CODES:
                        element_copy.fields['load_profile']['selection_list'] = self.parent.loadprofiles
                    self.insert_element_at_index(element_copy)
                    elements_copy.append(element_copy)
                # Update gid_assembly for elements
                for el_no, element in enumerate(elements_copy):
                    if element.code == 'element_assembly':
                        children_codes = self.floating_model.assembly_dict[el_no]
                        gid_assembly = element.get_gid()
                        for child_el_no in children_codes:
                            child_element = elements_copy[child_el_no]
                            child_element.set_gid_assembly(gid_assembly)
            
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
        
    def draw_model(self, context, select=False, whitelist=None):
        """Draw the schematic model"""
        self.title_block.draw(context)
        self.template.draw(context)
        for elno, element in enumerate(self.elements):
            # If reference not linked display error
            if element.code in misc.REFERENCE_CODES:
                if element.fields['ref']['value'] in ('', '?', 'CR?'):
                    element.draw_schem_color = misc.COLOR_SELECTED_WARNING
                else:
                    element.draw_schem_color = misc.COLOR_NORMAL
            # Draw considering whitelist
            if whitelist is not None and (elno not in whitelist):
                element.draw(context, select, override_color=misc.COLOR_INACTIVE)
            else:
                element.draw(context, select)
        self.draw_selected_ports(context)
        self.models_drawn = True
            
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
