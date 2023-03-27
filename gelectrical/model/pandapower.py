#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
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

import logging
import copy
import datetime
from gi.repository import Gtk, Gdk
import cairo

import numpy as np
import pandas as pd
import pandapower as pp
import pandapower.plotting as pplot
import pandapower.control as control
import pandapower.networks as nw
import pandapower.timeseries as timeseries
import pandapower.shortcircuit as sc
from pandapower.timeseries import OutputWriter
from pandapower.timeseries.data_sources.frame_data import DFData
import networkx as nx
from networkx.algorithms.components.connected import connected_components

# local files import
from .. import misc
from ..model.graph import GraphModel

# Get logger object
log = logging.getLogger(__name__)


class PandaPowerModel:
    """Class for modelling a Panda Power Project"""

    def __init__(self, network_model, loadprofiles, f_hz=50):

        # Data
        self.network_model = network_model
        self.loadprofiles = loadprofiles

        self.base_elements = self.network_model.base_elements
        # Maps local_node -> global_node i.e. ('(page,element):port') -> global_node
        self.node_mapping = self.network_model.node_mapping
        # Maps global_node -> [element1, ..]
        self.gnode_element_mapping = self.network_model.gnode_element_mapping

        # Power variables
        self.power_model = pp.create_empty_network(name='Project power model', f_hz=f_hz)
        self.power_model_gf = pp.create_empty_network(name='Ground fault power model', f_hz=f_hz)
        self.power_model_lf = pp.create_empty_network(name='Line fault power model', f_hz=f_hz)
        self.power_nodes = dict()  # Maps global_node -> power_node
        self.power_nodes_inverted = dict()  # Maps power_node -> global_node
        self.power_elements = dict()  # Maps element_code -> (table_code, slno)
        self.power_elements_inverted = dict()  # Maps (table_code, slno) -> element_code

        # Results
        self.element_results = dict()
        self.node_results = dict()
        self.diagnostic_results = dict()

    # Analysis functions

    def build_power_model(self, mode=misc.POWER_MODEL_POWERFLOW):
        """Build power models for use with pandapower"""
        self.power_nodes = dict()
        self.power_nodes_inverted = dict()
        self.power_elements = dict()
        self.power_elements_inverted = dict()

        if mode == misc.POWER_MODEL_POWERFLOW:
            self.power_model = pp.create_empty_network()
            power_model = self.power_model

        elif mode == misc.POWER_MODEL_LINEFAULT:
            self.power_model_lf = pp.create_empty_network()
            power_model = self.power_model_lf
            
        elif mode == misc.POWER_MODEL_GROUNDFAULT:
            self.power_model_gf = pp.create_empty_network()
            power_model = self.power_model_gf

        def get_node(local_node):
            if local_node in self.node_mapping:
                node = self.node_mapping[local_node]
                if node not in self.power_nodes:
                    bus = pp.create_bus(power_model, name=str(
                        node), type='n', vn_kv=0.415)
                    self.power_nodes[node] = bus
                    self.power_nodes_inverted[bus] = node
                    return bus
                else:
                    return self.power_nodes[node]

        # Create all elements
        for e_code, element in self.base_elements.items():
            power_model_elements = element.get_power_model(str(e_code), mode)
            for slno, power_model_sub in enumerate(power_model_elements):
                elementcode, local_nodes, model = power_model_sub
                if elementcode == 'bus':
                    node = get_node(local_nodes[0])
                    power_model.bus.name.at[node] = model['name']
                    power_model.bus.vn_kv.at[node] = model['vn_kv']
                    power_model.bus.type.at[node] = model['type']
                elif elementcode == 'switch':
                    node0 = get_node(local_nodes[0])
                    node1 = get_node(local_nodes[1])
                    element = pp.create_switch(
                        power_model, bus=node0, element=node1, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'ext_grid':
                    node = get_node(local_nodes[0])
                    element = pp.create_ext_grid(
                        power_model, bus=node, **model)
                    power_model.ext_grid.at[element,
                                                 'x0x_max'] = model['x0x_max']
                    power_model.ext_grid.at[element,
                                                 'r0x0_max'] = model['r0x0_max']
                    power_model.ext_grid.at[element,
                                                 'x0x_min'] = model['x0x_min']
                    power_model.ext_grid.at[element,
                                                 'r0x0_min'] = model['r0x0_min']
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'trafo':
                    node0 = get_node(local_nodes[0])
                    node1 = get_node(local_nodes[1])
                    element = pp.create_transformer_from_parameters(
                        power_model, hv_bus=node0, lv_bus=node1, **model)
                    power_model.trafo.at[element,
                                              'vector_group'] = model['vector_group']
                    power_model.trafo.at[element,
                                              'vk0_percent'] = model['vk0_percent']
                    power_model.trafo.at[element,
                                              'vkr0_percent'] = model['vkr0_percent']
                    power_model.trafo.at[element,
                                              'mag0_percent'] = model['mag0_percent']
                    power_model.trafo.at[element,
                                              'mag0_rx'] = model['mag0_rx']
                    power_model.trafo.at[element,
                                              'si0_hv_partial'] = model['si0_hv_partial']
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'trafo3w':
                    node0 = get_node(local_nodes[0])
                    node1 = get_node(local_nodes[1])
                    node2 = get_node(local_nodes[2])
                    element = pp.create_transformer3w_from_parameters(
                        power_model, hv_bus=node0, mv_bus=node1, lv_bus=node2, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'gen':
                    node = get_node(local_nodes[0])
                    element = pp.create_gen(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'sgen':
                    node = get_node(local_nodes[0])
                    element = pp.create_sgen(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'asymmetric_sgen':
                    node = get_node(local_nodes[0])
                    element = pp.create_asymmetric_sgen(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'storage':
                    node = get_node(local_nodes[0])
                    element = pp.create_storage(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'impedance':
                    node0 = get_node(local_nodes[0])
                    node1 = get_node(local_nodes[1])
                    element = pp.create_impedance(
                        power_model, from_bus=node0, to_bus=node1, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'line':
                    node0 = get_node(local_nodes[0])
                    node1 = get_node(local_nodes[1])
                    element = pp.create_line_from_parameters(
                        power_model, from_bus=node0, to_bus=node1, **model)
                    # Add value explicitly to avoid bug in PP
                    power_model.line.at[element,
                                             'endtemp_degree'] = model['endtemp_degree']
                    power_model.line.at[element,
                                             'r0_ohm_per_km'] = model['r0_ohm_per_km']
                    power_model.line.at[element,
                                             'x0_ohm_per_km'] = model['x0_ohm_per_km']
                    power_model.line.at[element,
                                             'c0_nf_per_km'] = model['c0_nf_per_km']
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'dcline':
                    node0 = get_node(local_nodes[0])
                    node1 = get_node(local_nodes[1])
                    element = pp.create_dcline(
                        power_model, from_bus=node0, to_bus=node1, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'load':
                    node = get_node(local_nodes[0])
                    element = pp.create_load_from_cosphi(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'asymmetric_load':
                    node = get_node(local_nodes[0])
                    element = pp.create_asymmetric_load(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'shunt':
                    node = get_node(local_nodes[0])
                    element = pp.create_shunt(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'ward':
                    node = get_node(local_nodes[0])
                    element = pp.create_ward(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code
                elif elementcode == 'xward':
                    node = get_node(local_nodes[0])
                    element = pp.create_xward(
                        power_model, bus=node, **model)
                    self.power_elements[e_code] = (elementcode, element)
                    self.power_elements_inverted[elementcode, element] = e_code

        # Update node voltages
        grids = power_model.ext_grid.to_dict(orient='records')
        gens = power_model.gen.to_dict(orient='records')
        trafo = power_model.trafo.to_dict(orient='records')
        trafo3w = power_model.trafo3w.to_dict(orient='records')
        mg_no_trafos = pp.topology.create_nxgraph(
            power_model, include_trafos=False, include_trafo3ws=False)
        voltage_zones = list(pp.topology.connected_components(mg_no_trafos))
        # Maps node to voltage update elements; index: node, value: [e_code, ...]
        voltage_updated_from = dict()

        def set_voltage(bus, vn_kv, e_code):
            for zone in voltage_zones:
                if bus in zone:  # If element bus in zone
                    for power_node in zone:  # Update all nodes in zone
                        node = self.power_nodes_inverted[power_node]
                        if node not in voltage_updated_from:
                            power_model.bus.vn_kv.at[power_node] = vn_kv
                            voltage_updated_from[node] = [e_code]
                        else:
                            voltage_updated_from[node].append(e_code)

        for index, values in enumerate(grids):
            bus = values['bus']
            e_code = self.power_elements_inverted['ext_grid', index]
            vn_kv = self.base_elements[e_code].fields['vn_kv']['value']
            set_voltage(bus, vn_kv, e_code)
        for index, values in enumerate(gens):
            bus = values['bus']
            e_code = self.power_elements_inverted['gen', index]
            vn_kv = self.base_elements[e_code].fields['vn_kv']['value']
            set_voltage(bus, vn_kv, e_code)
        for index, values in enumerate(trafo):
            lv_bus = values['lv_bus']
            hv_bus = values['hv_bus']
            e_code = self.power_elements_inverted['trafo', index]
            vn_lv_kv = values['vn_lv_kv']
            vn_hv_kv = values['vn_hv_kv']
            set_voltage(lv_bus, vn_lv_kv, e_code)
            set_voltage(hv_bus, vn_hv_kv, e_code)
        for index, values in enumerate(trafo3w):
            lv_bus = values['lv_bus']
            mv_bus = values['mv_bus']
            hv_bus = values['hv_bus']
            e_code = self.power_elements_inverted['trafo3w', index]
            vn_lv_kv = values['vn_lv_kv']
            vn_mv_kv = values['vn_mv_kv']
            vn_hv_kv = values['vn_hv_kv']
            set_voltage(lv_bus, vn_lv_kv, e_code)
            set_voltage(mv_bus, vn_mv_kv, e_code)
            set_voltage(hv_bus, vn_hv_kv, e_code)

        # Update node voltage in results
        for bus, model in power_model.bus.iterrows():
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            node_result['vn_kv'] = misc.get_field_dict(
                'float', 'Vn', 'kV', model['vn_kv'], decimal=3)

        log.info('PandaPowerModel - build_powermodel - model generated')

    def run_diagnostics(self):
        """Run Diagnostics"""
        log.info('PandaPowerModel - run_diagnostics - running diagnostic...')
        pp_diagnostic_result = pp.diagnostic(
            self.power_model, report_style='None', warnings_only=True, return_result_dict=True)
        # Parse result and add to main diagnostic result dict
        result_parsed = []
        ret_codes = []
        element_tables = ['switch', 'line', 'trafo',
                          'trafo3w', 'load', 'gen', 'sgen', 'ext_grid']
        error_code_subs_dict = {'switches': 'switch',
                                'lines': 'line',
                                'trafos': 'trafo',
                                'trafos3w': 'trafo3w',
                                'loads': 'load',
                                'gens': 'gen',
                                'sgens': 'sgen'}
        tranfo_subs_dict = {'trafo': 'element_transformer',
                            'trafo3w': 'element_transformer3w'}

        def error(message):
            return {'message': message, 'type': 'error'}

        def warning(message):
            return {'message': message, 'type': 'warning'}

        def ref_eid(elementids):
            return ', '.join([self.network_model.base_elements[tuple(eid)].fields['ref']['value'] for eid in elementids])

        for code, result in pp_diagnostic_result.items():
            if result:

                if code == 'disconnected_elements':
                    ret_codes.append(misc.OK)
                    for element_result in result:
                        for element_error_code, elementids_power in element_result.items():
                            if element_error_code in ['buses']:
                                gnodeids = [self.power_nodes_inverted[e_id]
                                            for e_id in elementids_power]
                                message = 'Disconnected Nodes \n' + 'Nodes: ' + ', '.join(map(str, gnodeids))
                                model = [['node', gnodeids]]
                                result_parsed.append([message, model])

                            elif element_error_code in error_code_subs_dict:
                                code = error_code_subs_dict[element_error_code]
                                elementids = [
                                    self.power_elements_inverted[code, e_id] for e_id in elementids_power]
                                message = 'Disconnected element \nElements: ' + ref_eid(elementids)
                                model = [['element', elementids]]
                                result_parsed.append([message, model])

                elif code == 'different_voltage_levels_connected':
                    ret_codes.append(misc.ERROR)
                    for element_error_code, elementids_power in result.items():
                        code = error_code_subs_dict[element_error_code]
                        elementids = [self.power_elements_inverted[code, e_id]
                                      for e_id in elementids_power]
                        message = 'Different voltage levels connected \nElements: ' + ref_eid(elementids)
                        model = [['element', elementids]]
                        result_parsed.append([error(message), model])

                elif code == 'impedance_values_close_to_zero':
                    ret_codes.append(misc.WARNING)
                    for element_result in result:
                        for element_error_code, elementids_power in element_result.items():
                            if element_error_code in ['line', 'xward', 'impedance']:
                                code = element_error_code
                                for elementid_power in elementids_power:
                                    elementids = self.power_elements_inverted[code,
                                                                             elementid_power]
                                    message = 'Line impedance values close to zero \nElements: ' + ref_eid([elementids])
                                    model = [['element', [elementids]]]
                                    result_parsed.append(
                                        [warning(message), model])

                elif code == 'nominal_voltages_dont_match':
                    ret_codes.append(misc.ERROR)
                    for element_error_code, bus_dict in result.items():
                        if element_error_code in ['trafo', 'trafo3w']:
                            elementids_added = []
                            for nodeids_power in bus_dict.values():
                                for n_id in nodeids_power:
                                    gnodeid = self.power_nodes_inverted[n_id]
                                    elementids = self.gnode_element_mapping[gnodeid]
                                    for elementid in elementids:
                                        if self.base_elements[elementid].code == tranfo_subs_dict[element_error_code]:
                                            elementids_added.append(elementid)
                            message = 'Nominal voltages of transformer ports dont match \nElements: ' + ref_eid(elementids)
                            model = [['element', elementids_added]]
                            result_parsed.append([error(message), model])

                elif code == 'invalid_values':
                    ret_codes.append(misc.ERROR)
                    for element_error_code, error_lists in result.items():
                        for error_list in error_lists:
                            if element_error_code in ['bus']:
                                elementid_power = error_list[0]
                                gnodeids = [
                                    self.power_nodes_inverted[elementid_power]]
                                message = 'Invalid values found in model \n' + 'Nodes: ' + ', '.join(map(str, gnodeids))
                                model = [['node', gnodeids]]
                                result_parsed.append([message, model])

                            elif element_error_code in element_tables:
                                code = element_error_code
                                elementid_power = error_list[0]
                                elementids = [
                                    self.power_elements_inverted[code, elementid_power]]
                                message = 'Invalid values found in model \nElements: ' + ref_eid(elementids)
                                model = [['element', elementids]]
                                result_parsed.append([error(message), model])

                elif code == 'multiple_voltage_controlling_elements_per_bus':
                    ret_codes.append(misc.WARNING)
                    for element_error_code, error_lists in result.items():
                        if element_error_code in ['buses_with_gens_and_ext_grids', 'buses_with_mult_ext_grids']:
                            elementids_added = []
                            for n_id in error_lists:
                                gnodeid = self.power_nodes_inverted[n_id]
                                elementids = self.gnode_element_mapping[gnodeid]
                                for elementid in elementids:
                                    if self.base_elements[elementid].code not in ['element_reference', 'element_wire', 'element_busbar']:
                                        elementids_added.append(elementid)
                            message = 'Multiple voltage sources connected to bus \nElements: ' + ref_eid(elementids_added)
                            model = [['elements', elementids_added]]
                            result_parsed.append([warning(message), model])

                elif code == 'no_ext_grid':
                    ret_codes.append(misc.ERROR)
                    result_parsed.append(
                        [error('No power source found in the model.'), []])

                elif code == 'parallel_switches':
                    ret_codes.append(misc.WARNING)
                    model = []
                    for elementids_power in result:
                        elementids = [self.power_elements_inverted['switch', e_id]
                                      for e_id in elementids_power]
                        result_parsed.append(
                            ['Parallel connected switches.', [['element', model]]])
                        message = 'Parallel connected switches \nElements: ' + ref_eid(elementids)
                        model = [['element', elementids]]
                        result_parsed.append([warning(message), model])

                else:
                    ret_codes.append(misc.WARNING)
                    result_parsed.append(
                        [warning(code + ': ' + str(result)), []])

        self.diagnostic_results['Electrical Model'] = result_parsed
        ret_code = misc.ERROR if misc.ERROR in ret_codes else misc.WARNING
        log.info('PandaPowerModel - run_diagnostics - diagnostic run')
        return self.diagnostic_results, ret_code

    def run_powerflow(self, pf_type, runpp_3ph):
        """Run symmetric power flow"""

        # Run powerflow
        if runpp_3ph:
            if pf_type == 'Power flow with diversity':
                # Add diversity factor simulation elements
                # Method 1: Use controller and sgen power injection to reduce power at Bus
                # for e_code, element in self.base_elements.items():
                #     if element.code == 'element_busbar':
                #         lnode = element.get_nodes(str(e_code))[0][0]
                #         gnode = self.node_mapping[lnode]
                #         bus_index = self.power_nodes[gnode]
                #         DF = element.fields['DF']['value']
                #         lines = self.network_model.get_downstream_element(e_code, codes=misc.LINE_ELEMENT_CODES)
                #         if lines:
                #             for line_code in lines:
                #                 (linecode, line_index) = self.power_elements[line_code]
                #                 # Add phantom power injection elements to take up balance power
                #                 sgen_index = pp.create_asymmetric_sgen(self.power_model, bus_index, 
                #                     p_a_mw=0, p_b_mw=0, p_c_mw=0,
                #                     q_a_mvar=0, q_b_mvar=0, q_c_mvar=0)
                #                 # Add control elements
                #                 char_index = pp.control.util.characteristic.Characteristic(self.power_model, 
                #                     [-1e10, 1e10], [-(1-DF)*1e10, (1-DF)*1e10]).index
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'asymmetric_sgen', 'p_a_mw', sgen_index, 'res_line_3ph', 'p_a_from_mw', line_index, 
                #                     char_index, tol=0.0001, order=1)
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'asymmetric_sgen', 'p_b_mw', sgen_index, 'res_line_3ph', 'p_b_from_mw', line_index, 
                #                     char_index, tol=0.0001, order=1)
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'asymmetric_sgen', 'p_c_mw', sgen_index, 'res_line_3ph', 'p_c_from_mw', line_index, 
                #                     char_index, tol=0.0001, order=1)
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'asymmetric_sgen', 'q_a_mvar', sgen_index, 'res_line_3ph', 'q_a_from_mvar', line_index, 
                #                     char_index, tol=0.0001, order=1)
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'asymmetric_sgen', 'q_b_mvar', sgen_index, 'res_line_3ph', 'q_b_from_mvar', line_index, 
                #                     char_index, tol=0.0001, order=1)
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'asymmetric_sgen', 'q_c_mvar', sgen_index, 'res_line_3ph', 'q_c_from_mvar', line_index, 
                #                     char_index, tol=0.0001, order=1)
                # Method 2: Calculate net diversity factor per load and calculate sgen power
                #   injection at each bus
                for e_code, element in self.base_elements.items():
                    if element.code == 'element_busbar':
                        gnode_bus =  self.network_model.gnode_element_mapping_inverted[e_code][0]
                        bus_index = self.power_nodes[gnode_bus]
                        DF_bus = self.network_model.gnode_df_mapping[gnode_bus]
                        loads = self.network_model.get_downstream_element(e_code, codes=misc.LOAD_ELEMENT_CODES)
                        if loads:
                            p_a_mw = 0
                            p_b_mw = 0
                            p_c_mw = 0
                            q_a_mvar = 0
                            q_b_mvar = 0
                            q_c_mvar = 0
                            for load_code in loads:
                                gnode_load = self.network_model.gnode_element_mapping_inverted[load_code][0]
                                path_gnodes = self.network_model.get_nodes_between_gnodes(gnode_bus, gnode_load)
                                path_gnodes.discard(gnode_bus)
                                DF_downstream = [self.network_model.gnode_df_mapping[gnode] for gnode in path_gnodes]
                                RF = np.prod(DF_downstream)*(1-DF_bus)
                                (loadcode, load_index) = self.power_elements[load_code]
                                if loadcode == 'load':
                                    p_a_mw += self.power_model['load']['p_mw'][load_index]/3*RF
                                    p_b_mw += self.power_model['load']['p_mw'][load_index]/3*RF
                                    p_c_mw += self.power_model['load']['p_mw'][load_index]/3*RF
                                    q_a_mvar += self.power_model['load']['q_mvar'][load_index]/3*RF
                                    q_b_mvar += self.power_model['load']['q_mvar'][load_index]/3*RF
                                    q_c_mvar += self.power_model['load']['q_mvar'][load_index]/3*RF
                                elif loadcode == 'asymmetric_load':
                                    p_a_mw += self.power_model['asymmetric_load']['p_a_mw'][load_index]*RF
                                    p_b_mw += self.power_model['asymmetric_load']['p_b_mw'][load_index]*RF
                                    p_c_mw += self.power_model['asymmetric_load']['p_c_mw'][load_index]*RF
                                    q_a_mvar += self.power_model['asymmetric_load']['q_a_mvar'][load_index]*RF
                                    q_b_mvar += self.power_model['asymmetric_load']['q_b_mvar'][load_index]*RF
                                    q_c_mvar += self.power_model['asymmetric_load']['q_c_mvar'][load_index]*RF
                            # Add phantom power injection element to take up balance power
                            sgen_index = pp.create_asymmetric_sgen(self.power_model, bus_index, 
                                p_a_mw=p_a_mw, p_b_mw=p_b_mw, p_c_mw=p_c_mw,
                                q_a_mvar=q_a_mvar, q_b_mvar=q_b_mvar, q_c_mvar=q_c_mvar)

            pp.runpp_3ph(self.power_model, run_control=True)
        else:
            # Add transformer controller for OLTC simulation
            trafos = self.power_model.trafo.to_dict(orient='records')
            for trafo_index, values in enumerate(trafos):
                if values['oltc']:
                    trafo_controller = control.DiscreteTapControl.from_tap_step_percent(self.power_model, 
                        trafo_index, 1, order=1)
            if pf_type == 'Power flow with diversity':
                # Add diversity factor simulation elements
                # Method 1: Use controller and sgen power injection to reduce power at Bus
                # for e_code, element in self.base_elements.items():
                #     if element.code == 'element_busbar':
                #         gnode =  self.network_model.gnode_element_mapping_inverted[e_code][0]
                #         bus_index = self.power_nodes[gnode]
                #         DF = element.fields['DF']['value']
                #         lines = self.network_model.get_downstream_element(e_code, codes=misc.LINE_ELEMENT_CODES)
                #         if lines:
                #             for line_code in lines:
                #                 (linecode, line_index) = self.power_elements[line_code]
                #                 # Add phantom power injection elements to take up balance power
                #                 sgen_index = pp.create_sgen(self.power_model, bus_index, p_mw=0, q_mvar=0)
                #                 # Add control elements
                #                 char_index = pp.control.util.characteristic.Characteristic(self.power_model, 
                #                     [-1e10, 1e10], [-(1-DF)*1e10, (1-DF)*1e10]).index
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'sgen', 'p_mw', sgen_index, 'res_line', 'p_from_mw', line_index, 
                #                     char_index, tol=0.0001, order=2)
                #                 pp.control.controller.characteristic_control.CharacteristicControl(self.power_model, 
                #                     'sgen', 'q_mvar', sgen_index, 'res_line', 'q_from_mvar', line_index, 
                #                     char_index, tol=0.0001, order=2)
                # Method 2: Calculate net diversity factor per load and calculate sgen power
                #   injection at each bus
                for e_code, element in self.base_elements.items():
                    if element.code == 'element_busbar':
                        gnode_bus =  self.network_model.gnode_element_mapping_inverted[e_code][0]
                        bus_index = self.power_nodes[gnode_bus]
                        DF_bus = self.network_model.gnode_df_mapping[gnode_bus]
                        loads = self.network_model.get_downstream_element(e_code, codes=misc.LOAD_ELEMENT_CODES)
                        if loads:
                            p_mw = 0
                            q_mvar = 0
                            for load_code in loads:
                                gnode_load = self.network_model.gnode_element_mapping_inverted[load_code][0]
                                path_gnodes = self.network_model.get_nodes_between_gnodes(gnode_bus, gnode_load)
                                path_gnodes.discard(gnode_bus)
                                DF_downstream = [self.network_model.gnode_df_mapping[gnode] for gnode in path_gnodes]
                                RF = np.prod(DF_downstream)*(1-DF_bus)
                                (loadcode, load_index) = self.power_elements[load_code]
                                if loadcode == 'load':
                                    p_mw += self.power_model['load']['p_mw'][load_index]*RF
                                    q_mvar += self.power_model['load']['q_mvar'][load_index]*RF
                                elif loadcode == 'asymmetric_load':
                                    p_mw += self.power_model['asymmetric_load']['p_a_mw'][load_index]*RF
                                    p_mw += self.power_model['asymmetric_load']['p_b_mw'][load_index]*RF
                                    p_mw += self.power_model['asymmetric_load']['p_c_mw'][load_index]*RF
                                    q_mvar += self.power_model['asymmetric_load']['q_a_mvar'][load_index]*RF
                                    q_mvar += self.power_model['asymmetric_load']['q_b_mvar'][load_index]*RF
                                    q_mvar += self.power_model['asymmetric_load']['q_c_mvar'][load_index]*RF
                            # Add phantom power injection element to take up balance power
                            sgen_index = pp.create_sgen(self.power_model, bus_index, 
                                p_mw=p_mw, q_mvar=q_mvar)
            pp.runpp(self.power_model, run_control=True, calculate_voltage_angles = True)

        # Data modification functions

        R = round

        def sum_func(x1,x2,x3, decimal): 
            result = x1 + x2 + x3
            return R(result, decimal)


        def percentage_1_1_func(a,b, decimal): 
            result = a/b*100 if abs(b)>1e-4 else 0
            return R(result, decimal)
        
        def percentage_3_3_func(x1,x2,x3,y1,y2,y3, decimal): 
            a = x1 + x2 + x3
            b = y1 + y2 + y3
            return percentage_1_1_func(a,b, decimal)

        def pf_1_1_func(p,q, decimal): 
            s = (p**2 + q**2)**0.5
            result = p/s if abs(s)>1e-4 else 0
            return R(result, decimal)

        def pf_3_3_func(pa,pb,pc,qa,qb,qc, decimal): 
            p = pa + pb + pc
            q = qa + qb + qc
            return pf_1_1_func(p,q, decimal)

        # Update nodes
        for bus_id, values in self.power_model.bus.iterrows():
            node = self.power_nodes_inverted[bus_id]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result

            if runpp_3ph:
                result = getattr(self.power_model, 'res_bus_3ph').loc[bus_id]
            else:
                result = getattr(self.power_model, 'res_bus').loc[bus_id]

            if runpp_3ph:
                min_v = min(result['vm_a_pu'], result['vm_b_pu'], result['vm_c_pu'])
                node_result['delv_perc_max'] = misc.get_field_dict(
                    'float', 'ΔV', '%', 100-min_v*100, decimal=2)
                node_result['delv_perc_a'] = misc.get_field_dict(
                    'float', 'ΔVa', '%', 100-result['vm_a_pu']*100, decimal=2)
                node_result['delv_perc_b'] = misc.get_field_dict(
                    'float', 'ΔVb', '%', 100-result['vm_b_pu']*100, decimal=2)
                node_result['delv_perc_c'] = misc.get_field_dict(
                    'float', 'ΔVc', '%', 100-result['vm_c_pu']*100, decimal=2)
            else:
                node_result['delv_perc_max'] = misc.get_field_dict(
                    'float', 'ΔV', '%', 100-result['vm_pu']*100, decimal=2)
                # node_result['vm_pu'] = misc.get_field_dict('float', 'V', 'pu', result['vm_pu'], decimal=3)
                # node_result['va_degree'] = misc.get_field_dict('float', 'V angle', 'degree', result['va_degree'], decimal=1)

        # Update elements
        for e_code, element in self.base_elements.items():
            if e_code in self.power_elements:
                # Create/get element dict
                if e_code in self.element_results:
                    element_result = self.element_results[e_code]
                else:
                    element_result = dict()
                    self.element_results[e_code] = element_result
                (elementcode, element_id) = self.power_elements[e_code]
                
                # Get result table
                if elementcode != 'switch':  # Remove elements without results
                    if runpp_3ph:
                        result = getattr(self.power_model, 'res_' +
                                        elementcode + '_3ph').loc[element_id]
                    else:
                        result = getattr(self.power_model, 'res_' +
                                        elementcode).loc[element_id]
                
                # Populate element results
                if runpp_3ph:
                    if elementcode in ['load', 'sgen', 'storage']:
                        element_result['p_mw'] = misc.get_field_dict(
                            'float', 'P', 'MW', R(result['p_mw'],4))
                        element_result['q_mvar'] = misc.get_field_dict(
                            'float', 'Q', 'MVAr', R(result['q_mvar'],4))
                        element_result['pf'] = misc.get_field_dict(
                            'float', 'PF', '', 
                            pf_1_1_func(result['p_mw'], result['q_mvar'], 2))
                    elif elementcode in ['ext_grid', 'asymmetric_load', 'asymmetric_sgen']:
                        element_result['p_mw'] = misc.get_field_dict('float', 'P', '', 
                            sum_func(result['p_a_mw'], result['p_b_mw'], result['p_c_mw'], 4))
                        element_result['pf'] = misc.get_field_dict('float', 'PF', '', 
                            pf_3_3_func(result['p_a_mw'], result['p_b_mw'], result['p_c_mw'], 
                                        result['q_a_mvar'], result['q_b_mvar'], result['q_c_mvar'], 2))
                        element_result['p_a_mw'] = misc.get_field_dict(
                            'float', 'Pa', 'MW', R(result['p_a_mw'],4))
                        element_result['p_b_mw'] = misc.get_field_dict(
                            'float', 'Pb', 'MW', R(result['p_b_mw'],4))
                        element_result['p_c_mw'] = misc.get_field_dict(
                            'float', 'Pc', 'MW', R(result['p_c_mw'],4))
                    elif elementcode == 'trafo':
                        element_result['p_hv_mw'] = misc.get_field_dict('float', 'P', 'MW', 
                            sum_func(result['p_a_hv_mw'], result['p_b_hv_mw'], result['p_c_hv_mw'], 4))
                        element_result['pf'] = misc.get_field_dict('float', 'PF', '', 
                            pf_3_3_func(result['p_a_hv_mw'], result['p_b_hv_mw'], result['p_c_hv_mw'], 
                                        result['q_a_hv_mvar'], result['q_b_hv_mvar'], result['q_c_hv_mvar'], 2))
                        element_result['loading_percent_max'] = misc.get_field_dict(
                            'float', '% Loading', '%', R(result['loading_percent'], 1))
                        element_result['pl_mw'] = misc.get_field_dict(
                            'float', 'P loss', 'MW', 
                            sum_func(result['p_a_l_mw'], result['p_b_l_mw'], result['p_c_l_mw'], 4))
                    elif elementcode == 'trafo3w':
                        element_result['p_hv_mw'] = misc.get_field_dict(
                            'float', 'P HV', 'MW', R(result['p_hv_mw'], 4))
                        element_result['q_hv_mvar'] = misc.get_field_dict(
                            'float', 'Q HV', 'MVAr', R(result['q_hv_mvar'], 4))
                        element_result['p_mv_mw'] = misc.get_field_dict(
                            'float', 'P MV', 'MW', R(result['p_mv_mw'], 4))
                        element_result['q_mv_mvar'] = misc.get_field_dict(
                            'float', 'Q MV', 'MVAr', R(result['q_mv_mvar'], 4))
                        element_result['p_lv_mw'] = misc.get_field_dict(
                            'float', 'P LV', 'MW', R(result['p_lv_mw'], 4))
                        element_result['q_lv_mvar'] = misc.get_field_dict(
                            'float', 'Q LV', 'MVAr', R(result['q_lv_mvar'], 4))
                        element_result['pl_mw'] = misc.get_field_dict(
                            'float', 'P loss', 'MW', R(result['pl_mw'], 4))
                        element_result['loading_percent_max'] = misc.get_field_dict(
                            'float', '% Loading', '%', R(result['loading_percent'], 1))
                    elif elementcode in ['line']:                        
                        element_result['p_from_mw'] = misc.get_field_dict('float', 'P', 'MW', 
                            sum_func(result['p_a_from_mw'], result['p_b_from_mw'], result['p_c_from_mw'], 4))
                        element_result['q_from_mvar'] = misc.get_field_dict('float', 'Q', 'MVAr', 
                            sum_func(result['q_a_from_mvar'], result['q_b_from_mvar'], result['q_c_from_mvar'], 4))
                        element_result['pf'] = misc.get_field_dict('float', 'PF', '', 
                            pf_3_3_func(result['p_a_from_mw'], result['p_b_from_mw'], result['p_c_from_mw'], 
                                        result['q_a_from_mvar'], result['q_b_from_mvar'], result['q_c_from_mvar'], 2))
                        element_result['p_a_from_mw'] = misc.get_field_dict(
                            'float', 'Pa', 'MW', R(result['p_a_from_mw'],4))
                        element_result['p_b_from_mw'] = misc.get_field_dict(
                            'float', 'Pb', 'MW', R(result['p_b_from_mw'],4))
                        element_result['p_c_from_mw'] = misc.get_field_dict(
                            'float', 'Pc', 'MW', R(result['p_c_from_mw'],4))
                        element_result['loading_percent_max'] = misc.get_field_dict(
                            'float', '% Loading', '%', R(result['loading_percent'], 1))
                        element_result['pl_mw_max'] = misc.get_field_dict('float', '% P Loss', '%', 
                            percentage_3_3_func(result['p_a_l_mw'], result['p_b_l_mw'], result['p_c_l_mw'],
                                                result['p_a_from_mw'], result['p_b_from_mw'], result['p_c_from_mw'], 1))
                else:
                    if elementcode in ['ext_grid', 'load', 'sgen', 'shunt', 'ward', 'xward', 'storage']:
                        element_result['p_mw'] = misc.get_field_dict(
                            'float', 'P', 'MW', R(result['p_mw'],4))
                        element_result['q_mvar'] = misc.get_field_dict(
                            'float', 'Q', 'MVAr', R(result['q_mvar'],4))
                        element_result['pf'] = misc.get_field_dict(
                            'float', 'PF', '', 
                            pf_1_1_func(result['p_mw'], result['q_mvar'], 2))
                    elif elementcode == 'trafo':
                        element_result['p_hv_mw'] = misc.get_field_dict(
                            'float', 'P', 'MW', R(result['p_hv_mw'], 4))
                        element_result['q_hv_mvar'] = misc.get_field_dict(
                            'float', 'Q', 'MVAr', R(result['q_hv_mvar'], 4))
                        element_result['pl_mw'] = misc.get_field_dict(
                            'float', 'P loss', 'MW', R(result['pl_mw'], 4))
                        element_result['loading_percent_max'] = misc.get_field_dict(
                            'float', '% Loading', '%', R(result['loading_percent'], 1))
                    elif elementcode == 'trafo3w':
                        element_result['p_hv_mw'] = misc.get_field_dict(
                            'float', 'P HV', 'MW', R(result['p_hv_mw'], 4))
                        element_result['q_hv_mvar'] = misc.get_field_dict(
                            'float', 'Q HV', 'MVAr', R(result['q_hv_mvar'], 4))
                        element_result['p_mv_mw'] = misc.get_field_dict(
                            'float', 'P MV', 'MW', R(result['p_mv_mw'], 4))
                        element_result['q_mv_mvar'] = misc.get_field_dict(
                            'float', 'Q MV', 'MVAr', R(result['q_mv_mvar'], 4))
                        element_result['p_lv_mw'] = misc.get_field_dict(
                            'float', 'P LV', 'MW', R(result['p_lv_mw'], 4))
                        element_result['q_lv_mvar'] = misc.get_field_dict(
                            'float', 'Q LV', 'MVAr', R(result['q_lv_mvar'], 4))
                        element_result['pl_mw'] = misc.get_field_dict(
                            'float', 'P loss', 'MW', R(result['pl_mw'], 4))
                        element_result['loading_percent_max'] = misc.get_field_dict(
                            'float', '% Loading', '%', R(result['loading_percent'], 1))
                    elif elementcode == 'gen':
                        element_result['p_mw'] = misc.get_field_dict(
                            'float', 'P', 'MW', R(result['p_mw'], 4))
                        element_result['q_mvar'] = misc.get_field_dict(
                            'float', 'Q', 'MVAr', R(result['q_mvar'], 4))
                        element_result['pf'] = misc.get_field_dict(
                            'float', 'PF', '', 
                            pf_1_1_func(result['p_mw'], result['q_mvar'], 2))
                        element_result['vm_pu'] = misc.get_field_dict(
                            'float', 'V', 'pu', R(result['vm_pu'], 2))
                        element_result['va_degree'] = misc.get_field_dict(
                            'float', 'V angle', 'degree', R(result['va_degree'], 1))
                    elif elementcode in ['impedance', 'dcline']:
                        element_result['p_from_mw'] = misc.get_field_dict(
                            'float', 'P', 'MW', R(result['p_from_mw'], 4))
                        element_result['q_from_mvar'] = misc.get_field_dict(
                            'float', 'Q', 'MVAr', R(result['q_from_mvar'], 4))
                        element_result['pl_mw'] = misc.get_field_dict(
                            'float', 'P loss', 'MW', R(result['pl_mw'], 4))
                    elif elementcode in ['line']:
                        element_result['p_from_mw'] = misc.get_field_dict(
                            'float', 'P', 'MW', R(result['p_from_mw'], 4))
                        element_result['q_from_mvar'] = misc.get_field_dict(
                            'float', 'Q', 'MW', R(result['q_from_mvar'], 4))
                        element_result['pf'] = misc.get_field_dict(
                            'float', 'PF', '', 
                            pf_1_1_func(result['p_from_mw'], result['q_from_mvar'], 2))
                        element_result['loading_percent_max'] = misc.get_field_dict(
                            'float', '% Loading', '%', R(result['loading_percent'], 1))
                        element_result['pl_mw_max'] = misc.get_field_dict(
                            'float', '% P Loss', '%', 
                            percentage_1_1_func(result['pl_mw'], result['p_from_mw'], 1))
        log.info('PandaPowerModel - run_powerflow - calculation run')

    def run_powerflow_timeseries(self, runpp_3ph=False):
        """Run power flow time series simulation"""
    
        sgens = self.power_model.sgen.to_dict(orient='records')
        asymmetric_sgens = self.power_model.asymmetric_sgen.to_dict(orient='records')
        loads = self.power_model.load.to_dict(orient='records')
        asymmetric_loads = self.power_model.asymmetric_load.to_dict(orient='records')
        dfdata_p = dict()
        dfdata_q = dict()
        dfdata_pa = dict()
        dfdata_pb = dict()
        dfdata_pc = dict()
        dfdata_qa = dict()
        dfdata_qb = dict()
        dfdata_qc = dict()
        n_ts = 24

        # Sgen controller
        for gen_index, values in enumerate(sgens):
            col_p = []
            col_q = []
            dfdata_p[gen_index] = col_p
            dfdata_q[gen_index] = col_q
            p_mw = values['p_mw']
            q_mvar = values['q_mvar']
            e_code = self.power_elements_inverted['sgen', gen_index]
            graph_uid = self.base_elements[e_code].fields['load_profile']['value']
            if graph_uid not in self.loadprofiles:
                graph_uid = list(self.loadprofiles.keys())[0]
            load_profile = self.loadprofiles[graph_uid][1][0]
            load_profile_func = GraphModel(load_profile).get_value_func()
            for time_index in range(n_ts):
                col_p.append(load_profile_func(time_index)*p_mw)
                col_q.append(load_profile_func(time_index)*q_mvar)
        df_p = pd.DataFrame(data=dfdata_p, index=list(
            range(n_ts)), columns=self.power_model.sgen.index)
        df_q = pd.DataFrame(data=dfdata_q, index=list(
            range(n_ts)), columns=self.power_model.sgen.index)
        ds_p = DFData(df_p)
        ds_q = DFData(df_q)
        const_sgen_p = control.ConstControl(self.power_model, element='sgen', element_index=self.power_model.sgen.index,
                                            variable='p_mw', data_source=ds_p, profile_name=self.power_model.sgen.index)
        const_sgen_q = control.ConstControl(self.power_model, element='sgen', element_index=self.power_model.sgen.index,
                                            variable='q_mvar', data_source=ds_q, profile_name=self.power_model.sgen.index)

        # Asymetric Sgen controller
        for gen_index, values in enumerate(asymmetric_sgens):
            col_pa = []
            col_pb = []
            col_pc = []
            col_qa = []
            col_qb = []
            col_qc = []
            dfdata_pa[gen_index] = col_pa
            dfdata_pb[gen_index] = col_pb
            dfdata_pc[gen_index] = col_pc
            dfdata_qa[gen_index] = col_qa
            dfdata_qb[gen_index] = col_qb
            dfdata_qc[gen_index] = col_qc
            pa_mw = values['p_a_mw']
            pb_mw = values['p_b_mw']
            pc_mw = values['p_c_mw']
            qa_mvar = values['q_a_mvar']
            qb_mvar = values['q_b_mvar']
            qc_mvar = values['q_c_mvar']
            e_code = self.power_elements_inverted['asymmetric_sgen', gen_index]
            graph_uid = self.base_elements[e_code].fields['load_profile']['value']
            if graph_uid not in self.loadprofiles:
                graph_uid = list(self.loadprofiles.keys())[0]
            load_profile = self.loadprofiles[graph_uid][1][0]
            load_profile_func = GraphModel(load_profile).get_value_func()
            for time_index in range(n_ts):
                col_pa.append(load_profile_func(time_index)*pa_mw)
                col_pb.append(load_profile_func(time_index)*pb_mw)
                col_pc.append(load_profile_func(time_index)*pc_mw)
                col_qa.append(load_profile_func(time_index)*qa_mvar)
                col_qb.append(load_profile_func(time_index)*qb_mvar)
                col_qc.append(load_profile_func(time_index)*qc_mvar)
        df_pa = pd.DataFrame(data=dfdata_pa, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_sgen.index)
        df_pb = pd.DataFrame(data=dfdata_pb, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_sgen.index)
        df_pc = pd.DataFrame(data=dfdata_pc, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_sgen.index)
        df_qa = pd.DataFrame(data=dfdata_qa, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_sgen.index)
        df_qb = pd.DataFrame(data=dfdata_qb, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_sgen.index)
        df_qc = pd.DataFrame(data=dfdata_qc, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_sgen.index)
        ds_pa = DFData(df_pa)
        ds_pb = DFData(df_pb)
        ds_pc = DFData(df_pc)
        ds_qa = DFData(df_qa)
        ds_qb = DFData(df_qb)
        ds_qc = DFData(df_qc)
        const_asgen_pa = control.ConstControl(self.power_model, element='asymmetric_sgen', 
                                            element_index=self.power_model.asymmetric_sgen.index,
                                            variable='p_a_mw', data_source=ds_pa, 
                                            profile_name=self.power_model.asymmetric_sgen.index)
        const_asgen_pb = control.ConstControl(self.power_model, element='asymmetric_sgen', 
                                            element_index=self.power_model.asymmetric_sgen.index,
                                            variable='p_b_mw', data_source=ds_pb, 
                                            profile_name=self.power_model.asymmetric_sgen.index)
        const_asgen_pc = control.ConstControl(self.power_model, element='asymmetric_sgen', 
                                            element_index=self.power_model.asymmetric_sgen.index,
                                            variable='p_c_mw', data_source=ds_pc, 
                                            profile_name=self.power_model.asymmetric_sgen.index)
        const_asgen_qa = control.ConstControl(self.power_model, element='asymmetric_sgen', 
                                            element_index=self.power_model.asymmetric_sgen.index,
                                            variable='q_a_mvar', data_source=ds_qa, 
                                            profile_name=self.power_model.asymmetric_sgen.index)
        const_asgen_qb = control.ConstControl(self.power_model, element='asymmetric_sgen', 
                                            element_index=self.power_model.asymmetric_sgen.index,
                                            variable='q_b_mvar', data_source=ds_qb, 
                                            profile_name=self.power_model.asymmetric_sgen.index)
        const_asgen_qc = control.ConstControl(self.power_model, element='asymmetric_sgen', 
                                            element_index=self.power_model.asymmetric_sgen.index,
                                            variable='q_c_mvar', data_source=ds_qc, 
                                            profile_name=self.power_model.asymmetric_sgen.index)
        # Load controller
        for load_index, values in enumerate(loads):
            col_p = []
            col_q = []
            dfdata_p[load_index] = col_p
            dfdata_q[load_index] = col_q
            p_mw = values['p_mw']
            q_mvar = values['q_mvar']
            e_code = self.power_elements_inverted['load', load_index]
            graph_uid = self.base_elements[e_code].fields['load_profile']['value']
            if graph_uid not in self.loadprofiles:
                graph_uid = list(self.loadprofiles.keys())[0]
            load_profile = self.loadprofiles[graph_uid][1][0]
            load_profile_func = GraphModel(load_profile).get_value_func()
            for time_index in range(n_ts):
                col_p.append(load_profile_func(time_index)*p_mw)
                col_q.append(load_profile_func(time_index)*q_mvar)
        df_p = pd.DataFrame(data=dfdata_p, index=list(
            range(n_ts)), columns=self.power_model.load.index)
        df_q = pd.DataFrame(data=dfdata_q, index=list(
            range(n_ts)), columns=self.power_model.load.index)
        ds_p = DFData(df_p)
        ds_q = DFData(df_q)
        const_load_p = control.ConstControl(self.power_model, element='load', element_index=self.power_model.load.index,
                                            variable='p_mw', data_source=ds_p, profile_name=self.power_model.load.index)
        const_load_q = control.ConstControl(self.power_model, element='load', element_index=self.power_model.load.index,
                                            variable='q_mvar', data_source=ds_q, profile_name=self.power_model.load.index)

        # Asymmetric Load controller
        for load_index, values in enumerate(asymmetric_loads):
            col_pa = []
            col_pb = []
            col_pc = []
            col_qa = []
            col_qb = []
            col_qc = []
            dfdata_pa[load_index] = col_pa
            dfdata_pb[load_index] = col_pb
            dfdata_pc[load_index] = col_pc
            dfdata_qa[load_index] = col_qa
            dfdata_qb[load_index] = col_qb
            dfdata_qc[load_index] = col_qc
            pa_mw = values['p_a_mw']
            pb_mw = values['p_b_mw']
            pc_mw = values['p_c_mw']
            qa_mvar = values['q_a_mvar']
            qb_mvar = values['q_b_mvar']
            qc_mvar = values['q_c_mvar']
            e_code = self.power_elements_inverted['asymmetric_load', load_index]
            graph_uid = self.base_elements[e_code].fields['load_profile']['value']
            if graph_uid not in self.loadprofiles:
                graph_uid = list(self.loadprofiles.keys())[0]
            load_profile = self.loadprofiles[graph_uid][1][0]
            load_profile_func = GraphModel(load_profile).get_value_func()
            for time_index in range(n_ts):
                col_pa.append(load_profile_func(time_index)*pa_mw)
                col_pb.append(load_profile_func(time_index)*pb_mw)
                col_pc.append(load_profile_func(time_index)*pc_mw)
                col_qa.append(load_profile_func(time_index)*qa_mvar)
                col_qb.append(load_profile_func(time_index)*qb_mvar)
                col_qc.append(load_profile_func(time_index)*qc_mvar)
        df_pa = pd.DataFrame(data=dfdata_pa, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_load.index)
        df_pb = pd.DataFrame(data=dfdata_pb, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_load.index)
        df_pc = pd.DataFrame(data=dfdata_pc, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_load.index)
        df_qa = pd.DataFrame(data=dfdata_qa, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_load.index)
        df_qb = pd.DataFrame(data=dfdata_qb, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_load.index)
        df_qc = pd.DataFrame(data=dfdata_qc, index=list(
            range(n_ts)), columns=self.power_model.asymmetric_load.index)
        ds_pa = DFData(df_pa)
        ds_pb = DFData(df_pb)
        ds_pc = DFData(df_pc)
        ds_qa = DFData(df_qa)
        ds_qb = DFData(df_qb)
        ds_qc = DFData(df_qc)
        const_load_pa = control.ConstControl(self.power_model, element='asymmetric_load', 
                                            element_index=self.power_model.asymmetric_load.index,
                                            variable='p_a_mw', data_source=ds_pa, 
                                            profile_name=self.power_model.asymmetric_load.index)
        const_load_pb = control.ConstControl(self.power_model, element='asymmetric_load', 
                                            element_index=self.power_model.asymmetric_load.index,
                                            variable='p_b_mw', data_source=ds_pb, 
                                            profile_name=self.power_model.asymmetric_load.index)
        const_load_pc = control.ConstControl(self.power_model, element='asymmetric_load', 
                                            element_index=self.power_model.asymmetric_load.index,
                                            variable='p_c_mw', data_source=ds_pc, 
                                            profile_name=self.power_model.asymmetric_load.index)
        const_load_qa = control.ConstControl(self.power_model, element='asymmetric_load', 
                                            element_index=self.power_model.asymmetric_load.index,
                                            variable='q_a_mvar', data_source=ds_qa, 
                                            profile_name=self.power_model.asymmetric_load.index)
        const_load_qb = control.ConstControl(self.power_model, element='asymmetric_load', 
                                            element_index=self.power_model.asymmetric_load.index,
                                            variable='q_b_mvar', data_source=ds_qb, 
                                            profile_name=self.power_model.asymmetric_load.index)
        const_load_qc = control.ConstControl(self.power_model, element='asymmetric_load', 
                                            element_index=self.power_model.asymmetric_load.index,
                                            variable='q_c_mvar', data_source=ds_qc, 
                                            profile_name=self.power_model.asymmetric_load.index)
        
        # Output writer
        # Elements
        time_steps = range(n_ts)
        log_variables = []
        if runpp_3ph:
            log_variables.append(('res_bus_3ph', 'vm_a_pu'))
            log_variables.append(('res_bus_3ph', 'vm_b_pu'))
            log_variables.append(('res_bus_3ph', 'vm_c_pu'))
        else:
            log_variables.append(('res_bus', 'vm_pu'))
        for e_code, element in self.base_elements.items():
            if e_code in self.power_elements:
                (elementcode, element_id) = self.power_elements[e_code]
                if runpp_3ph:
                    if elementcode in ['load', 'sgen', 'storage']:
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_mvar'))
                    elif elementcode in ['ext_grid', 'asymmetric_load', 'asymmetric_sgen']:
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_mvar'))
                    elif elementcode == 'trafo':
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_hv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_hv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_hv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_hv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_hv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_hv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_lv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_lv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_lv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_lv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_lv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_lv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_l_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_l_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_l_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_l_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_l_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_l_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'loading_percent'))
                    elif elementcode == 'trafo3w':
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_hv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_hv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_mv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_mv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_lv_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_lv_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'pl_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'ql_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'loading_percent'))
                    # elif elementcode in ['impedance',]:
                    #     log_variables.append(('res_'+elementcode, 'p_from_mw'))
                    #     log_variables.append(('res_'+elementcode, 'q_from_mvar'))
                    #     log_variables.append(('res_'+elementcode, 'p_to_mw'))
                    #     log_variables.append(('res_'+elementcode, 'q_to_mvar'))
                    #     log_variables.append(('res_'+elementcode, 'pl_mw'))
                    #     log_variables.append(('res_'+elementcode, 'ql_mvar'))
                    elif elementcode in ['line']:
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_from_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_from_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_to_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_to_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_a_l_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_a_l_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_from_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_from_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_to_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_to_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_b_l_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_b_l_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_from_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_from_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_to_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_to_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'p_c_l_mw'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'q_c_l_mvar'))
                        log_variables.append(('res_'+elementcode+'_3ph', 'loading_percent'))
                    # elif elementcode == 'gen':
                    #     log_variables.append(('res_'+elementcode, 'p_mw'))
                    #     log_variables.append(('res_'+elementcode, 'q_mvar'))
                    #     log_variables.append(('res_'+elementcode, 'vm_pu'))
                    #     log_variables.append(('res_'+elementcode, 'va_degree'))
                    # elif elementcode in ['dcline']:
                    #     log_variables.append(('res_'+elementcode, 'p_from_mw'))
                    #     log_variables.append(('res_'+elementcode, 'q_from_mvar'))
                    #     log_variables.append(('res_'+elementcode, 'p_to_mw'))
                    #     log_variables.append(('res_'+elementcode, 'q_to_mvar'))
                    #     log_variables.append(('res_'+elementcode, 'pl_mw'))
                    #     log_variables.append(('res_'+elementcode, 'ql_mvar'))
                else:
                    if elementcode in ['ext_grid', 'load', 'sgen', 'shunt', 'ward', 'xward', 'storage']:
                        log_variables.append(('res_'+elementcode, 'p_mw'))
                        log_variables.append(('res_'+elementcode, 'q_mvar'))
                    elif elementcode == 'trafo':
                        log_variables.append(('res_'+elementcode, 'p_hv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_hv_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_lv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_lv_mvar'))
                        log_variables.append(('res_'+elementcode, 'pl_mw'))
                        log_variables.append(('res_'+elementcode, 'ql_mvar'))
                        log_variables.append(
                            ('res_'+elementcode, 'loading_percent'))
                    elif elementcode == 'trafo3w':
                        log_variables.append(('res_'+elementcode, 'p_hv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_hv_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_mv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_mv_mvar'))
                        log_variables.append(('res_'+elementcode, 'p_lv_mw'))
                        log_variables.append(('res_'+elementcode, 'q_lv_mvar'))
                        log_variables.append(('res_'+elementcode, 'pl_mw'))
                        log_variables.append(('res_'+elementcode, 'ql_mvar'))
                        log_variables.append(
                            ('res_'+elementcode, 'loading_percent'))
                    elif elementcode == 'gen':
                        log_variables.append(('res_'+elementcode, 'p_mw'))
                        log_variables.append(('res_'+elementcode, 'q_mvar'))
                        log_variables.append(('res_'+elementcode, 'vm_pu'))
                        log_variables.append(('res_'+elementcode, 'va_degree'))
                    elif elementcode in ['impedance', 'dcline']:
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

        ow = OutputWriter(self.power_model, time_steps,
                          output_path=None, log_variables=log_variables)

        # Starting the timeseries simulation
        if runpp_3ph:
            timeseries.run_timeseries(self.power_model, time_steps=time_steps, run=pp.runpp_3ph)
        else:
            timeseries.run_timeseries(self.power_model, time_steps=time_steps)

        # Compile results

        def combine_graphdata(result, table, data, codes, combfunc, stat_fields=[]):
            codes_dict = dict()
            dst_code, element_id, caption, unit, decimal, modfunc = data
            for code in codes:
                values = []
                if runpp_3ph:
                    table_code = 'res_' + table + '_3ph.' + code
                else:
                    table_code = 'res_' + table + '.' + code
                for time_index in time_steps:
                    if modfunc:
                        value = modfunc(
                            ow.np_results[table_code][time_index][element_id])
                    else:
                        value = ow.np_results[table_code][time_index][element_id]
                    values.append(value)
                codes_dict[code] = values
            values_combined = combfunc(codes_dict)
            values_combined = list(np.round(values_combined, decimal))
            val_avg = round(sum(values_combined)/len(values_combined), decimal)
            val_max = round(max(values_combined), decimal)
            val_min = round(min(values_combined), decimal)
            delta = (val_max - val_min)*0.1
            ylimits = (val_min - delta, val_max + delta)
            title = '[{} | μ: {} | {}]'.format(val_min, val_avg, val_max)
            model = [{'mode': misc.GRAPH_DATATYPE_PROFILE,
                              'title': caption, 'xval': time_steps, 'yval': values_combined},]
            # Add combined graph
            graph_model = [title, model]
            result[dst_code] = misc.get_field_dict(
                'graph', caption, unit, graph_model, decimal=decimal)
            result[dst_code]['graph_options'] = (
                misc.GRAPH_LOAD_TIME_LIMITS, ylimits, 'Time (Hr)', caption + ' (' + unit + ')', {})
            # Add stats
            if 'avg' in stat_fields:
                subcode = dst_code + '_max'
                subcaption = caption + ' (avg)'
                result[subcode] = misc.get_field_dict(
                    'float', subcaption, unit, val_avg, decimal=decimal)
            if 'max' in stat_fields:
                subcode = dst_code + '_max'
                subcaption = caption + ' (max)'
                result[subcode] = misc.get_field_dict(
                    'float', subcaption, unit, val_max, decimal=decimal)
            if 'min' in stat_fields:
                subcode = dst_code + '_max'
                subcaption = caption + ' (min)'
                result[subcode] = misc.get_field_dict(
                    'float', subcaption, unit, val_min, decimal=decimal)
        
        def set_graphdata(result, table, data):
            model = []
            maintitle = ''
            maincaption = ''
            maincode = ''
            mainunit = ''
            ylimits_min = []
            ylimits_max = []
            for code, element_id, caption, unit, decimal, modfunc, modcode in data:
                values = []
                if runpp_3ph:
                    table_code = 'res_' + table + '_3ph.' + code
                else:
                    table_code = 'res_' + table + '.' + code
                for time_index in time_steps:
                    if modfunc:
                        value = modfunc(
                            ow.np_results[table_code][time_index][element_id])
                    else:
                        value = ow.np_results[table_code][time_index][element_id]
                    values.append(round(value, decimal))
                val_avg = round(sum(values)/len(values), decimal)
                val_max = round(max(values), decimal)
                val_min = round(min(values), decimal)
                delta = (val_max - val_min)*0.1
                title = caption + \
                    ': [{} | μ: {} | {}]'.format(
                        val_min, val_avg, val_max)
                ylimits_min.append(val_min - delta)
                ylimits_max.append(val_max + delta)

                model.append({'mode': misc.GRAPH_DATATYPE_PROFILE,
                              'title': caption, 'xval': time_steps, 'yval': values})
                maintitle += title + '\n'
                maincaption += caption + ', '
                mainunit += unit + ', '
                maincode += modcode + ','

            maintitle = maintitle.strip('\n') if len(
                data) > 1 else '[{} | μ: {} | {}]'.format(val_min, val_avg, val_max)
            maincaption = maincaption.strip(', ')
            mainunit = mainunit.strip(', ')
            maincode = maincode.strip(',')
            ylimits = (min(ylimits_min), max(ylimits_max), 0.1)
            graph_model = [maintitle, model]
            result[maincode] = misc.get_field_dict(
                'graph', maincaption, mainunit, graph_model, decimal=decimal)
            result[maincode]['graph_options'] = (
                misc.GRAPH_LOAD_TIME_LIMITS, ylimits, 'Time (Hr)', maincaption + ' (' + mainunit + ')', {})

        def set_graph_data_stats(result, table, data, fields=['avg']):
            model = []
            for (code, element_id, caption, unit, decimal, modfunc, modcode) in data:
                values = []
                if runpp_3ph:
                    table_code = 'res_' + table + '_3ph.' + code
                else:
                    table_code = 'res_' + table + '.' + code
                for time_index in time_steps:
                    if modfunc:
                        value = modfunc(
                            ow.np_results[table_code][time_index][element_id])
                    else:
                        value = ow.np_results[table_code][time_index][element_id]
                    values.append(value)

                if 'avg' in fields:
                    val_avg = round(sum(values)/len(values), decimal)
                    subcode = modcode + '_max'
                    subcaption = caption + ' (avg)'
                    result[subcode] = misc.get_field_dict(
                        'float', subcaption, unit, val_avg, decimal=decimal)
                if 'max' in fields:
                    val_max = round(max(values), decimal)
                    subcode = modcode + '_max'
                    subcaption = caption + ' (max)'
                    result[subcode] = misc.get_field_dict(
                        'float', subcaption, unit, val_max, decimal=decimal)
                if 'min' in fields:
                    val_min = round(min(values), decimal)
                    subcode = modcode + '_max'
                    subcaption = caption + ' (min)'
                    result[subcode] = misc.get_field_dict(
                        'float', subcaption, unit, val_min, decimal=decimal)
                    
        def modfunc(x): return 100-x*100

        def maxfunc(value_dict): 
            values_arr = np.array(list(value_dict.values()))
            result = np.max(np.abs(values_arr), axis=0)
            return list(result)
        
        def sumfunc(value_dict): 
            values_arr = np.array(list(value_dict.values()))
            result = np.sum(values_arr, axis=0)
            return list(result)
        
        def percentage_1_1_func(value_dict): 
            values = np.array(list(value_dict.values()))
            values1 = values[0:1,:]
            values2 = values[1:2,:]
            a = np.sum(values1, axis=0)
            b = np.sum(values2, axis=0)
            result = np.divide(a, b, out=np.zeros_like(a), where=(np.abs(b)>1e-8))*100
            return list(result)
        
        def percentage_3_3_func(value_dict): 
            values = np.array(list(value_dict.values()))
            values1 = values[0:3,:]
            values2 = values[3:6,:]
            a = np.sum(values1, axis=0)
            b = np.sum(values2, axis=0)
            result = np.divide(a, b, out=np.zeros_like(a), where=(np.abs(b)>1e-8))*100
            return list(result)

        def pf_1_1_func(value_dict): 
            values = np.array(list(value_dict.values()))
            values1 = values[0,:]
            values2 = values[1,:]
            p = np.abs(values1)
            q = np.array(values2)
            s = np.sqrt(p**2 + q**2)
            result = np.divide(p, s, out=np.ones_like(p), where=(np.abs(s)>1e-8))
            return list(result)

        def pf_3_3_func(value_dict): 
            values = np.array(list(value_dict.values()))
            values1 = values[0:3,:]
            values2 = values[3:6,:]
            p = np.abs(np.sum(values1, axis=0))
            q = np.sum(values2, axis=0)
            s = np.sqrt(p**2 + q**2)
            result = np.divide(p, s, out=np.ones_like(p), where=(np.abs(s)>1e-8))
            return list(result)

        # Update nodes
        for bus, node in self.power_nodes_inverted.items():
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result

            if runpp_3ph:
                set_graphdata(node_result, 'bus', [
                        ['vm_a_pu', bus, 'ΔVa', '%', 2, modfunc, 'delv_perc_a'],
                        ['vm_b_pu', bus, 'ΔVb', '%', 2, modfunc, 'delv_perc_b'],
                        ['vm_c_pu', bus, 'ΔVc', '%', 2, modfunc, 'delv_perc_c']])
                combine_graphdata(node_result, 'bus',
                    ['delv_perc', bus, 'ΔV', '%', 2, modfunc],
                    ['vm_a_pu', 'vm_b_pu', 'vm_c_pu'], maxfunc, stat_fields=['max'])
            else:
                set_graphdata(node_result, 'bus', [
                    ['vm_pu', bus, 'ΔV', '%', 2, modfunc, 'delv_perc']])
                set_graph_data_stats(node_result, 'bus', [
                    ['vm_pu', bus, 'ΔV', '%', 2, modfunc, 'delv_perc']], fields=['max'])

        # Update elements
        for e_code, element in self.base_elements.items():

            if e_code in self.power_elements:
                # Create/get element dict
                if e_code in self.element_results:
                    element_result = self.element_results[e_code]
                else:
                    element_result = dict()
                    self.element_results[e_code] = element_result
                (elementcode, element_id) = self.power_elements[e_code]

                # Populate element results
                if runpp_3ph:
                    if elementcode in ['load', 'sgen', 'storage']:
                        set_graphdata(element_result, elementcode, [['p_mw', element_id, 'P', 'MW', 4, None, 'p_mw'],
                                                                    ['q_mvar', element_id, 'Q', 'MVAr', 4, None, 'q_mvar']])
                        combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                            ['p_mw', 'q_mvar'], pf_1_1_func)
                    elif elementcode in ['ext_grid', 'asymmetric_load', 'asymmetric_sgen']:
                        combine_graphdata(element_result, elementcode, ['p_mw', element_id, 'P', 'MW', 4, None],
                            ['p_a_mw', 'p_b_mw', 'p_c_mw'], sumfunc, stat_fields=['avg', 'max'])
                        combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                            ['p_a_mw', 'p_b_mw', 'p_c_mw', 'q_a_mvar', 'q_b_mvar', 'q_c_mvar'], pf_3_3_func, stat_fields=['avg', 'min'])
                        set_graphdata(element_result, elementcode, [['p_a_mw', element_id, 'Pa', 'MW', 4, None, 'p_a_mw'],
                                                                    ['p_b_mw', element_id, 'Pb', 'MW', 4, None, 'p_b_mw'],
                                                                    ['p_c_mw', element_id, 'Pc', 'MW', 4, None, 'p_c_mw']])
                    elif elementcode == 'trafo':
                        combine_graphdata(element_result, elementcode, ['p_hv_mw', element_id, 'P', 'MW', 4, None],
                            ['p_a_hv_mw', 'p_b_hv_mw', 'p_c_hv_mw'], sumfunc, stat_fields=['avg', 'max'])
                        combine_graphdata(element_result, elementcode, ['pf_hv', element_id, 'PF', '', 2, None],
                            ['p_a_hv_mw', 'p_b_hv_mw', 'p_c_hv_mw', 'q_a_hv_mvar', 'q_b_hv_mvar', 'q_c_hv_mvar'], pf_3_3_func, stat_fields=['avg', 'min'])
                        set_graphdata(element_result, elementcode, [['p_a_hv_mw', element_id, 'Pa', 'MW', 4, None, 'p_a_hv_mw'],
                                                                    ['p_b_hv_mw', element_id, 'Pb', 'MW', 4, None, 'p_b_hv_mw'],
                                                                    ['p_c_hv_mw', element_id, 'Pc', 'MW', 4, None, 'p_c_hv_mw']])
                        set_graphdata(element_result, elementcode, [
                                    ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']])
                        set_graph_data_stats(element_result, elementcode, [
                            ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']], fields=['avg','max'])
                        combine_graphdata(element_result, elementcode, ['pl_mw', element_id, 'P Loss', 'MW', 4, None],
                            ['p_a_l_mw', 'p_b_l_mw', 'p_c_l_mw'], sumfunc, stat_fields=['max'])
                    elif elementcode == 'trafo3w':
                        set_graphdata(element_result, elementcode, [['p_hv_mw', element_id, 'P HV', 'MW', 4, None, 'p_hv_mw'],
                                                                    ['q_hv_mvar', element_id, 'Q HV', 'MVAr', 4, None, 'q_hv_mvar']])
                        set_graphdata(element_result, elementcode, [['p_mv_mw', element_id, 'P MV', 'MW', 4, None, 'p_mv_mw'],
                                                                    ['q_mv_mvar', element_id, 'Q MV', 'MVAr', 4, None, 'q_mv_mvar']])
                        set_graphdata(element_result, elementcode, [['p_lv_mw', element_id, 'P LV', 'MW', 4, None, 'p_lv_mw'],
                                                                    ['q_lv_mvar', element_id, 'Q LV', 'MVAr', 4, None, 'q_lv_mvar']])
                        set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None, 'pl_mw']])
                        set_graphdata(element_result, elementcode, [
                                    ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']])
                        set_graph_data_stats(element_result, elementcode, [
                            ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']], fields=['max'])
                    # elif elementcode == 'gen':
                    #     set_graphdata(element_result, elementcode, [['p_mw', element_id, 'P', 'MW', 4, None, 'p_mw'],
                    #                                                 ['q_mvar', element_id, 'Q', 'MVAr', 4, None, 'q_mvar']])
                    #     combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                    #         ['p_mw', 'q_mvar'], pf_1_1_func)
                    #     set_graphdata(element_result, elementcode, [
                    #                 ['vm_pu', element_id, 'V', 'pu', 3, None, 'vm_pu']])
                    #     set_graphdata(element_result, elementcode, [
                    #                 ['va_degree', element_id, 'V angle', 'degree', 1, None, 'va_degree']])
                    # elif elementcode in ['impedance', 'dcline']:
                    #     set_graphdata(element_result, elementcode, [['p_from_mw', element_id, 'P', 'MW', 4, None, 'p_from_mw']])
                    #     set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None, 'pl_mw']])
                    elif elementcode in ['line']:
                        combine_graphdata(element_result, elementcode, ['p_hv_mw', element_id, 'P', 'MW', 4, None],
                            ['p_a_from_mw', 'p_b_from_mw', 'p_c_from_mw'], sumfunc, stat_fields=['avg', 'max'])
                        combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                            ['p_a_from_mw', 'p_b_from_mw', 'p_c_from_mw', 'q_a_from_mvar', 'q_b_from_mvar', 'q_c_from_mvar'], pf_3_3_func, stat_fields=['avg', 'min'])
                        set_graphdata(element_result, elementcode, [['p_a_from_mw', element_id, 'Pa', 'MW', 4, None, 'p_a_from_mw'],
                                                                    ['p_b_from_mw', element_id, 'Pb', 'MW', 4, None, 'p_b_from_mw'],
                                                                    ['p_c_from_mw', element_id, 'Pc', 'MW', 4, None, 'p_c_from_mw']])
                        set_graphdata(element_result, elementcode, [['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']])
                        set_graph_data_stats(element_result, elementcode, [
                            ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']], fields=['avg','max'])
                        combine_graphdata(element_result, elementcode, ['pl_mw', element_id, '% P Loss', '%', 1, None],
                            ['p_a_l_mw', 'p_b_l_mw', 'p_c_l_mw', 'p_a_from_mw', 'p_b_from_mw', 'p_c_from_mw'], 
                            percentage_3_3_func, stat_fields=['max'])
                else:
                    if elementcode in ['ext_grid', 'load', 'sgen', 'shunt', 'ward', 'xward', 'storage']:
                        set_graphdata(element_result, elementcode, [['p_mw', element_id, 'P', 'MW', 4, None, 'p_mw'],
                                                                    ['q_mvar', element_id, 'Q', 'MVAr', 4, None, 'q_mvar']])
                        combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                            ['p_mw', 'q_mvar'], pf_1_1_func)
                    elif elementcode == 'trafo':
                        set_graphdata(element_result, elementcode, [['p_hv_mw', element_id, 'P', 'MW', 4, None, 'p_hv_mw'],
                                                                    ['q_hv_mvar', element_id, 'Q', 'MVAr', 4, None, 'q_hv_mvar']])
                        set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None, 'pl_mw']])
                        set_graphdata(element_result, elementcode, [
                                    ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']])
                        set_graph_data_stats(element_result, elementcode, [
                            ['loading_percent', element_id, '% Loading (max)', '%', 1, None, 'loading_percent']], fields=['max'])
                    elif elementcode == 'trafo3w':
                        set_graphdata(element_result, elementcode, [['p_hv_mw', element_id, 'P HV', 'MW', 4, None, 'p_hv_mw'],
                                                                    ['q_hv_mvar', element_id, 'Q HV', 'MVAr', 4, None, 'q_hv_mvar']])
                        set_graphdata(element_result, elementcode, [['p_mv_mw', element_id, 'P MV', 'MW', 4, None, 'p_mv_mw'],
                                                                    ['q_mv_mvar', element_id, 'Q MV', 'MVAr', 4, None, 'q_mv_mvar']])
                        set_graphdata(element_result, elementcode, [['p_lv_mw', element_id, 'P LV', 'MW', 4, None, 'p_lv_mw'],
                                                                    ['q_lv_mvar', element_id, 'Q LV', 'MVAr', 4, None, 'q_lv_mvar']])
                        set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None, 'pl_mw']])
                        set_graphdata(element_result, elementcode, [
                                    ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']])
                        set_graph_data_stats(element_result, elementcode, [
                            ['loading_percent', element_id, '% Loading (max)', '%', 1, None, 'loading_percent']], fields=['max'])
                    elif elementcode == 'gen':
                        set_graphdata(element_result, elementcode, [['p_mw', element_id, 'P', 'MW', 4, None, 'p_mw'],
                                                                    ['q_mvar', element_id, 'Q', 'MVAr', 4, None, 'q_mvar']])
                        combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                            ['p_mw', 'q_mvar'], pf_1_1_func)
                        set_graphdata(element_result, elementcode, [
                                    ['vm_pu', element_id, 'V', 'pu', 3, None, 'vm_pu']])
                        set_graphdata(element_result, elementcode, [
                                    ['va_degree', element_id, 'V angle', 'degree', 1, None, 'va_degree']])
                    elif elementcode in ['impedance', 'dcline']:
                        set_graphdata(element_result, elementcode, [['p_from_mw', element_id, 'P', 'MW', 4, None, 'p_from_mw']])
                        set_graphdata(element_result, elementcode, [['pl_mw', element_id, 'P loss', 'MW', 4, None, 'pl_mw']])
                    elif elementcode in ['line']:
                        set_graphdata(element_result, elementcode, [['p_from_mw', element_id, 'P', 'MW', 4, None, 'p_from_mw']])
                        combine_graphdata(element_result, elementcode, ['pf', element_id, 'PF', '', 2, None],
                            ['p_from_mw', 'q_from_mvar'], pf_1_1_func)
                        set_graphdata(element_result, elementcode, [
                                    ['loading_percent', element_id, '% Loading', '%', 1, None, 'loading_percent']])
                        set_graph_data_stats(element_result, elementcode, [
                            ['loading_percent', element_id, '% Loading (max)', '%', 1, None, 'loading_percent']], fields=['max'])
                        combine_graphdata(element_result, elementcode, ['pl_mw', element_id, '% P Loss', '%', 1, None],
                            ['pl_mw', 'p_from_mw'], percentage_1_1_func, stat_fields=['max'])

        log.info('PandaPowerModel - run_powerflow - calculation run')

    def run_sym_sccalc(self, lv_tol_percent=6, r_fault_ohm=0.0, x_fault_ohm=0.0):
        """Run symmetric short circuit calculation"""

        sc.calc_sc(self.power_model_lf, fault='3ph', case='max', lv_tol_percent=lv_tol_percent,
                   check_connectivity=True, r_fault_ohm=r_fault_ohm, x_fault_ohm=x_fault_ohm)
        res_3ph_max = self.power_model_lf.res_bus_sc.to_dict()
        sc.calc_sc(self.power_model_lf, fault='3ph', case='min', lv_tol_percent=lv_tol_percent,
                   check_connectivity=True, r_fault_ohm=r_fault_ohm, x_fault_ohm=x_fault_ohm)
        res_3ph_min = self.power_model_lf.res_bus_sc.to_dict()

        # Update nodes
        for bus in res_3ph_max['ikss_ka']:
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            node_result['ikss_ka_3ph_max'] = misc.get_field_dict(
                'float', 'Isc (sym, max)', 'kA', res_3ph_max['ikss_ka'][bus], decimal=2)
            node_result['ikss_ka_3ph_min'] = misc.get_field_dict(
                'float', 'Isc (sym, min)', 'kA', res_3ph_min['ikss_ka'][bus], decimal=2)

        log.info('PandaPowerModel - run_sym_sccalc - calculation run')

    def run_linetoground_sccalc(self, lv_tol_percent=6, r_fault_ohm=0.0, x_fault_ohm=0.0):
        """Run line to ground short circuit calculation"""

        sc.calc_sc(self.power_model_gf, fault='1ph', case='max', lv_tol_percent=lv_tol_percent,
                   check_connectivity=True, r_fault_ohm=r_fault_ohm, x_fault_ohm=x_fault_ohm)
        res_1ph_max = self.power_model_gf.res_bus_sc.to_dict()
        sc.calc_sc(self.power_model_gf, fault='1ph', case='min', lv_tol_percent=lv_tol_percent,
                   check_connectivity=True, r_fault_ohm=r_fault_ohm, x_fault_ohm=x_fault_ohm)
        res_1ph_min = self.power_model_gf.res_bus_sc.to_dict()

        # Update nodes
        for bus in res_1ph_max['ikss_ka']:
            node = self.power_nodes_inverted[bus]
            if node in self.node_results:
                node_result = self.node_results[node]
            else:
                node_result = dict()
                self.node_results[node] = node_result
            node_result['ikss_ka_1ph_max'] = misc.get_field_dict(
                'float', 'Isc (L-G, max)', 'kA', res_1ph_max['ikss_ka'][bus], decimal=2)
            node_result['ikss_ka_1ph_min'] = misc.get_field_dict(
                'float', 'Isc (L-G, min)', 'kA', res_1ph_min['ikss_ka'][bus], decimal=2)

        log.info('PandaPowerModel - run_linetoground_sccalc - calculation run')

    def update_results(self):
        # Copy node data to element power model
        for e_code, element in self.base_elements.items():

            if e_code in self.power_elements:
                # Create/get element dict
                if e_code in self.element_results:
                    element_result = self.element_results[e_code]
                else:
                    element_result = dict()
                    self.element_results[e_code] = element_result
                (elementcode, element_id) = self.power_elements[e_code]

                # Add node related data to elements
                if element.code in misc.PROTECTION_ELEMENT_CODES + misc.DAMAGE_ELEMENT_CODES:
                    if element.code not in misc.TRAFO_ELEMENT_CODES:
                        lnode = element.get_nodes(str(e_code))[0][0]
                        gnode = self.node_mapping[lnode]
                        node_result = self.node_results[gnode]
                        if 'vn_kv' in node_result:
                            field = node_result['vn_kv']
                            element_result['vn_kv'] = copy.deepcopy(field)

            elif element.code == 'element_busbar':
                # Create/get element dict
                if e_code in self.element_results:
                    element_result = self.element_results[e_code]
                else:
                    element_result = dict()
                    self.element_results[e_code] = element_result
                lnode = element.get_nodes(str(e_code))[0][0]
                gnode = self.node_mapping[lnode]
                node_result = self.node_results[gnode]
                for code, field in node_result.items():
                    element_result[code] = copy.deepcopy(field)

        # Update element with power model
        for e_code, element in self.base_elements.items():
            if e_code in self.element_results:
                element_result = self.element_results[e_code]
                element.res_fields = element_result
        log.info('PandaPowerModel - update_results - results updated')

    # Export/Import functions

    def export_html_report(self, filename):
        pplot.to_html(self.power_model, filename)

    def export_json(self, filename):
        pp.to_json(self.power_model, filename)
