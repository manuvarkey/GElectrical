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

import logging, copy, datetime
from gi.repository import Gtk, Gdk
import cairo

import networkx as nx
from networkx.algorithms.components.connected import connected_components

# local files import
from .. import misc

# Get logger object
log = logging.getLogger(__name__)


class NetworkModel:
    """Class for modelling a Network"""
    
    def __init__(self, drawing_models):
        # Data
        self.drawing_models = drawing_models
        
        # Generated
        self.global_nodes = set()  # Unique global node values after collapsing buses
        self.virtual_global_nodes = set()
        self.base_elements = dict()  # Addressing by (page, slno)
        self.gnode_element_mapping = dict()  # Maps global_node -> [element1, ..]
        self.gnode_element_mapping_inverted = dict()  # Maps element -> [global_node1, ..]
        self.node_mapping = dict()  # Maps local_node -> global_node i.e. ('(page,element):port') -> global_node
        self.port_mapping = dict()  # Maps (page,x,y) -> global_node
        self.port_mapping_inverted = dict()  # Maps global_node -> (page,x,y)
        
        # Graph variables
        self.graph = None
    
    ## Analysis functions
    
    def setup_base_elements(self):
        # Populate self.base_elements
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                self.base_elements[(k1,k2)] = element
    
    def setup_global_nodes(self):
        """Build network model from drawing sheets"""
        
        duplicate_ports_list = []
        cur_gnode_num = 0
        
        # Populate self.port_mapping, self.port_mapping_inverted, self.virtual_global_nodes
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str((k1,k2))
                nodes = element.get_nodes(code)
                for (p0, ports) in nodes:
                    gnode = cur_gnode_num
                    self.port_mapping_inverted[gnode] = set()
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
                            self.port_mapping_inverted[gnode].add(map_port)
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
            self.port_mapping_inverted[gnode] = set()
            for port in duplicate_ports:
                self.port_mapping[port] = gnode
                self.port_mapping_inverted[gnode].add(port)
            cur_gnode_num += 1
            
        # Populate self.node_mapping, self.global_nodes, self.gnode_element_mapping, self.gnode_element_mapping_inverted
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str((k1,k2))
                nodes = element.get_nodes(code)
                self.gnode_element_mapping_inverted[(k1,k2)] = []
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
                    if gnode in self.gnode_element_mapping:
                        self.gnode_element_mapping[gnode].append((k1,k2))
                    else:
                        self.gnode_element_mapping[gnode] = [(k1,k2)]
                    self.gnode_element_mapping_inverted[(k1,k2)].append(gnode)
                        
                    
        log.info('NetworkModel - setup_base_model - model generated')
        
        
    def build_graph_model(self):
        """Build graph model for network"""
        log.info('NetworkModel - build_graph - model generated')
        
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
