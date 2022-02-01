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
from gi.repository import Gtk, Gdk
import cairo

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.plotting as pplot
import pandapower.control as control
import pandapower.networks as nw
import pandapower.timeseries as timeseries
from pandapower.timeseries import OutputWriter
from pandapower.timeseries.data_sources.frame_data import DFData
import networkx as nx
from networkx.algorithms.components.connected import connected_components

import matplotlib
matplotlib.use('GTK3Agg')  # configure matplotlib
import matplotlib.pyplot as plt

# local files import
from .. import misc
from ..misc import undoable, group
from .drawing import DrawingModel
from ..view.drawing import DrawingView
from ..view.graph import GraphViewDialog
from ..model.graph import GraphModel

# Get logger object
log = logging.getLogger(__name__)


class ProjectModel:
    """Class for modelling a project"""
    
    def __init__(self, window, drawing_notebook, properties_view, results_view, diagnostics_view, database_view, program_state, program_settings):
        # Data
        self.drawing_models = []
        self.fields = {'project_name':          misc.get_field_dict('str', 'Project Name', '', 'PROJECT', status_inactivate=False),
                       'drawing_field_dept':    program_settings['drawing_field_dept'],
                       'drawing_field_techref': program_settings['drawing_field_techref'],
                       'drawing_field_created': program_settings['drawing_field_created'],
                       'drawing_field_approved':program_settings['drawing_field_approved'],
                       'drawing_field_lang':    program_settings['drawing_field_lang'],
                       'drawing_field_address': program_settings['drawing_field_address']}
        self.loadprofiles = misc.DEFAULT_LOAD_PROFILE
        
        # State variables
        self.window = window
        self.drawing_notebook = drawing_notebook
        self.properties_view = properties_view
        self.results_view = results_view
        self.diagnostics_view = diagnostics_view
        self.database_view = database_view
        self.program_state = program_state
        self.program_settings = program_settings
        self.drawing_views = []
        self.drawing_model = None
        self.drawing_view = None
        self.stack = program_state['stack']
        # Base variables
        self.port_mapping = dict()  # Maps (p,x,y) -> global_node
        self.node_mapping = dict()  # Maps local_node -> global_node
        self.global_nodes = set()
        self.virtual_global_nodes = set()
        self.base_models = dict()
        # Graph variables
        self.graph = None
        # Power variables
        self.power_model = None
        self.power_nodes = dict()  # Maps global_node -> power_node
        self.power_nodes_inverted = dict()  # Maps power_node -> global_node
        self.power_elements = dict()  # Maps code -> power_element
        self.power_elements_inverted = dict()  # power_element -> Maps code
        # Results
        self.element_results = dict()
        self.node_results = dict()
        self.diagnostic_results = dict()
        
        # Initialise tab
        self.add_page_vanilla()
        self.drawing_notebook.connect("switch-page", self.on_switch_tab)
        
    ## Functions
    
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
        ylabel = 'DF'
        dialog = GraphViewDialog(self.window, self.loadprofiles, xlim, ylim, xlabel, ylabel)
        dialog.run()
    
    def append_page(self):
        model = DrawingModel(self, self.program_state, self.program_settings)
        slno = self.get_page_nos()
        # Except first page copy fields from first page
        if slno > 0:
            base_model = self.drawing_models[0].get_model()
            model.set_model(base_model, copy_elements=False)
        sheet_name = "Sheet " + str(self.get_page_nos())
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
            self.drawing_model = DrawingModel(self, self.program_state, self.program_settings)
            sheet_name = "Sheet " + str(self.get_page_nos())
            self.drawing_model.set_sheet_name(sheet_name)
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
        if self.get_page_nos() > 1 and slno and slno < self.get_page_nos():
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
        blank_model = DrawingModel(self, self.program_state, self.program_settings).get_model()
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
        label = self.drawing_notebook.get_tab_label(page)
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
                
    def select_powermodel(self, model):
        if model:
            for row in model:
                code, elementids = row
                if code == 'node':
                    for k1, drawing_model in enumerate(self.drawing_models):
                        selected_ports = []
                        for k2, element in enumerate(drawing_model.elements):
                            ports = element.get_ports_global()
                            for port in ports:
                                map_port = (k1, *port)
                                node = self.port_mapping[map_port]
                                if node in elementids:
                                    selected_ports.append(port)
                        self.drawing_models[k1].select_ports(selected_ports, color=misc.COLOR_SELECTED_WARNING)
                        self.mark_page(k1)
                else:
                    for elementid in elementids:
                        (k1,k2) = self.power_elements_inverted[code, elementid]
                        element = self.drawing_models[k1].elements[k2]
                        element.set_selection(select=True, color=misc.COLOR_SELECTED_WARNING)
                        self.mark_page(k1)
            self.drawing_view.refresh()
        log.info('ProjectModel - select_powermodel - select')
    
    ## Analysis functions
    
    def setup_base_model(self):
        self.port_mapping = dict()  # Maps (p,x,y) -> global_node
        self.node_mapping = dict()  # Maps local_node -> global_node
        self.global_nodes = set()
        self.virtual_global_nodes = set()
        self.base_models = dict()
        
        duplicate_ports_list = []
        cur_gnode_num = 0
        
        # Populate self.port_mapping, self.virtual_global_nodes
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str(k1) + ',' + str(k2)
                nodes = element.get_nodes(code)
                for (p0, ports) in nodes:
                    gnode = cur_gnode_num
                    duplicate_ports = set()
                    if ports:
                        for port in ports:
                            # Get port in global coordinates
                            if len(port) == 2:
                                map_port = (k1, *port)  # If same page port ref add page number
                            else:
                                map_port = port
                            # Populate data
                            self.port_mapping[map_port] = gnode
                            if len(ports) > 1:
                                duplicate_ports.add(map_port)
                        if len(ports) > 1:
                            duplicate_ports_list.append(duplicate_ports)
                    else:
                        self.virtual_global_nodes.add(gnode)
                    cur_gnode_num += 1
                    
        # Filter duplicates in self.port_mapping
        duplicate_ports_list_comb = self.combine_connected_nodes(duplicate_ports_list)
        for duplicate_ports in duplicate_ports_list_comb:
            gnode = cur_gnode_num
            for port in duplicate_ports:
                self.port_mapping[port] = gnode
            cur_gnode_num += 1
            
        # Populate self.node_mapping, self.global_nodes, self.base_models
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                self.base_models[(k1,k2)] = element.get_model()
                code = str(k1) + ',' + str(k2)
                nodes = element.get_nodes(code)
                # Add nodes
                for (p0, ports) in nodes:
                    port = ports[0]
                    # Get port in global coordinates
                    if len(port) == 2:
                        map_port = (k1, *port)  # If same page port ref add page number
                    else:
                        map_port = port
                    gnode = self.port_mapping[map_port]
                    self.global_nodes.add(gnode)
                    self.node_mapping[p0] = gnode
        
        log.info('ProjectModel - setup_analysis - model generated')
        
    def build_graph_model(self):
        self.graph = nx.MultiDiGraph()
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str(k1) + ',' + str(k2)
                sysdesign_model = element.get_sysdesign_model(code)
                for code, ports, model in sysdesign_model:
                    pass
        log.info('ProjectModel - build_graph - model generated')
        
    def build_power_model(self):
        self.power_model = pp.create_empty_network()
        self.power_nodes = dict()
        self.power_nodes_inverted = dict()
        self.power_elements = dict()
        self.power_elements_inverted = dict()
        self.element_results = dict()
        self.node_results = dict()
        self.diagnostic_results = dict()
        
        def get_node(local_node):
            if local_node in self.node_mapping:
                node = self.node_mapping[local_node]
                if node not in self.power_nodes:
                    bus = pp.create_bus(self.power_model, name=str(node), type='n', vn_kv=0.415)
                    self.power_nodes[node] = bus
                    self.power_nodes_inverted[bus] = node
                    return bus
                else:
                    return self.power_nodes[node]
                        
        # Create all elements
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str(k1) + ',' + str(k2)
                power_model = element.get_power_model(code)
                for slno, power_model_sub in enumerate(power_model):
                    elementcode, local_nodes, model = power_model_sub
                    if elementcode == 'bus':
                        node = get_node(local_nodes[0])
                        self.power_model.bus.name.at[node] = model['name']
                        self.power_model.bus.vn_kv.at[node] = model['vn_kv']
                        self.power_model.bus.type.at[node] = model['type']
                    elif elementcode == 'switch':
                        node0 = get_node(local_nodes[0])
                        node1 = get_node(local_nodes[1])
                        element = pp.create_switch(self.power_model, bus=node0, element=node1, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'ext_grid':
                        node = get_node(local_nodes[0])
                        element = pp.create_ext_grid(self.power_model, bus=node, **model)
                        self.power_model.ext_grid.at[element, 'x0x_max'] = model['x0x_max']
                        self.power_model.ext_grid.at[element, 'r0x0_max'] = model['r0x0_max']
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'trafo':
                        node0 = get_node(local_nodes[0])
                        node1 = get_node(local_nodes[1])
                        element = pp.create_transformer_from_parameters(self.power_model, hv_bus=node0, lv_bus=node1, **model)
                        self.power_model.trafo.at[element, 'vector_group'] = model['vector_group']
                        self.power_model.trafo.at[element, 'vk0_percent'] = model['vk0_percent']
                        self.power_model.trafo.at[element, 'vkr0_percent'] = model['vkr0_percent']
                        self.power_model.trafo.at[element, 'mag0_percent'] = model['mag0_percent']
                        self.power_model.trafo.at[element, 'mag0_rx'] = model['mag0_rx']
                        self.power_model.trafo.at[element, 'si0_hv_partial'] = model['si0_hv_partial']
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'trafo3w':
                        node0 = get_node(local_nodes[0])
                        node1 = get_node(local_nodes[1])
                        node2 = get_node(local_nodes[2])
                        element = pp.create_transformer3w_from_parameters(self.power_model, hv_bus=node0, mv_bus=node1, lv_bus=node2, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'gen':
                        node = get_node(local_nodes[0])
                        element = pp.create_gen(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'sgen':
                        node = get_node(local_nodes[0])
                        element = pp.create_sgen(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'storage':
                        node = get_node(local_nodes[0])
                        element = pp.create_storage(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'impedance':
                        node0 = get_node(local_nodes[0])
                        node1 = get_node(local_nodes[1])
                        element = pp.create_impedance(self.power_model, from_bus=node0, to_bus=node1, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'line':
                        node0 = get_node(local_nodes[0])
                        node1 = get_node(local_nodes[1])
                        element = pp.create_line_from_parameters(self.power_model, from_bus=node0, to_bus=node1, **model)
                        self.power_model.line.at[element, 'endtemp_degree'] = model['endtemp_degree']  # Add value explicitly to avoid bug in PP
                        self.power_model.line.at[element, 'r0_ohm_per_km'] = model['r0_ohm_per_km']
                        self.power_model.line.at[element, 'x0_ohm_per_km'] = model['x0_ohm_per_km']
                        self.power_model.line.at[element, 'c0_nf_per_km'] = model['c0_nf_per_km']
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'dcline':
                        node0 = get_node(local_nodes[0])
                        node1 = get_node(local_nodes[1])
                        element = pp.create_dcline(self.power_model, from_bus=node0, to_bus=node1, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'load':
                        node = get_node(local_nodes[0])
                        element = pp.create_load_from_cosphi(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'shunt':
                        node = get_node(local_nodes[0])
                        element = pp.create_shunt(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'ward':
                        node = get_node(local_nodes[0])
                        element = pp.create_ward(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                    elif elementcode == 'xward':
                        node = get_node(local_nodes[0])
                        element = pp.create_xward(self.power_model, bus=node, **model)
                        self.power_elements[(k1,k2)] = (elementcode, element)
                        self.power_elements_inverted[elementcode, element] = (k1,k2)
                        
        # Update node voltages
        grids = self.power_model.ext_grid.to_dict(orient='records')
        gens = self.power_model.gen.to_dict(orient='records')      
        trafo = self.power_model.trafo.to_dict(orient='records')
        trafo3w = self.power_model.trafo3w.to_dict(orient='records')
        mg_no_trafos = pp.topology.create_nxgraph(self.power_model, include_trafos = False, include_trafo3ws=False)
        voltage_zones = list(pp.topology.connected_components(mg_no_trafos))
        voltage_updated_from = dict()  # Maps node to voltage update elements; index: node, value: [(k1,k2), ...]
        
        def set_voltage(bus, vn_kv, k1, k2):
            for zone in voltage_zones:
                if bus in zone:  # If element bus in zone
                    for power_node in zone:  # Update all nodes in zone
                        node = self.power_nodes_inverted[power_node]
                        if node not in voltage_updated_from:
                            self.power_model.bus.vn_kv.at[power_node] = vn_kv
                            voltage_updated_from[node] = [(k1,k2)]
                        else:
                            voltage_updated_from[node].append((k1,k2))
                            
        for index, values in enumerate(grids):
            bus = values['bus']
            k1,k2 = self.power_elements_inverted['ext_grid', index]
            vn_kv = self.base_models[(k1,k2)]['fields']['vn_kv']['value']
            set_voltage(bus, vn_kv, k1, k2)
        for index, values in enumerate(gens):
            bus = values['bus']
            k1,k2 = self.power_elements_inverted['gen', index]
            vn_kv = self.base_models[(k1,k2)]['fields']['vn_kv']['value']
            set_voltage(bus, vn_kv, k1, k2)
        for index, values in enumerate(trafo):
            lv_bus = values['lv_bus']
            hv_bus = values['hv_bus']
            k1,k2 = self.power_elements_inverted['trafo', index]
            vn_lv_kv = values['vn_lv_kv']
            vn_hv_kv = values['vn_hv_kv']
            set_voltage(lv_bus, vn_lv_kv, k1, k2)
            set_voltage(hv_bus, vn_hv_kv, k1, k2)
        for index, values in enumerate(trafo3w):
            lv_bus = values['lv_bus']
            mv_bus = values['mv_bus']
            hv_bus = values['hv_bus']
            k1,k2 = self.power_elements_inverted['trafo3w', index]
            vn_lv_kv = values['vn_lv_kv']
            vn_mv_kv = values['vn_mv_kv']
            vn_hv_kv = values['vn_hv_kv']
            set_voltage(lv_bus, vn_lv_kv, k1, k2)
            set_voltage(mv_bus, vn_mv_kv, k1, k2)
            set_voltage(hv_bus, vn_hv_kv, k1, k2)
            
        # Update node voltage in results
        for bus, model in self.power_model.bus.iterrows():
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            node_result['vn_kv'] = misc.get_field_dict('float', 'Vn', 'kV', model['vn_kv'], decimal=3)
        
        log.info('ProjectModel - build_powermodel - model generated')
        
    def run_diagnostics(self):
        """Run Diagnostics"""
        log.info('ProjectModel - run_diagnostics - running diagnostic...')
        pp_diagnostic_result = pp.diagnostic(self.power_model, report_style='None', warnings_only = True, return_result_dict=True)
        # Parse result and add to main diagnostic result dict
        result_parsed = []
        self.diagnostic_results['Electrical Model'] = result_parsed
        for code, result in pp_diagnostic_result.items():
            if code == 'busses_mult_gens_ext_grids':
                result_parsed.append(['Multiple voltage sources connected to bus', [['node', result]]])
            elif code == 'no_ext_grid':
                if result:
                    result_parsed.append(['No power source found in the model.', []])
            elif code == 'inconsistent_voltages':
                model = []
                for element_code, elementids in result.items():
                    model.append([element_code, elementids])
                result_parsed.append(['Different voltage sources connected together.', model])
            elif code == 'invalid_values':
                model = []
                for element_code, elements in result.items():
                    elementids = []
                    for element in elements:
                        if element:
                            elementids.append(element[0])
                    model.append([element_code, elementids])
                result_parsed.append(['Invalid values found in model.', model])
            elif code == 'isolated_sections':
                if 'isolated_sections' in result:
                    model = []
                    for elementids in result['isolated_sections']:
                        model.extend(elementids)
                    result_parsed.append(['Elements disconnected from network.', [['node', model]]])
                if 'lines_both_switches_open' in result:
                    model = result['lines_both_switches_open']
                    result_parsed.append(['Lines disconnected at both ends.', [['line', model]]])
            elif code == 'lines_with_impedance_zero':
                result_parsed.append(['Lines with zero impedance.', [['line', result]]])
            elif code == 'wrong_switch_configuration':
                if result:
                    result_parsed.append(['Wrong switch configuration.', []])
            elif code == 'disconnected_elements':
                model = []
                if result:
                    for line in result:
                        for element_code, elementids in line.items():
                            model.append([element_code, elementids])
                    result_parsed.append(['Invalid values found in model.', model])
            elif code == 'parallel_switches':
                model = []
                for elementids in result:
                    model.extend(elementids)
                result_parsed.append(['Parallel connected switches.', [['switch', model]]])
            else:
                result_parsed.append(['Warning - ' + code + ': ' + str(result), []])
                
        self.diagnostics_view.update(self.diagnostic_results, self.select_powermodel)
        log.info('ProjectModel - run_diagnostics - diagnostic run')
        
    def run_powerflow(self):
        """Run power flow"""
        
        pp.runpp(self.power_model, neglect_open_switch_branches=True)
        
        # Update nodes
        for bus, result in self.power_model.res_bus.iterrows():
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            
            node_result['delv_perc'] = misc.get_field_dict('float', 'ΔV', '%', 100-result['vm_pu']*100, decimal=1)  
            # node_result['vm_pu'] = misc.get_field_dict('float', 'V', 'pu', result['vm_pu'], decimal=3)
            # node_result['va_degree'] = misc.get_field_dict('float', 'V angle', 'degree', result['va_degree'], decimal=1)
            
        # Update elements
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                
                if (k1,k2) in self.power_elements:
                    # Create/get element dict
                    if (k1,k2) in self.element_results:
                        element_result = self.element_results[k1,k2]
                    else:
                        element_result = dict()
                        self.element_results[k1,k2] = element_result
                    (elementcode, element_id) = self.power_elements[k1,k2]
                    # Remove elements without results
                    if elementcode != 'switch':
                        result = getattr(self.power_model, 'res_' + elementcode).loc[element_id]
                    
                    # Populate element results
                    if elementcode in ['ext_grid','load','sgen','shunt','ward','sward','storage']:
                        element_result['p_mw'] = misc.get_field_dict('float', 'P', 'MW', result['p_mw'])
                        element_result['q_mvar'] = misc.get_field_dict('float', 'Q', 'MVAr', result['q_mvar'])
                    elif elementcode == 'trafo':
                        element_result['p_hv_mw'] = misc.get_field_dict('float', 'P HV', 'MW', result['p_hv_mw'])
                        element_result['q_hv_mvar'] = misc.get_field_dict('float', 'Q HV', 'MVAr', result['q_hv_mvar'])
                        element_result['p_lv_mw'] = misc.get_field_dict('float', 'P LV', 'MW', result['p_lv_mw'])
                        element_result['q_lv_mvar'] = misc.get_field_dict('float', 'Q LV', 'MVAr', result['q_lv_mvar'])
                        element_result['pl_mw'] = misc.get_field_dict('float', 'P loss', 'MW', result['pl_mw'])
                        element_result['ql_mvar'] = misc.get_field_dict('float', 'Q loss', 'MVAr', result['ql_mvar'])
                        element_result['loading_percent'] = misc.get_field_dict('float', '% Loading', '%', result['loading_percent'])
                    elif elementcode == 'trafo3w':
                        element_result['p_hv_mw'] = misc.get_field_dict('float', 'P HV', 'MW', result['p_hv_mw'])
                        element_result['q_hv_mvar'] = misc.get_field_dict('float', 'Q HV', 'MVAr', result['q_hv_mvar'])
                        element_result['p_mv_mw'] = misc.get_field_dict('float', 'P MV', 'MW', result['p_mv_mw'])
                        element_result['q_mv_mvar'] = misc.get_field_dict('float', 'Q MV', 'MVAr', result['q_mv_mvar'])
                        element_result['p_lv_mw'] = misc.get_field_dict('float', 'P LV', 'MW', result['p_lv_mw'])
                        element_result['q_lv_mvar'] = misc.get_field_dict('float', 'Q LV', 'MVAr', result['q_lv_mvar'])
                        element_result['pl_mw'] = misc.get_field_dict('float', 'P loss', 'MW', result['pl_mw'])
                        element_result['ql_mvar'] = misc.get_field_dict('float', 'Q loss', 'MVAr', result['ql_mvar'])
                        element_result['loading_percent'] = misc.get_field_dict('float', '% Loading', '%', result['loading_percent'])
                    elif elementcode == 'gen':
                        element_result['p_mw'] = misc.get_field_dict('float', 'P', 'MW', result['p_mw'])
                        element_result['q_mvar'] = misc.get_field_dict('float', 'Q', 'MVAr', result['q_mvar'])
                        element_result['vm_pu'] = misc.get_field_dict('float', 'V', 'pu', result['vm_pu'])
                        element_result['va_degree'] = misc.get_field_dict('float', 'V angle', 'degree', result['va_degree'])
                    elif elementcode in ['impedence','dcline']:
                        element_result['p_from_mw'] = misc.get_field_dict('float', 'P from', 'MW', result['p_from_mw'])
                        element_result['q_from_mvar'] = misc.get_field_dict('float', 'Q from', 'MVAr', result['q_from_mvar'])
                        element_result['p_to_mw'] = misc.get_field_dict('float', 'P to', 'MW', result['p_to_mw'])
                        element_result['q_to_mvar'] = misc.get_field_dict('float', 'Q to', 'MVAr', result['q_to_mvar'])
                        element_result['pl_mw'] = misc.get_field_dict('float', 'P loss', 'MW', result['pl_mw'])
                        element_result['ql_mvar'] = misc.get_field_dict('float', 'Q loss', 'MVAr', result['ql_mvar'])
                    elif elementcode in ['line']:
                        element_result['p_from_mw'] = misc.get_field_dict('float', 'P from', 'MW', result['p_from_mw'])
                        element_result['q_from_mvar'] = misc.get_field_dict('float', 'Q from', 'MVAr', result['q_from_mvar'])
                        element_result['p_to_mw'] = misc.get_field_dict('float', 'P to', 'MW', result['p_to_mw'])
                        element_result['q_to_mvar'] = misc.get_field_dict('float', 'Q to', 'MVAr', result['q_to_mvar'])
                        element_result['pl_mw'] = misc.get_field_dict('float', 'P loss', 'MW', result['pl_mw'])
                        element_result['ql_mvar'] = misc.get_field_dict('float', 'Q loss', 'MVAr', result['ql_mvar'])
                        element_result['loading_percent'] = misc.get_field_dict('float', '% Loading', '%', result['loading_percent'])
                    
        log.info('ProjectModel - run_powerflow - model generated')
        
    def run_powerflow_timeseries(self):
        """Run power flow time series simulation"""
        
        sgens = self.power_model.sgen.to_dict(orient='records')
        loads = self.power_model.load.to_dict(orient='records')
        dfdata_load = dict()
        dfdata_p = dict()
        dfdata_q = dict()
        n_ts = 24

        # Sgen controller
        for gen_index, values in enumerate(sgens):
            col_p = []
            col_q = []
            dfdata_p[gen_index] = col_p
            dfdata_q[gen_index] = col_q
            p_mw = values['p_mw']
            q_mvar = values['q_mvar']
            k1,k2 = self.power_elements_inverted['sgen', gen_index]
            load_profile = self.loadprofiles[self.base_models[(k1,k2)]['fields']['load_profile']['value']][1][0]
            load_profile_func = GraphModel(load_profile).get_value_func()
            for time_index in range(n_ts):
                col_p.append(load_profile_func(time_index)*p_mw)
                col_q.append(load_profile_func(time_index)*q_mvar)
        df_p = pd.DataFrame(data=dfdata_p, index=list(range(n_ts)), columns=self.power_model.sgen.index)
        df_q = pd.DataFrame(data=dfdata_q, index=list(range(n_ts)), columns=self.power_model.sgen.index)
        ds_p = DFData(df_p)
        ds_q = DFData(df_q)
        const_sgen_p = control.ConstControl(self.power_model, element='sgen', element_index=self.power_model.sgen.index,
                                          variable='p_mw', data_source=ds_p, profile_name=self.power_model.sgen.index)
        const_sgen_q = control.ConstControl(self.power_model, element='sgen', element_index=self.power_model.sgen.index,
                                          variable='q_mvar', data_source=ds_q, profile_name=self.power_model.sgen.index)

        # Load controller
        for load_index, values in enumerate(loads):
            col_p = []
            col_q = []
            dfdata_p[load_index] = col_p
            dfdata_q[load_index] = col_q
            p_mw = values['p_mw']
            q_mvar = values['q_mvar']
            k1,k2 = self.power_elements_inverted['load', load_index]
            load_profile = self.loadprofiles[self.base_models[(k1,k2)]['fields']['load_profile']['value']][1][0]
            load_profile_func = GraphModel(load_profile).get_value_func()
            for time_index in range(n_ts):
                col_p.append(load_profile_func(time_index)*p_mw)
                col_q.append(load_profile_func(time_index)*q_mvar)
        df_p = pd.DataFrame(data=dfdata_p, index=list(range(n_ts)), columns=self.power_model.load.index)
        df_q = pd.DataFrame(data=dfdata_q, index=list(range(n_ts)), columns=self.power_model.load.index)
        ds_p = DFData(df_p)
        ds_q = DFData(df_q)
        const_load_p = control.ConstControl(self.power_model, element='load', element_index=self.power_model.load.index,
                                          variable='p_mw', data_source=ds_p, profile_name=self.power_model.load.index)
        const_load_q = control.ConstControl(self.power_model, element='load', element_index=self.power_model.load.index,
                                          variable='q_mvar', data_source=ds_q, profile_name=self.power_model.load.index)

        # Output writer
        time_steps = range(n_ts)
        log_variables = []
        log_variables.append(('res_bus', 'vm_pu'))
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                
                if (k1,k2) in self.power_elements:
                    (elementcode, element_id) = self.power_elements[k1,k2]                    
                    if elementcode in ['ext_grid','load','sgen','shunt','ward','sward','storage']:
                        log_variables.append(('res_'+elementcode, 'p_mw'))
                        log_variables.append(('res_'+elementcode, 'q_mvar'))
                    elif elementcode == 'trafo':
                        log_variables.append(('res_'+elementcode, 'p_hv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_hv_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_lv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_lv_mvar'))
                        log_variables.append(('res_'+elementcode, 'pl_mw'))
                        log_variables.append(('res_'+elementcode, 'ql_mvar'))
                        log_variables.append(('res_'+elementcode, 'loading_percent'))
                    elif elementcode == 'trafo3w':
                        log_variables.append(('res_'+elementcode, 'p_hv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_hv_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_mv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_mv_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_lv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_lv_mvar'))
                        log_variables.append(('res_'+elementcode, 'pl_mw'))
                        log_variables.append(('res_'+elementcode, 'ql_mvar'))
                        log_variables.append(('res_'+elementcode, 'loading_percent'))
                    elif elementcode == 'gen':
                        log_variables.append(('res_'+elementcode, 'p_mw'))
                        log_variables.append(('res_'+elementcode, 'q_mvar'))
                        log_variables.append(('res_'+elementcode, 'vm_pu'))
                        log_variables.append(('res_'+elementcode, 'va_degree'))
                    elif elementcode in ['impedence','dcline']:
                        log_variables.append(('res_'+elementcode, 'p_from_mw'))
                        log_variables.append(('res_'+elementcode, 'q_from_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_to_mw'))
                        log_variables.append(('res_'+elementcode, 'q_to_mvar'))
                        log_variables.append(('res_'+elementcode, 'pl_mw'))
                        log_variables.append(('res_'+elementcode, 'ql_mvar'))
                    elif elementcode in ['line']:
                        log_variables.append(('res_'+elementcode, 'p_from_mw'))
                        log_variables.append(('res_'+elementcode, 'q_from_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_to_mw'))
                        log_variables.append(('res_'+elementcode, 'q_to_mvar'))
                        log_variables.append(('res_'+elementcode, 'pl_mw'))
                        log_variables.append(('res_'+elementcode, 'ql_mvar'))
                        log_variables.append(('res_'+elementcode, 'loading_percent'))
        
        
        ow = OutputWriter(self.power_model, time_steps, output_path=None, log_variables=log_variables)

        # Starting the timeseries simulation
        timeseries.run_timeseries(self.power_model, time_steps=time_steps)
        
        def set_graphdata(result, table, data):
            model = []
            maintitle = ''
            maincaption = ''
            mainunit = ''
            ylimits_min = []
            ylimits_max = []
            for code, element_id, caption, unit, decimal, modfunc in data:
                values = []
                table_code = 'res_' + table + '.' + code
                for time_index in time_steps:
                    if modfunc:
                        value = modfunc(ow.np_results[table_code][time_index][element_id])
                    else:
                        value = ow.np_results[table_code][time_index][element_id]
                    values.append(value)
                val_avg = round(sum(values)/len(values), decimal)
                val_max = round(max(values), decimal)
                val_min = round(min(values), decimal)
                delta = (val_max - val_min)*0.1
                title = caption + ': (max: {}, min: {}, avg: {})'.format(val_max, val_min, val_avg)
                ylimits_min.append(val_min - delta)
                ylimits_max.append(val_max + delta)
                
                model.append({'mode':misc.GRAPH_DATATYPE_PROFILE, 'title':caption, 'xval':time_steps, 'yval':values})
                maintitle += title + '\n'
                maincaption += caption + ', '
                mainunit += unit + ', '
            
            maintitle = maintitle.strip('\n') if len(data) > 1 else '(max: {}, min: {}, avg: {})'.format(val_max, val_min, val_avg)
            maincaption =maincaption.strip(', ')
            mainunit = mainunit.strip(', ')
            ylimits = (min(ylimits_min), max(ylimits_max), 0.1)    
            graph_model = [maintitle, model]
            result[code] = misc.get_field_dict('graph', maincaption, mainunit, graph_model, decimal=decimal)
            result[code]['graph_options'] = (misc.GRAPH_LOAD_TIME_LIMITS, ylimits, 'Time (Hr)', maincaption + ' (' + mainunit + ')')
        
        # Update nodes
        for bus, node in self.power_nodes_inverted.items():
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            modfunc = lambda x: 100-x*100
            set_graphdata(node_result, 'bus', [['vm_pu', bus, 'ΔV', '%', 2, modfunc]])
            
        # Update elements
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                
                if (k1,k2) in self.power_elements:
                    # Create/get element dict
                    if (k1,k2) in self.element_results:
                        element_result = self.element_results[k1,k2]
                    else:
                        element_result = dict()
                        self.element_results[k1,k2] = element_result
                    (elementcode, element_id) = self.power_elements[k1,k2]
                    
                    # Populate element results
                    if elementcode in ['ext_grid','load','sgen','shunt','ward','sward','storage']:
                        set_graphdata(element_result, elementcode, [['p_mw', element_id, 'P', 'MW', 4, None],
                                                                    ['q_mvar', element_id, 'Q', 'MVAr', 4, None]])
                    elif elementcode == 'trafo':
                        set_graphdata(element_result, elementcode, [['p_hv_mw', element_id, 'P HV', 'MW', 4, None],
                                                                    ['q_hv_mvar', element_id, 'Q HV', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['p_lv_mw', element_id, 'P LV', 'MW', 4, None],
                                                                    ['q_lv_mvar', element_id, 'Q LV', 'MVAr', 4, None]])
                        # set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None]])
                        # set_graphdata(element_result, elementcode, [['ql_mvar', element_id, 'Q loss', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['loading_percent', element_id, '% Loading', '%', 1, None]])
                    elif elementcode == 'trafo3w':
                        set_graphdata(element_result, elementcode, [['p_hv_mw', element_id, 'P HV', 'MW', 4, None],
                                                                    ['q_hv_mvar', element_id, 'Q HV', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['p_mv_mw', element_id, 'P MV', 'MW', 4, None],
                                                                    ['q_mv_mvar', element_id, 'Q MV', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['p_lv_mw', element_id, 'P LV', 'MW', 4, None],
                                                                    ['q_lv_mvar', element_id, 'Q LV', 'MVAr', 4, None]])
                        # set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None]])
                        # set_graphdata(element_result, elementcode, [['ql_mvar', element_id, 'Q loss', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['loading_percent', element_id, '% Loading', '%', 1, None]])
                    elif elementcode == 'gen':
                        set_graphdata(element_result, elementcode, [['p_mw', element_id, 'P', 'MW', 4, None],
                                                                    ['q_mvar', element_id, 'Q', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['vm_pu', element_id, 'V', 'pu', 3, None]])
                        set_graphdata(element_result, elementcode, [['va_degree', element_id, 'V angle', 'degree', 1, None]])
                    elif elementcode in ['impedence','dcline']:
                        set_graphdata(element_result, elementcode, [['p_from_mw', element_id, 'P from', 'MW', 4, None],
                                                                    ['q_from_mvar', element_id, 'Q from', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['p_to_mw', element_id, 'P to', 'MW', 4, None],
                                                                    ['q_to_mvar', element_id, 'Q to', 'MVAr', 4, None]])
                        # set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None]])
                        # set_graphdata(element_result, elementcode, [['ql_mvar', element_id, 'Q loss', 'MVAr', 4, None]])
                    elif elementcode in ['line']:
                        set_graphdata(element_result, elementcode, [['p_from_mw', element_id, 'P from', 'MW', 4, None],
                                                                    ['q_from_mvar', element_id, 'Q from', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['p_to_mw', element_id, 'P to', 'MW', 4, None],
                                                                    ['q_to_mvar', element_id, 'Q to', 'MVAr', 4, None]])
                        # set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None]])
                        # set_graphdata(element_result, elementcode, [['ql_mvar', element_id, 'Q loss', 'MVAr', 4, None]])
                        set_graphdata(element_result, elementcode, [['loading_percent', element_id, '% Loading', '%', 1, None]])
                    
        log.info('ProjectModel - run_powerflow - model generated')
    
    def run_sym_sccalc(self):
        """Run symmetric short circuit calculation"""

        pp.shortcircuit.calc_sc(self.power_model, fault='3ph', case='max', lv_tol_percent=6, branch_results=True, check_connectivity=True)
        res_3ph_max = self.power_model.res_bus_sc.to_dict()
        pp.shortcircuit.calc_sc(self.power_model, fault='3ph', case='min', lv_tol_percent=6, branch_results=True, check_connectivity=True)
        res_3ph_min = self.power_model.res_bus_sc.to_dict()
                
        # Update nodes
        for bus in res_3ph_max['ikss_ka']:
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            node_result['ikss_ka_3ph_max'] = misc.get_field_dict('float', 'Isc (sym, max)', 'kA', res_3ph_max['ikss_ka'][bus], decimal=2)
            node_result['ikss_ka_3ph_min'] = misc.get_field_dict('float', 'Isc (sym, min)', 'kA', res_3ph_min['ikss_ka'][bus], decimal=2)
                    
        log.info('ProjectModel - run_sym_sccalc - model generated')
    
    def run_linetoground_sccalc(self):
        """Run line to ground short circuit calculation"""

        pp.shortcircuit.calc_sc(self.power_model, fault='1ph', case='max', lv_tol_percent=6, branch_results=True, check_connectivity=True)
        res_1ph_max = self.power_model.res_bus_sc.to_dict()
        #pp.shortcircuit.calc_sc(self.power_model, fault='1ph', case='min', lv_tol_percent=6, branch_results=True, check_connectivity=True)
        #res_1ph_min = self.power_model.res_bus_sc.to_dict()
                
        # Update nodes
        for bus in res_1ph_max['ikss_ka']:
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            node_result['ikss_ka_1ph_max'] = misc.get_field_dict('float', 'Isc (L-G, max)', 'kA', res_1ph_max['ikss_ka'][bus], decimal=2)
            # node_result['ikss_ka_1ph_min'] = misc.get_field_dict('float', 'Isc (L-G, min)', 'kA', res_1ph_min['ikss_ka'][bus], decimal=2)
                    
        log.info('ProjectModel - run_linetoground_sccalc - model generated')
        
    def update_results(self):
        # Copy node data to element power model
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                
                if (k1,k2) in self.power_elements:
                    # Create/get element dict
                    if (k1,k2) in self.element_results:
                        element_result = self.element_results[k1,k2]
                    else:
                        element_result = dict()
                        self.element_results[k1,k2] = element_result
                    (elementcode, element_id) = self.power_elements[k1,k2]
                    
                    # Add node related data to elements
                    for port_no, port in enumerate(element.get_ports_global()):
                        node = self.port_mapping[(k1,) + tuple(port)]
                        node_result = self.node_results[node]
                        for code, field in node_result.items():
                            code = 'port_' + str(port_no) + code
                            element_result[code] = copy.deepcopy(field)
                            element_result[code]['caption'] = '<i>[' + str(port_no) + ']: ' + element_result[code]['caption'] + '</i>'
                
                elif element.code == 'element_busbar':
                    # Create/get element dict
                    if (k1,k2) in self.element_results:
                        element_result = self.element_results[k1,k2]
                    else:
                        element_result = dict()
                        self.element_results[k1,k2] = element_result
                    node = self.port_mapping[(k1,) + tuple(element.get_ports_global()[0])]
                    node_result = self.node_results[node]
                    for code, field in node_result.items():
                        element_result[code] = copy.deepcopy(field)
                        
        # Update element with power model
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                if (k1,k2) in self.element_results:
                    element_result = self.element_results[k1,k2]
                    element.res_fields = element_result
        log.info('ProjectModel - update_results - results updated')
        
    ## Export/Import functions
    
    def export_html_report(self, filename):
        pplot.to_html(self.power_model, filename)
        
    def export_json(self, filename):
        pp.to_json(self.power_model, filename)
        
    def export_drawing(self, filename):
        surface = cairo.PDFSurface(filename, 0, 0)
        #TODO
        #surface.set_metadata(PDFMetadata.TITLE, '')
        #surface.set_metadata(PDFMetadata.AUTHOR, '')
        #surface.set_metadata(PDFMetadata.SUBJECT, 'Electrical schematic drawing')
        #surface.set_metadata(PDFMetadata.CREATOR, misc.PROGRAM_NAME)
        #surface.set_metadata(PDFMetadata.CREATE_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        #surface.set_metadata(PDFMetadata.MOD_DATE, datetime.datetime.now().astimezone().replace(microsecond=0).isoformat())
        context = cairo.Context(surface)
        for drawing_model in self.drawing_models:
            surface.set_size(drawing_model.fields['page_width']['value'], drawing_model.fields['page_height']['value'])
            drawing_model.export_drawing(context)
            surface.show_page()
        surface.finish()
        
    def get_model(self):
        """Get storage model"""
        drawing_models = []
        for drawing_model in self.drawing_models:
            drawing_models.append(drawing_model.get_model())
        model = {'drawing_models': drawing_models, 
                 'fields': self.fields,
                 'loadprofiles':self.loadprofiles}
        return ['ProjectModel', model]
            
    def set_model(self, model):
        """Set storage model"""
        self.clear_all()
        if model[0] == 'ProjectModel':
            self.fields = model[1]['fields']
            self.loadprofiles = model[1]['loadprofiles']
            for slno, base_model in enumerate(model[1]['drawing_models']):
                if slno > 0:
                    self.append_page()
                self.drawing_model.set_model(base_model)
        else:
            return False
        # Switch to first page
        self.set_page(0)
        
    ## Private functions
    
    def combine_connected_nodes(self, duplicate_ports_list):
        def to_edges(ports):
            """ 
                treat `ports` as a Graph and returns it's edges 
                to_edges(['a','b','c','d']) -> [(a,b), (b,c),(c,d)]
            """
            it = iter(ports)
            last = next(it)
            for current in it:
                yield last, current
                last = current
                
        G = nx.Graph()
        for part in duplicate_ports_list:
            # each sublist is a bunch of nodes
            G.add_nodes_from(part)
            # it also imlies a number of edges:
            G.add_edges_from(to_edges(part))
        return connected_components(G)
    
    ## Callbacks
    
    def on_switch_tab(self, notebook, page, pagenum):
        """Refresh display on switching between views"""
        log.info('ProjectModel - on_switch_tab called - ' + str(pagenum))
        self.set_page(pagenum, switch_tab=False)
