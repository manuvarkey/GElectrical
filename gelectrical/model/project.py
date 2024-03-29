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

import logging, copy, datetime, io, math
from gi.repository import Gtk, Gdk, GLib
import cairo
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS

# local files import
from .. import misc
from ..misc import undoable, group
from .drawing import DrawingModel
from ..view.drawing import DrawingView
from ..view.graph import GraphViewDialog, GraphImage
from ..view.protection import ProtectionViewDialog
from .networkmodel import NetworkModel
from .pandapower import PandaPowerModel
from .rulescheck import electrical_rules_check

# Get logger object
log = logging.getLogger(__name__)


class ProjectModel:
    """Class for modelling a project"""
    
    def __init__(self, window, program_state):
        # Data
        self.drawing_models = []
        program_settings = program_state['program_settings_main']
        self.fields = misc.default_project_settings
        self.fields['Information']['drawing_field_dept']['value'] = copy.deepcopy(program_settings['drawing_field_dept']['value'])
        self.fields['Information']['drawing_field_techref']['value'] =  copy.deepcopy(program_settings['drawing_field_techref']['value'])
        self.fields['Information']['drawing_field_created']['value'] =  copy.deepcopy(program_settings['drawing_field_created']['value'])
        self.fields['Information']['drawing_field_approved']['value'] = copy.deepcopy(program_settings['drawing_field_approved']['value'])
        self.fields['Information']['drawing_field_lang']['value'] = copy.deepcopy(program_settings['drawing_field_lang']['value'])
        self.fields['Information']['drawing_field_address']['value'] = copy.deepcopy(program_settings['drawing_field_address']['value'])
        program_state['project_settings_main'] = self.fields['Information']
        program_state['project_settings'] = self.fields
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
        self.page_no = 0
        # Analysis varables
        self.status = {}
        self.clear_status()
        self.networkmodel = None
        self.powermodel = None
        # Initialise tab
        self.add_page_vanilla()
        self.tab_handler_id = self.drawing_notebook.connect("switch-page", self.on_switch_tab)
        self.drawing_notebook.connect("page_reordered", self.on_page_reordered)


    ## Functions
    
    def clear_status(self):
        """Clear module status"""
        self.status = {'net_model': False, 'node_elements': False, 'power_model': False, 'power_analysis': False, 'power_results': False}
    
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

        self.program_state['project_settings_main'] = self.fields['Information']
        self.program_state['project_settings'] = self.fields
        
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
        database_path = misc.open_library('load_profiles.csv')
        loadprofiles_copy = copy.deepcopy(self.loadprofiles)
        dialog = GraphViewDialog(self.window, 
                                'Edit Load Profiles',
                                loadprofiles_copy, 
                                xlim, ylim, xlabel, ylabel, 
                                 database_path=database_path)
        selected_graph, database_modified_flag = dialog.run()
        if database_modified_flag:
            self.modify_loadprofiles(loadprofiles_copy)

    def view_protection_coordination(self):
        selected_elements = self.get_selected(codes=misc.PROTECTION_ELEMENT_CODES + misc.DAMAGE_ELEMENT_CODES + ('element_display_node',))
        if selected_elements:
            # Populate voltage levels for breakers
            if self.status['power_results'] == False or self.stack.haschanged():
                self.setup_base_model(add_node_elements=False)  # Do not generate node elements
                self.build_power_model(which='powerflow')  # Build element voltages
                self.update_results(update_node_elements=False)  # Update element voltages. Do not overwrite node results.
            dialog = ProtectionViewDialog(self.window, self.program_state, selected_elements)
            dialog.run()
        else:
            return (misc.WARNING, 'No protection elements selected.')
        
    @undoable
    def modify_loadprofiles(self, loadprofiles):
        loadprofiles_old = copy.deepcopy(self.loadprofiles)
        self.loadprofiles = loadprofiles

        yield "Update load profiles"
        # Undo action
        self.loadprofiles = loadprofiles_old
    
    def append_page(self, copy_selected_sheet=False):
        model = DrawingModel(self, self.program_state)
        slno = self.get_page_nos()
        cur_slno = self.drawing_notebook.get_current_page()
        # Except first page copy fields from selected page
        if slno > 0:
            # Copy model from first page or selected page
            if copy_selected_sheet:
                base_model = self.drawing_models[cur_slno].get_model()
            else:
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
        self.drawing_notebook.set_tab_reorderable(page, True)
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

    @undoable
    def reorder_tab(self, prev_pagenum, pagenum):
        if prev_pagenum != pagenum:
            model = self.drawing_models.pop(prev_pagenum)
            view = self.drawing_views.pop(prev_pagenum)
            self.drawing_models.insert(pagenum, model)
            self.drawing_views.insert(pagenum, view)
            self.set_page(pagenum)
            self.update_tabs()
            self.reg_refs_sheets()

        yield 'Reorder tab - from {} to {}'.format(prev_pagenum, pagenum)
        if prev_pagenum != pagenum:
            self.reorder_tab(pagenum, prev_pagenum)
            self.update_tabs()
            self.reg_refs_sheets()
            
    def clear_all(self):
        # Delete all pages except first
        self.drawing_notebook.disconnect(self.tab_handler_id)
        for slno in range(0,self.get_page_nos()):
            if self.get_page_nos() > 1:
                self.drawing_models.pop(0)
                self.drawing_views.pop(0)
                page = self.drawing_notebook.get_nth_page(0)
                self.drawing_notebook.detach_tab(page)
        # Clear first page model
        blank_model = DrawingModel(self, self.program_state).get_model()
        self.drawing_models[0].set_model(blank_model)
        self.clear_status()
        self.clear_results()
        self.tab_handler_id = self.drawing_notebook.connect("switch-page", self.on_switch_tab)
        log.info('ProjectModel - clear_all - cleared all models')
        
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
            self.page_no = slno
                
    def mark_page(self, slno):
        page = self.drawing_notebook.get_nth_page(slno)
        sheet_name = self.drawing_models[slno].fields['name']['value']
        label = self.drawing_notebook.get_tab_label(page).get_children()[0]
        label.set_markup('<span foreground="red"><b>{}</b></span>'.format(sheet_name))
        label.set_use_markup(True)
    
    def update_tabs(self, slno=None):
    
        def set_label(page, sheet_name):                
            label_hbox = Gtk.Box()
            page_label = Gtk.Label(sheet_name)
            label_hbox.pack_start(page_label, True, True, 0)
            self.drawing_notebook.set_tab_label(page, label_hbox)
            label_hbox.show_all()
            
        if slno is not None:
            page = self.drawing_notebook.get_nth_page(slno)
            sheet_name = self.drawing_models[slno].fields['name']['value']
            self.drawing_models[slno].fields['sheet_no']['value'] = str(slno + 1)
            set_label(page, sheet_name)
        else:
            for slno in range(0, self.get_page_nos()):
                page = self.drawing_notebook.get_nth_page(slno)
                sheet_name = self.drawing_models[slno].fields['name']['value']
                self.drawing_models[slno].fields['sheet_no']['value'] = str(slno + 1)
                set_label(page, sheet_name)
                
    def update_title_blocks(self):
        for drawing_model in self.drawing_models:
            drawing_model.update_title_block()            
                
    def select_networkmodel(self, model, clear=True):
        if clear:
            self.de_select_all()
            self.update_tabs()
        if model:
            for code, elementids in model:
                if code == 'node':
                    for k1, drawing_model in enumerate(self.drawing_models):
                        for k2, element in enumerate(drawing_model.elements):
                            if (k1,k2) in self.networkmodel.gnode_element_mapping_inverted:
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
            self.drawing_view.refresh(redraw=True)
        log.info('ProjectModel - select_powermodel - select')

    def de_select_all(self):
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                element.set_selection(select=False)
        log.info('ProjectModel - de_select_all - deselected')
        
    def get_selected(self, codes=None):
        # Get selected elements from each sheet and consolidate
        selected_elements_comb = {}
        for drawing_model in self.drawing_models:
            selected_elements = drawing_model.get_selected(codes=codes, with_time_stamp=True)
            selected_elements_comb.update(selected_elements)
        # Sort elements by selection timestamp
        if selected_elements_comb:
            sorted_keys = sorted(list(selected_elements_comb.keys()))
            selected_elements_list = [selected_elements_comb[i] for i in sorted_keys]
        else:
            selected_elements_list = []
        return selected_elements_list

    def get_selected_codes(self, codes=None):
        # Get selected elements from each sheet and consolidate
        selected_elements_comb = {}
        for page, drawing_model in enumerate(self.drawing_models):
            selected_elements = drawing_model.get_selected_codes(codes=codes, with_time_stamp=True, page=page)
            selected_elements_comb.update(selected_elements)
        # Sort elements by selection timestamp
        if selected_elements_comb:
            sorted_keys = sorted(list(selected_elements_comb.keys()))
            selected_slnos = [selected_elements_comb[i] for i in sorted_keys]
        else:
            selected_slnos = []
        return selected_slnos
    
    ## Analysis functions
    
    def setup_base_model(self, build_ana_model=True, add_node_elements=True):
        self.clear_status()
        self.networkmodel = NetworkModel(self.program_state)
        # Setup base elements
        self.networkmodel.setup_base_elements()
        if build_ana_model:
            # Setup node variables
            self.networkmodel.setup_global_nodes()
            # Build graph model
            self.networkmodel.build_graph_model()
            self.status['net_model'] = True
            log.info('ProjectModel - setup_base_model - model generated')
            # Build and add node elements
            if add_node_elements:
                node_elements = self.networkmodel.setup_node_elements()
                self.clear_results(clear_elements=False)
                with group(self, "Add node elements"):
                    for (k1, gnode), node_element in node_elements.items():
                        drawing_model = self.drawing_models[k1]
                        drawing_model.insert_element_at_index(node_element)
                    self.status['node_elements'] = True
                    log.info('ProjectModel - setup_base_model - node elements added')
        
    def build_power_model(self, which='all'):
        if self.status['net_model']:
            sim_settings = self.get_project_fields(page='Simulation')
            f_hz = sim_settings['grid_frequency']
            self.powermodel = PandaPowerModel(self.networkmodel, self.loadprofiles, f_hz)
            
            if which in ('all', 'lf'):
                self.powermodel.build_power_model(mode=misc.POWER_MODEL_LINEFAULT)
            if which in ('all', 'gf'):
                self.powermodel.build_power_model(mode=misc.POWER_MODEL_GROUNDFAULT)
            if which in ('all', 'powerflow'):
                self.powermodel.build_power_model(mode=misc.POWER_MODEL_POWERFLOW)
                
            if which in ('all', 'lf', 'gf', 'powerflow'):
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
        
    def run_powerflow(self, pf_type):
        """Run power flow"""
        if self.status['power_model']:
            sim_settings = self.get_project_fields(page='Simulation')
            if sim_settings['power_flow_3ph']['value']:
                self.powermodel.run_powerflow(pf_type, runpp_3ph=True)
                log.info('ProjectModel - run_powerflow (3ph) - calculation run')
            else:
                self.powermodel.run_powerflow(pf_type, runpp_3ph=False)
                log.info('ProjectModel - run_powerflow - calculation run')
            self.status['power_analysis'] = True
        else:
            raise RuntimeError('ProjectModel - run_powerflow - Power model not built')
    
    def run_powerflow_timeseries(self):
        """Run power flow"""
        if self.status['power_model']:
            sim_settings = self.get_project_fields(page='Simulation')
            if sim_settings['power_flow_3ph']['value']:
                self.powermodel.run_powerflow_timeseries(runpp_3ph=True)
                log.info('ProjectModel - run_powerflow_timeseries (3ph) - calculation run')
            else:
                self.powermodel.run_powerflow_timeseries(runpp_3ph=False)
                log.info('ProjectModel - run_powerflow_timeseries - calculation run')
            self.status['power_analysis'] = True
        else:
            raise RuntimeError('ProjectModel - run_powerflow_timeseries - Power model not built')
    
    def run_sym_sccalc(self):
        """Run symmetric short circuit calculation"""
        if self.status['power_model']:
            sim_settings = self.get_project_fields(page='Simulation')
            self.powermodel.run_sym_sccalc(lv_tol_percent=sim_settings['lv_tol_percent']['value'], 
                                           r_fault_ohm=sim_settings['r_fault_ohm']['value'], 
                                           x_fault_ohm=sim_settings['x_fault_ohm']['value'],
                                           show_impedances=sim_settings['show_impedances']['value'])
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
                                                    x_fault_ohm=sim_settings['x_fault_ohm']['value'],
                                                    show_impedances=sim_settings['show_impedances']['value'])
            self.status['power_analysis'] = True
            log.info('ProjectModel - run_linetoground_sccalc - calculation run')
        else:
            raise RuntimeError('ProjectModel - run_linetoground_sccalc - Power model not built')

    def run_rulescheck(self):
        """Run electrical rules check and report errors in diagnostic view"""
        log.info('ProjectModel - run_rulescheck - running rulescheck...')
        settings = self.get_project_fields(full=True)
        sim_settings = settings['Simulation']
        rules_settings = settings['Rules Check']
        diagnostic_results = electrical_rules_check(self.networkmodel, sim_settings, rules_settings)
        self.diagnostics_view.update(diagnostic_results, self.select_networkmodel)
        log.info('ProjectModel - run_rulescheck - rulescheck run')
        
    def update_results(self, update_node_elements=True):
        """ Update analysis results"""

        if self.status['power_model']:
            # Update element results
            self.powermodel.update_results()
            # Add new node elements
            if update_node_elements and self.status['node_elements']:
                for (k1, gnode), node_element in self.networkmodel.node_elements.items():
                    if gnode in self.powermodel.node_results:
                        node_element.res_fields = copy.deepcopy(self.powermodel.node_results[gnode])
            self.status['power_results'] = True
            log.info('ProjectModel - update_results - results updated')
            self.drawing_view.refresh()
        else:
            log.info('ProjectModel - update_results - no results to update')

    def clear_results(self, clear_elements=True):
        """ Clear analysis results"""
        with group(self, "Clear analysis results"):
            for drawing_model in self.drawing_models:
                drawing_model.clear_results(clear_elements)
        
    ## Model functions
    
    @undoable
    def renumber_elements(self, mode):
        """Renumber drawing elements"""
        
        # Setup network model
        self.setup_base_model(build_ana_model=False)
        base_elements = self.networkmodel.get_elements_sorted_loc()  # Get sorted element dict
        
        # Setup local variables
        refs = misc.ReferenceCounter(1)  # Counter for base references
        prefix_codes = dict()  # Prefix codes for elements for assembly references
        changed = []  # Undo tracking of changed elements
        base_ref = dict()  # Base references dictionary
        for code, model in self.program_state['element_models'].items():
            if code not in misc.NON_ELEMENT_CODES:
                base_ref[code] = model(project_settings=self.get_project_fields(full=True)).fields['ref']['value'].strip('?')
        base_ref['element_assembly'] = 'A'
        
        # Get selected elements
        if mode == "Selected elements only":
            selected_elements = self.get_selected()
            selected_keys = self.get_selected_codes()
        
        # Update largest refs for assembly elements
        if mode in ("New elements only", "Selected elements only"):
            for key, model in base_elements.items():
                code = model.code
                if code == 'element_assembly':
                    code_ref = base_ref[code]
                    ref = model.fields['ref']['value']
                    try:
                        count = int(ref.lstrip(code_ref))
                        refs[code_ref] = max(refs[code_ref], count+1)
                    except:
                        pass
                    
        # Number assembly elements
        if mode == "All":
            for key, model in base_elements.items():
                code = model.code
                if code == 'element_assembly':
                    code_ref = base_ref[code]
                    ref = model.fields['ref']['value']
                    new_ref = code_ref + str(refs[code_ref])
                    refs[code_ref] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        elif mode == "New elements only":
            for key, model in base_elements.items():
                code = model.code
                if code == 'element_assembly':
                    code_ref = base_ref[code]
                    ref = model.fields['ref']['value']
                    if ref.strip('?') == code_ref:
                        new_ref = code_ref + str(refs[code_ref])
                        refs[code_ref] += 1
                        base_elements[key].set_text_field_value('ref', new_ref)
                        changed.append([key, ref])
        elif mode == "Selected elements only":
            for key, model in zip(selected_keys, selected_elements):
                code = model.code
                if code == 'element_assembly':
                    code_ref = base_ref[code]
                    ref = model.fields['ref']['value']
                    new_ref = code_ref + str(refs[code_ref])
                    refs[code_ref] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        
        # Update prefix for elements inside assembly
        for key, model in base_elements.items():
            code = model.code
            if code == 'element_assembly':
                code_ref = base_ref[code]
                children = model.get_children()
                for drg_no, element_index in children:
                    prefix_codes[(drg_no, element_index)] = model.fields['ref']['value'] + '-'
        
        # Update largest refs for elements
        if mode in ("New elements only", "Selected elements only"):
            for key, model in base_elements.items():
                code = model.code
                if code not in misc.NON_ELEMENT_CODES:
                    code_ref = base_ref[code]
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    try:
                        # Add prefixed base to base_ref
                        if prefix + code not in base_ref:
                            base_ref[prefix + code] = prefix + code_ref
                        prefix_code_ref = base_ref[prefix + code]
                        count = int(ref.lstrip(prefix_code_ref))
                        refs[prefix_code_ref] = max(refs[prefix_code_ref], count+1)
                    except:
                        pass
        
        # Number remaining elements
        if mode == "All":
            for key, model in base_elements.items():
                code = model.code
                if code not in misc.NON_ELEMENT_CODES:
                    code_ref = base_ref[code]
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                        base_ref[prefix + code] = prefix + code_ref
                    else:
                        prefix = ''
                    prefix_code_ref = base_ref[prefix + code]
                    ref = model.fields['ref']['value']
                    new_ref = prefix + code_ref + str(refs[prefix_code_ref])
                    refs[prefix_code_ref] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        elif mode == "New elements only":
            # Modify references
            for key, model in base_elements.items():
                code = model.code
                if code not in misc.NON_ELEMENT_CODES:
                    code_ref = base_ref[code]
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    if ref.strip('?') == code_ref:
                        prefix_code_ref = base_ref[prefix + code]
                        new_ref = prefix + code_ref + str(refs[prefix_code_ref])
                        refs[prefix_code_ref] += 1
                        base_elements[key].set_text_field_value('ref', new_ref)
                        changed.append([key, ref])
        elif mode == "Selected elements only":
            for key, model in zip(selected_keys, selected_elements):
                code = model.code
                if code not in misc.NON_ELEMENT_CODES:
                    code_ref = base_ref[code]
                    if key in prefix_codes:
                        prefix = prefix_codes[key]
                    else:
                        prefix = ''
                    ref = model.fields['ref']['value']
                    prefix_code_ref = base_ref[prefix + code]
                    new_ref = prefix + code_ref + str(refs[prefix_code_ref])
                    refs[prefix_code_ref] += 1
                    base_elements[key].set_text_field_value('ref', new_ref)
                    changed.append([key, ref])
        self.drawing_view.refresh()
        yield "Renumber Elements - " + mode
        # Undo action
        for key, ref in changed:
            base_elements[key].set_text_field_value('ref', ref)

    def reg_refs_sheets(self):
        mapping = {}  # Maps 'CRX' -> [(sheetno, element), ... ]
        mapping_sheetnos = {}  # Maps 'CRX' -> [sheetno1, ... ]
        # Populate mapping
        for drawing_model in self.drawing_models:
            sheetno = drawing_model.fields['sheet_no']['value']
            slnos = drawing_model.get_element_codes(codes=misc.REFERENCE_CODES)
            for slno in slnos:
                element = drawing_model.elements[slno]
                ref = element.fields['ref']['value']
                if ref not in ('', '?', 'CR?'):
                    # Update mapping
                    if ref in mapping:
                        mapping[ref].append((sheetno, element))
                    else:
                        mapping[ref] = [(sheetno, element)]
                    # Update mapping_sheetnos
                    if ref in mapping_sheetnos:
                        mapping_sheetnos[ref].append(sheetno)
                    else:
                        mapping_sheetnos[ref] = [sheetno]
        # Update sheet refs
        for ref, item_list in mapping.items():
            for (sheetno, element) in item_list:
                sheetnos = mapping_sheetnos[ref][:]
                sheetnos.remove(sheetno)
                sheetnos = set(sheetnos)
                if sheetnos:
                    refstr = ','.join(sheetnos)
                    element.fields['sheet']['value'] = refstr
            
    def get_reference_code(self):
        """Get unique reference code"""
        # Setup network model
        self.setup_base_model(build_ana_model=False)
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
    
    def link_references(self, base_ref, selected_dict, copy_titles=False):
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
                        if copy_titles:
                            element.fields['title']['value'] = title
                            element.fields['sub_title']['value'] = subtitle
                        self.drawing_models[page].update_element_at_index(element ,el_no)
            selected_element.fields['ref']['value'] = reference
            selected_sheets.remove(sheet)
            selected_element.fields['sheet']['value'] =  ','.join(selected_sheets)
            self.drawing_models[selected_page].update_element_at_index(selected_element ,selected_slno)
    
    ## Export/Import functions
    
    def export_html_report(self, filename, call_at_exit=None):
        self.powermodel.export_html_report(filename)
        if call_at_exit:
            call_at_exit()

    def export_element_graph(self, filename, call_at_exit=None):
        self.networkmodel.export_element_graph_html(filename)
        if call_at_exit:
            call_at_exit()
        
    def export_json(self, filename, call_at_exit=None):
        self.powermodel.export_json(filename)
        if call_at_exit:
            call_at_exit()
        
    def export_pdf_report(self, foldername, settings, call_at_exit=None):
        template_path = misc.abs_path("templates")
        env = Environment(loader=FileSystemLoader(template_path))
        
        # General variables
        project_settings = self.get_project_fields()
        report_settings = self.get_project_fields(page='Reports')
        export_graphs_flag = report_settings['export_graphs']['value']
        export_elements_flag = report_settings['export_elements']['value']
        export_boq_flag = report_settings['export_boq']['value']
        export_loadprofiles_flag = report_settings['export_loadprofiles']['value']
        export_ana_flag = report_settings['export_analysis']['value']
        gen_variables = {'program_version'        : 'v' + misc.PROGRAM_VER,
                         'project_name'           : project_settings['project_name']['value'],
                         'drawing_field_approved' : project_settings['drawing_field_approved']['value'],
                         'drawing_field_dept'     : project_settings['drawing_field_dept']['value'],
                         'drawing_field_address'  : project_settings['drawing_field_address']['value'].replace('\n','</br>'),
                         'doc_title': project_settings['project_name']['value'],
                         'doc_author': project_settings['drawing_field_approved']['value'],
                         'doc_subject': "Project Report",
                         'doc_lang': project_settings['drawing_field_lang']['value'],
                         'doc_creator':misc.PROGRAM_NAME + ' v' + misc.PROGRAM_VER,
                         'doc_create_date': datetime.datetime.now().astimezone().replace(microsecond=0).isoformat(),
                         'doc_mod_date': datetime.datetime.now().astimezone().replace(microsecond=0).isoformat()}
        
        # Elements
        element_captions = dict()
        element_refs = dict()
        element_tables = dict()
        element_lines = []
        element_loads = []
        element_switches = []
        element_nodes = dict()
        loadprofile_captions_used = set()
        self.networkmodel.setup_base_elements()
        base_elements = self.networkmodel.base_elements
        # First pass add all required elements
        for key, model in base_elements.items():
            if 'ref' in model.fields and model.code not in misc.NON_ELEMENT_CODES:
                element_captions[key] = model.fields['ref']['value'] + ' - ' + model.name
                element_refs[key] = model.fields['ref']['value']
                if export_elements_flag:
                    element_tables[key] = misc.fields_to_table(model.fields, insert_graph=export_graphs_flag)
            # Lines
            if model.code in misc.LINE_ELEMENT_CODES:
                element_lines.append(model)
            # Loads
            if model.code in misc.LOAD_ELEMENT_CODES:
                element_loads.append(model)
            # Switches
            if model.code in misc.SWITCH_ELEMENT_CODES:
                element_switches.append(model)
            # Nodes
            if model.code in misc.DISPLAY_ELEMENT_CODES:
                element_nodes[int(model.fields['ref']['value'])] = model
            # Loads
            if model.code in misc.LOADPROFILE_CODES and model.fields['load_profile']['value'] in self.loadprofiles:
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
                if export_elements_flag:
                    element_tables[key] = misc.fields_to_table(assembly_fields, insert_graph=export_graphs_flag)
        # Sort by reference
        element_captions = dict(sorted(element_captions.items(), key=lambda item:item[1]))
        if export_elements_flag:
            element_tables = {key:element_tables[key] for key in element_captions}
                                 
        # BOQ
        boq_tables = dict()
        boq_captions = dict()
        E = misc.ELEMENT_FIELD
        R = misc.ELEMENT_RESULT
        P = misc.ELEMENT_PLACEHOLDER
        if export_boq_flag:
            # Lines
            if element_lines:
                col_codes = ['ref', 'name', 'designation', 'type', 'parallel', 'length_km', 'max_i_ka', 'df', 'in_service', 'loading_percent_max', 'pl_mw_max', 'pl_perc_max']
                col_captions = ['Reference', 'Name', 'Designation', 'Type', '# Parallel Lines',  'Length', 'Imax', 'Derating Factor', 'In Service ?', '% Loading', 'P loss', '% P loss']
                code_sources = [E,E,E,E,E,E,E,E,E,R,R,R]
                table = misc.elements_to_table(element_lines, col_codes, col_captions, code_sources, 'boq_lines',
                                            show_element_class=True, sum_cols=[10])
                boq_tables['boq_lines'] = table
                boq_captions['boq_lines'] = 'Lines'
            # Loads
            if element_loads:

                def modifyfunc_load(table):
                    table['Rated power'][0] = 'kVA'
                    table['Sa'][0] = 'kVA'
                    table['Sb'][0] = 'kVA'
                    table['Sc'][0] = 'kVA'
                    for slno, element in enumerate(element_loads):
                        scaling = element.fields['scaling']['value']
                        if element.code in ('element_load','element_async_motor_3ph'):
                            s_kva = round(element.fields['sn_kva']['value']*scaling, 4)
                            pf = str(round(element.fields['cos_phi']['value'], 2)) + (' lag' if element.fields['mode']['value'] else ' lead')
                        else:
                            fields = element.get_power_model('')[0][2]
                            p_a_kw = round(fields['p_a_mw']*1000*scaling, 4)
                            p_b_kw = round(fields['p_b_mw']*1000*scaling, 4)
                            p_c_kw = round(fields['p_c_mw']*1000*scaling, 4)
                            q_a_kvar = round(fields['q_a_mvar']*1000*scaling, 4)
                            q_b_kvar = round(fields['q_b_mvar']*1000*scaling, 4)
                            q_c_kvar = round(fields['q_c_mvar']*1000*scaling, 4)
                            p_kw = p_a_kw + p_b_kw + p_c_kw
                            q_kvar = q_a_kvar + q_b_kvar + q_c_kvar
                            table['Sa'][slno+1] = str(p_a_kw) + '+j' + str(q_a_kvar)
                            table['Sb'][slno+1] = str(p_b_kw) + '+j' + str(q_b_kvar)
                            table['Sc'][slno+1] = str(p_c_kw) + '+j' + str(q_c_kvar)
                            s_kva = round(math.sqrt(p_kw**2 + q_kvar**2), 4)
                            pf = str(round((p_kw/s_kva),2)) + (' lag' if q_kvar > 0 else ' lead')
                        table['Rated power'][slno+1] = str(s_kva)
                        table['PF'][slno+1] = pf
                        
                col_codes = ['ref', 'name', 'sn_kva', 'cos_phi', 'sa', 'sb', 'sc', 'in_service', 'load_profile']
                col_captions = ['Reference', 'Name', 'Rated power', 'PF', 'Sa', 'Sb', 'Sc', 'In Service ?', 'Load Profile']
                code_sources = [E,E,P,P,P,P,P,E,E]
                table = misc.elements_to_table(element_loads, col_codes, col_captions, code_sources, 'boq_loads',
                                            show_element_class=True, modifyfunc=modifyfunc_load, sum_cols=[2])
                boq_tables['element_loads'] = table
                boq_captions['element_loads'] = 'Loads'
            # Switches
            if element_switches:

                def modifyfunc_switch(table):
                    for slno, element in enumerate(element_switches):
                        if table['Line protection curve'][slno+1] == 'None':
                            table['Line protection curve'][slno+1] = ''
                        if table['Ground protection curve'][slno+1] == 'None':
                            table['Ground protection curve'][slno+1] = ''

                col_codes = ['ref', 'name', 'type', 'subtype', 'poles', 'Un', 'In', 
                            'prot_curve_type', 'prot_0_curve_type', 'closed']
                col_captions = ['Reference', 'Name', 'Type', 'Sub type', 'Poles', 'Un', 'In',
                                'Line protection curve', 'Ground protection curve', 'Closed']
                code_sources = [E,E,E,E,E,E,E,E,E,E]
                table = misc.elements_to_table(element_switches, col_codes, col_captions, code_sources, 'boq_switches',
                                            show_element_class=False, modifyfunc=modifyfunc_switch)
                boq_tables['element_switches'] = table
                boq_captions['element_switches'] = 'Switches'
            # Nodes
            if element_nodes:
                nodes_sorted_by_name = [element_nodes[x] for x in sorted(element_nodes.keys())]
                col_codes = ['ref', 'vn_kv', 'delv_perc_max', 'ikss_ka_3ph_max', 'ikss_ka_3ph_min', 'ipss_ka_3ph_max', 'ikss_ka_1ph_max', 'ikss_ka_1ph_min']
                col_captions = ['Node ID', 'Vn', 'ΔV', 'Isc (sym, max)', 'Isc (sym, min)', 'Isc (pk, max)', 'Isc (L-G, max)', 'Isc (L-G, min)']
                code_sources = [E,R,R,R,R,R,R,R]
                table = misc.elements_to_table(nodes_sorted_by_name, col_codes, col_captions, code_sources, 'boq_nodes',
                                            show_slno=False, show_element_class=False)
                boq_tables['element_nodes'] = table
                boq_captions['element_nodes'] = 'Nodes'
            
        # Load profiles
        loadprofile_captions = dict()
        loadprofile_images = dict()
        if export_loadprofiles_flag:
            loadprofile_captions = {key:self.loadprofiles[key][0] for key in loadprofile_captions_used}
            # Sort
            loadprofile_captions = dict(sorted(loadprofile_captions.items(), key=lambda item:item[1]))
            # Add images
            xlim = misc.GRAPH_LOAD_TIME_LIMITS
            ylim = misc.GRAPH_LOAD_CURRENT_LIMITS
            xlabel = 'Time (Hr)'
            ylabel = 'Diversity Factor'
            params = {}
            for loadprofile_caption in loadprofile_captions:
                title, graph_model = self.loadprofiles[loadprofile_caption]
                graph_image = GraphImage(xlim, ylim, '', xlabel, ylabel, graph_params=params)
                graph_image.add_plots(graph_model)
                emb_image = graph_image.get_embedded_html_image(figsize=(500, 175))
                loadprofile_images[loadprofile_caption] = emb_image
            
        # Analysis options
        if (settings['powerflow'] or settings['sc_sym'] or settings['sc_gf']) and export_ana_flag:
            analysis_flag = True
        else: 
            analysis_flag = False
        ana_opt_table = misc.fields_to_table(self.get_project_fields(page='Simulation'))
        
        # Analysis results
        ana_res_captions = dict()
        ana_res_tables = dict()
        if analysis_flag: 
            base_elements = self.networkmodel.base_elements
            # First pass add all required elements
            for key, model in base_elements.items():
                if 'ref' in model.fields and (model.code not in misc.REFERENCE_CODES) and (model.code != 'element_assembly'):
                    if model.res_fields:
                        table = misc.fields_to_table(model.res_fields, insert_graph=export_graphs_flag)
                        ana_res_captions[str(key)+'_res'] = model.fields['ref']['value'] + ' - ' + model.name
                        ana_res_tables[str(key)+'_res'] = table
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
                         'export_elements_flag': export_elements_flag,
                         'export_boq_flag': export_boq_flag,
                         'export_loadprofiles_flag': export_loadprofiles_flag,
                         'ana_opt_table': ana_opt_table,
                         'ana_res_tables': ana_res_tables,
                         'ana_res_captions': ana_res_captions
                        }
        html_out = template.render(template_vars)
        
        # Load CSS file
        template_css = env.get_template("report.css")
        template_vars_css = {'report_font': misc.REPORT_FONT_FACE,
                             'report_font_size': misc.REPORT_FONT_SIZE}
        css_out = template_css.render(template_vars_css)
        css_obj = io.BytesIO(bytes(css_out, 'utf-8'))
        
        # Render HTML, PDF
        filename_pdf = misc.posix_path(foldername, 'report.pdf')
        filename_html = misc.posix_path(foldername, 'report.html')
        filename_css = misc.posix_path(foldername, 'report.css')
        with open(filename_html, 'w') as fp:
            fp.write(html_out)
        with open(filename_css, 'w') as fp:
            fp.write(css_out)
        HTML(string=html_out).write_pdf(filename_pdf, stylesheets=[css_obj])
        
        if call_at_exit:
            call_at_exit()
        
    def export_drawing(self, filename, call_at_exit=None):
        surface = cairo.PDFSurface(filename, 0, 0)
        proj_fields = self.get_project_fields()
        surface.set_metadata(cairo.PDFMetadata.TITLE, proj_fields['project_name']['value'])
        surface.set_metadata(cairo.PDFMetadata.AUTHOR, proj_fields['drawing_field_approved']['value'])
        surface.set_metadata(cairo.PDFMetadata.SUBJECT, 'Electrical Schematic Drawing')
        surface.set_metadata(cairo.PDFMetadata.CREATOR, misc.PROGRAM_NAME + ' v' + misc.PROGRAM_VER)
        surface.set_metadata(cairo.PDFMetadata.CREATE_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        surface.set_metadata(cairo.PDFMetadata.MOD_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        context = cairo.Context(surface)
        # If dark mode, load correct values while drawing
        if self.program_state['dark_mode']:
            misc.reset_dark_mode_drawing_values()
        for drawing_model in self.drawing_models:
            surface.set_size(drawing_model.fields['page_width']['value'], drawing_model.fields['page_height']['value'])
            drawing_model.export_drawing(context)
            surface.show_page()
        # If dark mode, restore original values
        if self.program_state['dark_mode']:
            misc.set_dark_mode_drawing_values()  
        surface.finish()
        if call_at_exit:
            call_at_exit()
        
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
        self.drawing_notebook.disconnect(self.tab_handler_id)
        if ('proj_drawing_names' in document and 
            'proj_fields' in document and 
            'proj_loadprofiles.json' in pages):
            self.fields = misc.update_fields_dict(self.fields, document['proj_fields'])
            self.program_state['project_settings_main'] = self.fields['Information']
            self.program_state['project_settings'] = self.fields
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
        self.update_tabs()
        self.set_page(0)
        self.tab_handler_id = self.drawing_notebook.connect("switch-page", self.on_switch_tab)
        
    ## Callbacks
    
    def on_switch_tab(self, notebook, page, pagenum):
        """Refresh display on switching between views"""
        log.info('ProjectModel - on_switch_tab called - ' + str(pagenum))
        self.drawing_view.save_scroll_position()
        self.set_page(pagenum, switch_tab=False)
        GLib.idle_add(self.drawing_view.restore_scroll_position)
        self.program_state['zoom_display_label'].set_label(str(int(self.drawing_view.scale*100)) + '%')

    def on_page_reordered(self, notebook, page, pagenum):
        prev_pagenum = self.page_no
        self.reorder_tab(prev_pagenum, pagenum)
        log.info('ProjectModel - on_page_reordered called - from {} to {}'.format(prev_pagenum, pagenum))