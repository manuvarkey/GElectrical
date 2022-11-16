#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# project
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

import logging, copy, datetime, io
from gi.repository import Gtk, Gdk
import cairo
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

# local files import
from .. import misc
from ..misc import undoable, group
from .drawing import DrawingModel
from ..view.drawing import DrawingView
from ..view.graph import GraphViewDialog, GraphImage
from ..model.graph import GraphModel
from .networkmodel import NetworkModel
from .pandapower import PandaPowerModel

# Get logger object
log = logging.getLogger(__name__)


class ProjectModel:
    """Class for modelling a project"""
    
    def __init__(self, window, program_state):
        # Data
        self.drawing_models = []
        program_settings = program_state['program_settings_main']
        self.fields = misc.default_project_settings
        self.fields['Information']['drawing_field_dept']['value'] = program_settings['drawing_field_dept']['value']
        self.fields['Information']['drawing_field_techref']['value'] =  program_settings['drawing_field_techref']['value']
        self.fields['Information']['drawing_field_created']['value'] =  program_settings['drawing_field_created']['value']
        self.fields['Information']['drawing_field_approved']['value'] = program_settings['drawing_field_approved']['value']
        self.fields['Information']['drawing_field_lang']['value'] = program_settings['drawing_field_lang']['value']
        self.fields['Information']['drawing_field_address']['value'] = program_settings['drawing_field_address']['value']
        program_state['project_settings_main'] = self.fields['Information']
        self.loadprofiles = misc.DEFAULT_LOAD_PROFILE
        
        # State variables
        self.window = window
        self.program_state = program_state
        self.drawing_notebook = program_state['drawing_notebook']
        self.properties_view = program_state['properties_view']
        self.results_view = program_state['results_view']
        self.diagnostics_view = program_state['diagnostics_view']
        self.database_view = program_state['database_view']
        self.program_settings = program_settings
        self.drawing_views = []
        self.drawing_model = None
        self.drawing_view = None
        self.stack = program_state['stack']
        self.status = {'net_model': False, 'power_model': False, 'power_analysis': False}
        # Analysis varables
        self.networkmodel = None
        self.powermodel = None
        self.graph = None
        # Initialise tab
        self.add_page_vanilla()
        self.drawing_notebook.connect("switch-page", self.on_switch_tab)
        
    ## Functions
    
    def clear_status(self):
        """Clear module status"""
        self.status = {'net_model': False, 'power_model': False, 'power_analysis': False}
        self.networkmodel = None
        self.powermodel = None
    
    def get_project_fields(self, page='Information', full=False):
        if full:
            return self.fields
        else:
            return self.fields[page]
        
    def get_drawing_model_index(self, model):
        return self.drawing_models.index(model)
    
    @undoable
    def update_project_fields(self, new_fields):
        old_fields = self.fields
        self.fields = new_fields
        
        self.update_tabs()
        self.update_title_blocks()
        
        yield "Update project settings"
        # Undo action
        self.update_project_fields(old_fields)
        
    def edit_loadprofiles(self):
        xlim = misc.GRAPH_LOAD_TIME_LIMITS
        ylim = misc.GRAPH_LOAD_CURRENT_LIMITS
        xlabel = 'Time (Hr)'
        ylabel = 'Diversity Factor'
        dialog = GraphViewDialog(self.window, self.loadprofiles, xlim, ylim, xlabel, ylabel)
        dialog.run()
    
    def append_page(self):
        model = DrawingModel(self, self.program_state)
        slno = self.get_page_nos()
        # Except first page copy fields from first page
        if slno > 0:
            base_model = self.drawing_models[0].get_model()
            model.set_model(base_model, copy_elements=False)
            model.fields['sheet_no']['value'] = str(slno + 1)
            model.fields['date_of_issue']['value'] = datetime.datetime.today().strftime('%Y-%m-%d')
        sheet_name = "Sheet " + str(self.get_page_nos() + 1)
        model.set_sheet_name(sheet_name)
        add_slno = self.add_page(slno, model)
    
    @undoable
    def add_page(self, slno, model):
        self.add_page_vanilla(slno, model)
        
        yield "Add page at " + str(slno)
        # Undo action
        self.remove_page(slno)
        
    def add_page_vanilla(self, slno=None, model=None):
        if model:
            self.drawing_model = model
        else:
            self.drawing_model = DrawingModel(self, self.program_state)
            sheet_name = "Sheet " + str(self.get_page_nos() + 1)
            self.drawing_model.set_sheet_name(sheet_name)
            self.drawing_model.fields['date_of_issue']['value'] = datetime.datetime.today().strftime('%Y-%m-%d')
            
        if slno:
            # Setup model
            self.drawing_models.insert(slno, self.drawing_model)
            # Setup drawing view
            page = Gtk.Box()
            self.drawing_notebook.insert_page(page, None, slno) 
            self.drawing_view = DrawingView(self.window, page, self.drawing_model, self.program_state, self.program_settings, self.properties_view, self.results_view, self.database_view)
            self.drawing_views.insert(slno, self.drawing_view)
            self.drawing_notebook.show_all()
            self.set_page(slno)  # Switch to added page
            add_slno = slno
        else:
            # Setup model
            self.drawing_models.append(self.drawing_model)
            # Setup drawing view
            page = Gtk.Box()
            self.drawing_notebook.append_page(page, None)
            self.drawing_view = DrawingView(self.window, page, self.drawing_model, self.program_state, self.program_settings, self.properties_view, self.results_view, self.database_view)
            self.drawing_views.append(self.drawing_view)
            self.drawing_notebook.show_all()
            self.set_page(self.get_page_nos() -1)  # Switch to added page
            add_slno = self.get_page_nos() -1       
        return add_slno
        
    @undoable
    def remove_page(self, slno):
        delete_slno = None
        if self.get_page_nos() > 1 and slno < self.get_page_nos():
            del_model = self.drawing_models.pop(slno)
            self.drawing_views.pop(slno)
            page = self.drawing_notebook.get_nth_page(slno)
            self.drawing_notebook.detach_tab(page)
            delete_slno = slno
            if slno != 0:
                self.set_page(slno-1)
            else:
                self.set_page(0)
                
        yield "Remove page at " + str(delete_slno)
        # Undo action
        if delete_slno:
            self.add_page(delete_slno, del_model)
            
    def clear_all(self):
        # Delete all pages except first
        for slno in range(0,self.get_page_nos()):
            self.remove_page(slno)
        # Clear first page model
        blank_model = DrawingModel(self, self.program_state).get_model()
        self.drawing_models[0].set_model(blank_model)
        
    def get_page_nos(self):
        return len(self.drawing_models)
        
    def set_page(self, slno, switch_tab=True):
        if slno < self.get_page_nos():
            self.drawing_model = self.drawing_models[slno]
            self.drawing_view = self.drawing_views[slno]
            if switch_tab:
                self.drawing_notebook.set_current_page(slno)
            self.drawing_view.select_page()
            self.update_tabs(slno)
                
    def mark_page(self, slno):
        page = self.drawing_notebook.get_nth_page(slno)
        sheet_name = self.drawing_models[slno].fields['name']['value']
        label = self.drawing_notebook.get_tab_label(page).get_children()[0]
        label.set_markup('<span foreground="red"><b>{}</b></span>'.format(sheet_name))
        label.set_use_markup(True)
    
    def update_tabs(self, slno=None):
    
        def set_label(page, sheet_name, slno, close_button=True):
            
            def remove_page_callback(button, slno):
                self.remove_page(slno)
                
            label_hbox = Gtk.Box()
            page_label = Gtk.Label(sheet_name)
            label_hbox.pack_start(page_label, True, True, 0)
            if close_button:
                close_button = Gtk.Button.new_from_icon_name('window-close-symbolic', Gtk.IconSize.SMALL_TOOLBAR)
                close_button.set_relief(Gtk.ReliefStyle.NONE)
                close_button.connect("clicked", remove_page_callback, slno)
                label_hbox.pack_start(close_button, True, True, 0)
            self.drawing_notebook.set_tab_label(page, label_hbox)
            label_hbox.show_all()
            
        if slno:
            page = self.drawing_notebook.get_nth_page(slno)
            sheet_name = self.drawing_models[slno].fields['name']['value']
            if slno == 0:
                set_label(page, sheet_name, slno, close_button=False)
            else:
                set_label(page, sheet_name, slno)
            
        else:
            for slno in range(0, self.get_page_nos()):
                page = self.drawing_notebook.get_nth_page(slno)
                sheet_name = self.drawing_models[slno].fields['name']['value']
                self.drawing_notebook.set_tab_label_text(page, sheet_name)
                set_label(page, sheet_name, slno)
                if slno == 0:
                    set_label(page, sheet_name, slno, close_button=False)
                else:
                    set_label(page, sheet_name, slno)
                
    def update_title_blocks(self):
        for drawing_model in self.drawing_models:
            drawing_model.update_title_block()            
                
    def select_networkmodel(self, model):
        if model:
            for code, elementids in model:
                if code == 'node':
                    for k1, drawing_model in enumerate(self.drawing_models):
                        for k2, element in enumerate(drawing_model.elements):
                            gnodes = self.networkmodel.gnode_element_mapping_inverted[(k1,k2)]
                            for gnode in gnodes:
                                if gnode in elementids:
                                    element = self.drawing_models[k1][k2]
                                    element.set_selection(select=True, color=misc.COLOR_SELECTED_WARNING)
                                    self.mark_page(k1)
                else:
                    for k1,k2 in elementids:
                        element = self.drawing_models[k1][k2]
                        element.set_selection(select=True, color=misc.COLOR_SELECTED_WARNING)
                        self.mark_page(k1)
            self.drawing_view.refresh()
        log.info('ProjectModel - select_powermodel - select')
    
    ## Analysis functions
    
    def setup_base_model(self, elements=True, nodes=True):
        self.clear_status()
        self.networkmodel = NetworkModel(self.drawing_models)
        if elements:
            self.networkmodel.setup_base_elements()
        if nodes:
            self.networkmodel.setup_global_nodes()
        self.status['net_model'] = True
        log.info('ProjectModel - setup_base_model - model generated')
        
    def build_power_model(self):
        if self.status['net_model']:
            self.powermodel = PandaPowerModel(self.networkmodel, self.loadprofiles)
            self.powermodel.build_power_model()
            self.status['power_model'] = True
            log.info('ProjectModel - build_power_model - model generated')
        else:
            raise RuntimeError('ProjectModel - build_power_model - Network model not built')
        
    def run_diagnostics(self):
        """Run Diagnostics"""
        if self.status['power_model']:
            log.info('ProjectModel - run_diagnostics - running diagnostic...')
            diagnostic_results, ret_code = self.powermodel.run_diagnostics()
            self.diagnostics_view.update(diagnostic_results, self.select_networkmodel)
            self.status['power_analysis'] = True
            log.info('ProjectModel - run_diagnostics - diagnostic run')
            return ret_code
        else:
            raise RuntimeError('ProjectModel - run_diagnostics - Power model not built')
        
    def run_powerflow(self):
        """Run power flow"""
        if self.status['power_model']:
            self.powermodel.run_powerflow()
            self.status['power_analysis'] = True
            log.info('ProjectModel - run_powerflow - calculation run')
        else:
            raise RuntimeError('ProjectModel - run_powerflow - Power model not built')
    
    def run_powerflow_timeseries(self):
        """Run power flow"""
        if self.status['power_model']:
            self.powermodel.run_powerflow_timeseries()
            self.status['power_analysis'] = True
            log.info('ProjectModel - run_powerflow_timeseries - calculation run')
        else:
            raise RuntimeError('ProjectModel - run_powerflow_timeseries - Power model not built')
    
    def run_sym_sccalc(self):
        """Run symmetric short circuit calculation"""
        if self.status['power_model']:
            sim_settings = self.get_project_fields(page='Simulation')
            self.powermodel.run_sym_sccalc(lv_tol_percent=sim_settings['lv_tol_percent']['value'], 
                                           r_fault_ohm=sim_settings['r_fault_ohm']['value'], 
                                           x_fault_ohm=sim_settings['x_fault_ohm']['value'])
            self.status['power_analysis'] = True
            log.info('ProjectModel - run_sym_sccalc - calculation run')
        else:
            raise RuntimeError('ProjectModel - run_sym_sccalc - Power model not built')
    
    def run_linetoground_sccalc(self):
        """Run line to ground short circuit calculation"""
        if self.status['power_model']:
            sim_settings = self.get_project_fields(page='Simulation')
            self.powermodel.run_linetoground_sccalc(lv_tol_percent=sim_settings['lv_tol_percent']['value'], 
                                                    r_fault_ohm=sim_settings['r_fault_ohm']['value'], 
                                                    x_fault_ohm=sim_settings['x_fault_ohm']['value'])
            self.status['power_analysis'] = True
            log.info('ProjectModel - run_linetoground_sccalc - calculation run')
        else:
            raise RuntimeError('ProjectModel - run_linetoground_sccalc - Power model not built')
        
    def update_results(self):
        # Copy node data to element power model
        if self.status['power_analysis']:
            self.powermodel.update_results()
            log.info('ProjectModel - update_results - results updated')
        else:
            log.info('ProjectModel - update_results - no results to update')
        
    ## Model functions
    
    @undoable
    def renumber_elements(self, mode):
        """Renumber drawing elements"""
        
        # Setup network model
        self.setup_base_model(elements=True, nodes=False)
        base_elements = self.networkmodel.base_elements
        
        # Setup local variables
        refs = misc.ReferenceCounter(1)  # Counter for base references
        prefix_codes = dict()  # Prefix codes for elements for assembly references
        changed = []  # Undo tracking of changed elements
        base_ref = dict()  # Base references dictionary
        for code, model in self.program_state['element_models'].items():
            base_ref[code] = model().fields['ref']['value'].strip('?')
        base_ref['element_assembly'] = 'A'
        
        # Get selected elements
        if mode == "Selected elements only":
            selected_elements = self.drawing_model.get_selected()
            selected_keys = self.drawing_model.get_selected_codes()
            drg_no = self.get_drawing_model_index(self.drawing_model)
            selected_keys = [(drg_no, key) for key in selected_keys]
        
        # Update largest refs for assembly elements
        if mode in ("New elements only", "Selected elements only"):
            for key, model in base_elements.items():
                code = model.code
                if code == 'element_assembly':
                    ref = model.fields['ref']['value']
                    try:
                        count = int(ref.lstrip(base_ref[code]))
                        refs[code] = max(refs[code], count+1)
                    except:
                        pass
                    
        # Number assembly elements
        if mode == "All":
            for key, model in base_elements.items():
                code = model.code
                if code == 'element_assembly':
                    ref = model.fields['ref']['value']
                    new_ref = base_ref[code] + str(refs[code])
                    refs[code] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        elif mode == "New elements only":
            for key, model in base_elements.items():
                code = model.code
                if code == 'element_assembly':
                    ref = model.fields['ref']['value']
                    if ref.strip('?') == base_ref[code]:
                        new_ref = base_ref[code] + str(refs[code])
                        refs[code] += 1
                        base_elements[key].set_text_field_value('ref', new_ref)
                        changed.append([key, ref])
        elif mode == "Selected elements only":
            for key, model in zip(selected_keys, selected_elements):
                code = model.code
                if code == 'element_assembly':
                    ref = model.fields['ref']['value']
                    new_ref = base_ref[code] + str(refs[code])
                    refs[code] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        
        # Update prefix for elements inside assembly
        for key, model in base_elements.items():
            code = model.code
            if code == 'element_assembly':
                children = model.get_children()
                for drg_no, element_index in children:
                    prefix_codes[(drg_no, element_index)] = model.fields['ref']['value'] + '-'
        
        excluded_codes = (*misc.REFERENCE_CODES, 'element_wire', 'element_assembly')
        
        # Update largest refs for elements
        if mode in ("New elements only", "Selected elements only"):
            for key, model in base_elements.items():
                code = model.code
                if code not in excluded_codes:
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    try:
                        # Add prefixed base to base_ref
                        if prefix + code not in base_ref:
                            base_ref[prefix + code] = prefix + base_ref[code]
                        count = int(ref.lstrip(base_ref[prefix + code]))
                        refs[prefix + code] = max(refs[prefix + code], count+1)
                    except:
                        pass
        
        # Number remaining elements
        if mode == "All":
            for key, model in base_elements.items():
                code = model.code
                if code not in excluded_codes:
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    new_ref = prefix + base_ref[code] + str(refs[prefix + code])
                    refs[prefix + code] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        elif mode == "New elements only":
            # Modify references
            for key, model in base_elements.items():
                code = model.code
                if code not in excluded_codes:
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    if ref.strip('?') == base_ref[code]:
                        new_ref = prefix + base_ref[code] + str(refs[prefix + code])
                        refs[prefix + code] += 1
                        base_elements[key].set_text_field_value('ref', new_ref)
                        changed.append([key, ref])
        elif mode == "Selected elements only":
            for key, model in zip(selected_keys, selected_elements):
                code = model.code
                if code not in excluded_codes:
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    new_ref = prefix + base_ref[code] + str(refs[prefix + code])
                    refs[prefix + code] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        
        yield "Renumber Elements - " + mode
        # Undo action
        for key, ref in changed:
            base_elements[key].set_text_field_value('ref', ref)
            
    def get_reference_code(self):
        """Renumber drawing elements"""
        
        # Setup network model
        self.setup_base_model(elements=True, nodes=False)
        base_elements = self.networkmodel.base_elements
        # Setup local variables
        counter = 1
        # Update largest counter for reference elements
        for key, model in base_elements.items():
            code = model.code
            if code in misc.REFERENCE_CODES:
                ref = model.fields['ref']['value']
                try:
                    count = int(ref.lstrip('CR'))
                    counter = max(counter, count+1)
                except:
                    pass
        return 'CR' + str(counter)
    
    def link_references(self, base_ref, selected_dict):
        """Link reference items"""
        (selected_page, selected_slno) = base_ref
        selected_element = copy.deepcopy(self.drawing_models[selected_page][selected_slno])
        
        reference = selected_element.fields['ref']['value']
        if reference in ('', '?', 'CR?'):
            reference = self.get_reference_code()
        sheet = str(selected_page + 1)
        title = selected_element.fields['title']['value']
        subtitle = selected_element.fields['sub_title']['value']
        selected_sheets = [str(page+1) for page in selected_dict if selected_dict[page]]
        if sheet not in selected_sheets:
            selected_sheets.append(sheet)
            
        with group(self, "Link reference " + reference):
            for page, el_nos in selected_dict.items():
                if el_nos:
                    for el_no in el_nos:
                        element = copy.deepcopy(self.drawing_models[page][el_no])
                        selected_sheets_element = [x for x in selected_sheets if x != str(page+1)] 
                        element.fields['ref']['value'] = reference
                        element.fields['sheet']['value'] =  ','.join(selected_sheets_element)
                        element.fields['title']['value'] = title
                        element.fields['sub_title']['value'] = subtitle
                        self.drawing_models[page].update_element_at_index(element ,el_no)
            selected_element.fields['ref']['value'] = reference
            selected_sheets.remove(sheet)
            selected_element.fields['sheet']['value'] =  ','.join(selected_sheets)
            self.drawing_models[selected_page].update_element_at_index(selected_element ,selected_slno)
    
    ## Export/Import functions
    
    def export_html_report(self, filename):
        self.powermodel.export_html_report(filename)
        
    def export_json(self, filename):
        self.powermodel.export_json(filename)
        
    def export_pdf_report(self, filename, settings):
        template_path = misc.abs_path("templates")
        env = Environment(loader=FileSystemLoader(template_path))
        
        # General variables
        program_version = 'v' + misc.PROGRAM_VER
        project_settings = self.get_project_fields()
        gen_variables = {'program_version'        : 'v' + misc.PROGRAM_VER,
                         'project_name'           : project_settings['project_name']['value'],
                         'drawing_field_approved' : project_settings['drawing_field_approved']['value'],
                         'drawing_field_dept'     : project_settings['drawing_field_dept']['value'],
                         'drawing_field_address'  : project_settings['drawing_field_address']['value'].replace('\n','</br>')}
        
        # Elements
        element_captions = dict()
        element_refs = dict()
        element_tables = dict()
        element_lines = []
        element_loads = []
        element_switches = []
        loadprofile_captions_used = set()
        base_elements = self.networkmodel.base_elements
        # First pass add all required elements
        for key, model in base_elements.items():
            if 'ref' in model.fields and (model.code not in misc.REFERENCE_CODES) and (model.code != 'element_assembly'):
                element_captions[key] = model.fields['ref']['value'] + ' - ' + model.name
                element_refs[key] = model.fields['ref']['value']
                element_tables[key] = misc.fields_to_table(model.fields)
                
            # Lines
            if model.code in ['element_line', 'element_line_cable']:
                element_lines.append(model)
            # Loads
            if model.code in ['element_load']:
                element_loads.append(model)
            # Switches
            if model.code in ['element_switch', 'element_circuitbreaker']:
                element_switches.append(model)
            
            if model.code == 'element_load' and model.fields['load_profile']['value'] in self.loadprofiles:
                loadprofile_captions_used.add(model.fields['load_profile']['value'])
        # Second pass for adding assmebly details
        for key, model in base_elements.items():
            if model.code == 'element_assembly':
                assembly_fields = copy.deepcopy(model.fields)
                children_codes = model.children_codes
                children_list = []
                for child_code in children_codes:
                    if child_code in element_refs:
                        child_ref = element_refs[child_code]
                        children_list.append(child_ref)
                children_str = ''
                for s in children_list:
                    children_str = children_str + ', ' + s
                children_str = children_str[2:]
                assembly_fields['children'] = misc.get_field_dict('str', 'Sub-elements', '', children_str, status_inactivate=False)
                # Add element
                element_captions[key] = model.fields['ref']['value'] + ' - ' + model.name
                element_refs[key] = model.fields['ref']['value']
                element_tables[key] = misc.fields_to_table(assembly_fields)
        # Sort by reference
        element_captions = dict(sorted(element_captions.items(), key=lambda item:item[1]))
        element_tables = {key:element_tables[key] for key in element_captions}
                                 
        # BOQ
        boq_tables = dict()
        boq_captions = dict()
        E = misc.ELEMENT_FIELD
        R = misc.ELEMENT_RESULT
        # Lines
        if element_lines:
            col_codes = ['ref', 'name', 'designation', 'type', 'parallel', 'length_km', 'max_i_ka', 'df', 'in_service', 'loading_percent', 'pl_mw,ql_mvar']
            col_captions = ['Reference', 'Name', 'Designation', 'Type', '# Parallel Lines',  'Length', 'Imax', 'Derating Factor', 'In Service ?', '% Loading', 'P loss, Q loss']
            code_sources = [E,E,E,E,E,E,E,E,E,R,R]
            table = misc.elements_to_table(element_lines, col_codes, col_captions, code_sources, 'boq_lines')
            boq_tables['boq_lines'] = table
            boq_captions['boq_lines'] = 'Lines'
        # Loads
        if element_loads:
            col_codes = ['ref', 'name', 'sn_mva', 'cos_phi', 'mode', 'in_service', 'load_profile']
            col_captions = ['Reference', 'Name', 'Rated power', 'PF', 'Inductive ?', 'In Service ?', 'Load Profile']
            code_sources = [E,E,E,E,E,E,E]
            table = misc.elements_to_table(element_loads, col_codes, col_captions, code_sources, 'boq_loads')
            boq_tables['element_loads'] = table
            boq_captions['element_loads'] = 'Loads'
        # Switches
        if element_switches:
            col_codes = ['ref', 'type', 'poles', 'Un', 'In', 'closed']
            col_captions = ['Reference', 'Type', 'Poles', 'Un', 'In', 'Closed']
            code_sources = [E,E,E,E,E,E]
            table = misc.elements_to_table(element_switches, col_codes, col_captions, code_sources, 'boq_switches')
            boq_tables['element_switches'] = table
            boq_captions['element_switches'] = 'Switches'
        
        # Load profiles
        loadprofile_captions = {key:self.loadprofiles[key][0] for key in loadprofile_captions_used}
        # Sort
        loadprofile_captions = dict(sorted(loadprofile_captions.items(), key=lambda item:item[1]))
        # Add images
        loadprofile_images = dict()
        xlim = misc.GRAPH_LOAD_TIME_LIMITS
        ylim = misc.GRAPH_LOAD_CURRENT_LIMITS
        xlabel = 'Time (Hr)'
        ylabel = 'Diversity Factor'
        for loadprofile_caption in loadprofile_captions:
            title, graph_model = self.loadprofiles[loadprofile_caption]
            graph_image = GraphImage(xlim, ylim, '', xlabel, ylabel)
            graph_image.add_plots(graph_model)
            emb_image = graph_image.get_embedded_html_image(figsize=(500, 175))
            loadprofile_images[loadprofile_caption] = emb_image
            
        # Analysis options
        if settings['powerflow'] or settings['sc_sym'] or settings['sc_gf']:
            analysis_flag = True
        else: 
            analysis_flag = False
        ana_opt_table = misc.fields_to_table(self.get_project_fields(page='Simulation'))
        
        # Analysis results
        ana_res_captions = dict()
        ana_res_tables = dict()
        base_elements = self.networkmodel.base_elements
        # First pass add all required elements
        for key, model in base_elements.items():
            if 'ref' in model.fields and (model.code not in misc.REFERENCE_CODES) and (model.code != 'element_assembly'):
                ana_res_captions[str(key)+'_res'] = model.fields['ref']['value'] + ' - ' + model.name
                ana_res_tables[str(key)+'_res'] = misc.fields_to_table(model.res_fields)
        # Sort by reference
        ana_res_captions = dict(sorted(ana_res_captions.items(), key=lambda item:item[1]))
        ana_res_tables = {key:ana_res_tables[key] for key in ana_res_captions}
        
        # Load HTML file    
        template = env.get_template("report.html")
        template_vars = {'gen_variables': gen_variables,
                         'element_captions': element_captions,
                         'element_tables': element_tables,
                         'boq_tables': boq_tables,
                         'boq_captions': boq_captions,
                         'loadprofile_captions': loadprofile_captions,
                         'loadprofile_images': loadprofile_images,
                         'analysis_flag': analysis_flag,
                         'ana_opt_table': ana_opt_table,
                         'ana_res_tables': ana_res_tables,
                         'ana_res_captions': ana_res_captions
                        }
        html_out = template.render(template_vars)
        
        # Load CSS file
        template_css = env.get_template("report.css")
        template_vars_css = {'report_font': misc.REPORT_FONT_FACE}
        css_out = template_css.render(template_vars_css)
        css_obj = io.BytesIO(bytes(css_out, 'utf-8'))
        
        # Render PDF
        HTML(string=html_out).write_pdf(filename, stylesheets=[css_obj])
        
    def export_drawing(self, filename):
        surface = cairo.PDFSurface(filename, 0, 0)
        proj_fields = self.get_project_fields()
        surface.set_metadata(cairo.PDFMetadata.TITLE, proj_fields['project_name']['value'])
        surface.set_metadata(cairo.PDFMetadata.AUTHOR, proj_fields['drawing_field_approved']['value'])
        surface.set_metadata(cairo.PDFMetadata.SUBJECT, 'Electrical schematic drawing')
        surface.set_metadata(cairo.PDFMetadata.CREATOR, misc.PROGRAM_NAME + ' v' + misc.PROGRAM_VER)
        surface.set_metadata(cairo.PDFMetadata.CREATE_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        surface.set_metadata(cairo.PDFMetadata.MOD_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        context = cairo.Context(surface)
        for drawing_model in self.drawing_models:
            surface.set_size(drawing_model.fields['page_width']['value'], drawing_model.fields['page_height']['value'])
            drawing_model.export_drawing(context)
            surface.show_page()
        surface.finish()
        
    def print_drawing(self, context, page_nr):
        if page_nr < len(self.drawing_models):
            drawing_model = self.drawing_models[page_nr]
            drawing_model.export_drawing(context)
        
    def get_model(self):
        """Get storage model"""
        proj_pages = []
        drawing_names = []
        for slno, drawing_model in enumerate(self.drawing_models):
            page_name = 'proj_drawing_page_' + str(slno)+'.json'
            proj_pages.append((page_name, drawing_model.get_model()))
            drawing_names.append(page_name)
        proj_pages.append(('proj_loadprofiles.json', self.loadprofiles))
        proj_settings = {'proj_drawing_names'  : drawing_names,
                         'proj_fields'         : misc.get_fields_dict_trunc(self.fields)}
        return [proj_settings, proj_pages]
            
    def set_model(self, document, pages):
        """Set storage model"""
        self.clear_all()
        if ('proj_drawing_names' in document and 
            'proj_fields' in document and 
            'proj_loadprofiles.json' in pages):
            self.fields = misc.update_fields_dict(self.fields, document['proj_fields'])
            self.program_state['project_settings_main'] = self.fields['Information']
            self.loadprofiles = pages['proj_loadprofiles.json']
            slno = 0
            for page_name, page in pages.items():
                if page_name.startswith('proj_drawing_page_'):
                    if slno > 0:
                        self.append_page()
                    self.drawing_models[slno].set_model(page)
                    slno += 1
        else:
            return False
        # Switch to first page
        self.set_page(0)
        
    ## Callbacks
    
    def on_switch_tab(self, notebook, page, pagenum):
        """Refresh display on switching between views"""
        log.info('ProjectModel - on_switch_tab called - ' + str(pagenum))
        self.set_page(pagenum, switch_tab=False)
