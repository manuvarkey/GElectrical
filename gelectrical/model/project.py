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

import logging, copy, datetime

# local files import
from .. import undo
from ..core import constants, style
from ..core.fields import ReferenceCounter, new_project_settings, get_fields_dict_trunc, update_fields_dict
from ..core.undoable import group, undoable
from ..elementmodel import registry
from .drawing import DrawingModel
from .networkmodel import NetworkModel
from .pandapower import PandaPowerModel
from .rulescheck import electrical_rules_check

# Get logger object
log = logging.getLogger(__name__)


class ProjectModel:
    """Project document: drawing sheets, project fields, load profiles and
    analysis state. Headless (M2 step 6): no views and no dialogs.

    User interfaces observe the model with :meth:`subscribe`. Events
    (``callback(event, **data)``):

    * ``page_added`` (slno, model), ``page_removed`` (slno), ``page_moved``
      (from_slno, to_slno), ``page_selected`` (slno, switch_tab),
      ``page_marked`` (slno), ``pages_cleared``
    * ``tabs_changed`` (slno: one sheet or None for all)
    * ``fields_changed`` (fields): project fields replaced
    * ``diagnostics`` (results, select_callback): diagnostic or rules-check
      messages
    * ``refresh`` (redraw): element data changed, redraw the current sheet

    Arguments:
        stack: undo stack (a new ``undo.Stack`` when not given)
        program_settings: 'Defaults' page of the program settings, copied into
            the Information fields of a new project
        element_models: ``code -> class`` map (the element registry by default)
        listeners: callbacks subscribed before the first sheet is added
    """
    
    def __init__(self, stack=None, program_settings=None, element_models=None, listeners=None):
        # Data
        self.drawing_models = []
        self.fields = new_project_settings()  # Own copy of the defaults (D4)
        if program_settings:
            for code in ('drawing_field_dept', 'drawing_field_techref', 'drawing_field_created',
                         'drawing_field_approved', 'drawing_field_lang', 'drawing_field_address'):
                self.fields['Information'][code]['value'] = copy.deepcopy(program_settings[code]['value'])
        self.loadprofiles = constants.default_load_profile()  # Own copy (D4)
        self.element_models = element_models if element_models is not None else registry.get_element_models()
        
        # State variables
        self.listeners = list(listeners) if listeners else []
        self.program_settings = program_settings
        self.drawing_model = None
        self.stack = stack if stack is not None else undo.Stack()
        self.page_no = 0
        # Analysis varables
        self.status = {}
        self.clear_status()
        self.networkmodel = None
        self.powermodel = None
        # Initialise tab
        self.add_page_vanilla()

    ## Notifications

    def subscribe(self, callback):
        """Call ``callback(event, **data)`` on model events"""
        self.listeners.append(callback)

    def unsubscribe(self, callback):
        if callback in self.listeners:
            self.listeners.remove(callback)

    def notify(self, event, **data):
        for callback in list(self.listeners):
            callback(event, **data)

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
        self.notify('fields_changed', fields=self.fields)
        
        self.update_tabs()
        self.update_title_blocks()
        
        yield "Update project settings"
        # Undo action
        self.update_project_fields(old_fields)
        
    def prepare_protection_coordination(self):
        """Selected protection/damage elements with up-to-date voltages for
        the protection coordination view; empty list if none selected"""
        selected_elements = self.get_selected(codes=constants.PROTECTION_ELEMENT_CODES + constants.DAMAGE_ELEMENT_CODES + ('element_display_node',))
        if selected_elements:
            # Populate voltage levels for breakers
            if self.status['power_results'] == False or self.stack.haschanged():
                self.setup_base_model(add_node_elements=False)  # Do not generate node elements
                self.build_power_model(which='powerflow')  # Build element voltages
                self.update_results(update_node_elements=False)  # Update element voltages. Do not overwrite node results.
        return selected_elements
        
    @undoable
    def modify_loadprofiles(self, loadprofiles):
        loadprofiles_old = copy.deepcopy(self.loadprofiles)
        self.loadprofiles = loadprofiles

        yield "Update load profiles"
        # Undo action
        self.loadprofiles = loadprofiles_old
    
    def append_page(self, copy_selected_sheet=False):
        model = DrawingModel(self)
        slno = self.get_page_nos()
        cur_slno = self.page_no
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
            self.drawing_model = DrawingModel(self)
            sheet_name = "Sheet " + str(self.get_page_nos() + 1)
            self.drawing_model.set_sheet_name(sheet_name)
            self.drawing_model.fields['date_of_issue']['value'] = datetime.datetime.today().strftime('%Y-%m-%d')
            
        if slno:
            # Setup model
            self.drawing_models.insert(slno, self.drawing_model)
            add_slno = slno
        else:
            # Setup model
            self.drawing_models.append(self.drawing_model)
            add_slno = self.get_page_nos() -1
        self.notify('page_added', slno=add_slno, model=self.drawing_model)
        self.set_page(add_slno)  # Switch to added page
        return add_slno
        
    @undoable
    def remove_page(self, slno):
        delete_slno = None
        if self.get_page_nos() > 1 and slno < self.get_page_nos():
            del_model = self.drawing_models.pop(slno)
            self.notify('page_removed', slno=slno)
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
            self.drawing_models.insert(pagenum, model)
            self.notify('page_moved', from_slno=prev_pagenum, to_slno=pagenum)
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
        for slno in range(0,self.get_page_nos()):
            if self.get_page_nos() > 1:
                self.drawing_models.pop(0)
                self.notify('page_removed', slno=0)
        # Clear first page model
        blank_model = DrawingModel(self).get_model()
        self.drawing_models[0].set_model(blank_model)
        self.clear_status()
        self.clear_results()
        log.info('ProjectModel - clear_all - cleared all models')
        
    def get_page_nos(self):
        return len(self.drawing_models)
        
    def set_page(self, slno, switch_tab=True):
        """Select the current sheet"""
        if slno < self.get_page_nos():
            self.drawing_model = self.drawing_models[slno]
            self.notify('page_selected', slno=slno, switch_tab=switch_tab)
            self.update_tabs(slno)
            self.page_no = slno
                
    def mark_page(self, slno):
        """Highlight a sheet (selection of diagnostic messages)"""
        self.notify('page_marked', slno=slno)
    
    def update_tabs(self, slno=None):
        """Update sheet numbers from the sheet order"""
        if slno is not None:
            self.drawing_models[slno].fields['sheet_no']['value'] = str(slno + 1)
        else:
            for slno_ in range(0, self.get_page_nos()):
                self.drawing_models[slno_].fields['sheet_no']['value'] = str(slno_ + 1)
        self.notify('tabs_changed', slno=slno)
                
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
                                        element.set_selection(select=True, color=style.COLOR_SELECTED_WARNING)
                                        self.mark_page(k1)
                else:
                    for k1,k2 in elementids:
                        element = self.drawing_models[k1][k2]
                        element.set_selection(select=True, color=style.COLOR_SELECTED_WARNING)
                        self.mark_page(k1)
            self.notify('refresh', redraw=True)
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
        self.networkmodel = NetworkModel(self)
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
            f_hz = sim_settings['grid_frequency']['value']
            self.powermodel = PandaPowerModel(self.networkmodel, self.loadprofiles, f_hz)
            
            if which in ('all', 'lf'):
                self.powermodel.build_power_model(mode=constants.POWER_MODEL_LINEFAULT)
            if which in ('all', 'gf'):
                self.powermodel.build_power_model(mode=constants.POWER_MODEL_GROUNDFAULT)
            if which in ('all', 'powerflow'):
                self.powermodel.build_power_model(mode=constants.POWER_MODEL_POWERFLOW)
                
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
            self.notify('diagnostics', results=diagnostic_results, select_callback=self.select_networkmodel)
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
        self.notify('diagnostics', results=diagnostic_results, select_callback=self.select_networkmodel)
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
            self.notify('refresh', redraw=False)
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
        refs = ReferenceCounter(1)  # Counter for base references
        prefix_codes = dict()  # Prefix codes for elements for assembly references
        changed = []  # Undo tracking of changed elements
        base_ref = dict()  # Base references dictionary
        for code, model in self.element_models.items():
            if code not in constants.NON_ELEMENT_CODES:
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
                if code not in constants.NON_ELEMENT_CODES:
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
                if code not in constants.NON_ELEMENT_CODES:
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
                if code not in constants.NON_ELEMENT_CODES:
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
                if code not in constants.NON_ELEMENT_CODES:
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
        self.notify('refresh', redraw=False)
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
            slnos = drawing_model.get_element_codes(codes=constants.REFERENCE_CODES)
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
            if code in constants.REFERENCE_CODES:
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
        from ..reports import export
        export.export_html_report(self, filename, call_at_exit)

    def export_element_graph(self, filename, call_at_exit=None):
        from ..reports import export
        export.export_element_graph(self, filename, call_at_exit)
        
    def export_json(self, filename, call_at_exit=None):
        from ..reports import export
        export.export_json(self, filename, call_at_exit)
        
    def export_pdf_report(self, foldername, settings, call_at_exit=None):
        from ..reports import export
        export.export_pdf_report(self, foldername, settings, call_at_exit)
        
    def export_drawing(self, filename, call_at_exit=None):
        from ..reports import export
        export.export_drawing(self, filename, call_at_exit)
        
    def print_drawing(self, context, page_nr):
        from ..reports import export
        export.print_drawing(self, context, page_nr)
        
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
                         'proj_fields'         : get_fields_dict_trunc(self.fields)}
        return [proj_settings, proj_pages]
            
    def set_model(self, document, pages):
        """Set storage model"""
        self.clear_all()
        if ('proj_drawing_names' in document and 
            'proj_fields' in document and 
            'proj_loadprofiles.json' in pages):
            self.fields = update_fields_dict(self.fields, document['proj_fields'])
            self.notify('fields_changed', fields=self.fields)
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
