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

import logging, json
import networkx as nx
from networkx.algorithms.components.connected import connected_components
from html import escape

# local files import
from .. import misc

# Get logger object
log = logging.getLogger(__name__)


class Raw(object):
    def __init__(self, html):
        self.html = html

class Tag(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, *args, **kwargs):
        attr = ' ' + ' '.join('%s="%s"' % (k, escape(v)) for k, v in kwargs.items())
        contents = ''.join(a.html if isinstance(a, Raw) else escape(str(a)) for a in args)
        return Raw('<%s%s>%s</%s>' % (self.name, attr.rstrip(), contents, self.name))


class NetworkModel:
    """Class for modelling a Network"""

    START_GNODE = -1
    END_GNODE = -2

    def __init__(self, drawing_models):
        # Data
        self.drawing_models = drawing_models

        # Generated
        self.base_elements = dict()  # Addressing by (page, slno)
        self.global_nodes = set()  # Unique global node values after collapsing buses
        self.virtual_global_nodes = set()
        self.gnode_element_mapping = dict()  # Maps global_node -> [element1, ..]
        self.gnode_element_mapping_inverted = dict()  # Maps element -> [global_node1, ..]
        self.node_mapping = dict()  # Maps local_node -> global_node i.e. ('(page,element):port') -> global_node
        self.port_mapping = dict()  # Maps (page,x,y) -> global_node
        self.port_mapping_inverted = dict()  # Maps global_node -> (page,x,y)

        # Graph variables
        self.graph = None

    # Analysis functions

    def setup_base_elements(self):
        # Populate self.base_elements
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                self.base_elements[(k1, k2)] = element

    def setup_global_nodes(self):
        """Build network model from drawing sheets"""

        duplicate_ports_list = []
        cur_gnode_num = 1
        cur_vnode_num = 1

        # Populate self.port_mapping, self.virtual_global_nodes
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str((k1, k2))
                nodes = element.get_nodes(code)
                for (p0, ports) in nodes:
                    gnode = cur_gnode_num
                    duplicate_ports = set()
                    if ports:
                        for port in ports:
                            # Get port in global coordinates
                            if len(port) == 2:
                                # If same page port ref add page number
                                map_port = (k1, *port)
                            else:
                                map_port = port
                            # Populate data
                            self.port_mapping[map_port] = gnode
                            if len(ports) > 1:
                                duplicate_ports.add(map_port)
                        if len(ports) > 1:
                            duplicate_ports_list.append(duplicate_ports)
                        cur_gnode_num += 1
                    else:
                        self.virtual_global_nodes.add(cur_vnode_num)
                        cur_vnode_num += 1
                        
        # Filter duplicates in self.port_mapping
        duplicate_ports_list_comb = self.combine_connected_nodes(duplicate_ports_list)
        for duplicate_ports in duplicate_ports_list_comb:
            gnode = cur_gnode_num
            for port in duplicate_ports:
                self.port_mapping[port] = gnode
            cur_gnode_num += 1

        # Renumber gnodes to avoid gaps in numbering
        port_mapping_mod = dict()
        gnodes = set(self.port_mapping.values())
        subs_dict = {gnode:new_gnode for new_gnode, gnode in enumerate(sorted(gnodes), start=1)}
        port_mapping_mod = {key:subs_dict[value] for key, value in self.port_mapping.items()}
        self.port_mapping = port_mapping_mod
        self.global_nodes = gnodes

        # Populate self.port_mapping_inverted
        for eid, gnode in self.port_mapping.items():
            if gnode not in self.port_mapping_inverted:
                self.port_mapping_inverted[gnode] = set()
            self.port_mapping_inverted[gnode].add(eid)

        # Populate self.node_mapping, self.gnode_element_mapping, self.gnode_element_mapping_inverted
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                code = str((k1, k2))
                nodes = element.get_nodes(code)
                self.gnode_element_mapping_inverted[(k1, k2)] = []
                # Add nodes
                for (p0, ports) in nodes:
                    port = ports[0]
                    # Get port in global coordinates
                    if len(port) == 2:
                        # If same page port ref add page number
                        map_port = (k1, *port)
                    else:
                        map_port = port
                    gnode = self.port_mapping[map_port]
                    self.node_mapping[p0] = gnode
                    if gnode in self.gnode_element_mapping:
                        self.gnode_element_mapping[gnode].append((k1, k2))
                    else:
                        self.gnode_element_mapping[gnode] = [(k1, k2)]
                    self.gnode_element_mapping_inverted[(k1, k2)].append(gnode)

        log.info('NetworkModel - setup_base_model - model generated')

    def build_graph_model(self):
        """Build graph model for network"""
        self.graph = nx.Graph()
        for ecode, element in self.base_elements.items():
            code = element.code
            if code not in misc.NON_ELEMENT_CODES:
                if 'ref' in element.fields:
                    ref = element.fields['ref']['value']
                else:
                    ref = ''
                gnodes = self.gnode_element_mapping_inverted[ecode]
                # Single port elements
                if len(gnodes) == 1:
                    if code in misc.SUPPLY_ELEMENT_CODES:
                        self.graph.add_edge(self.START_GNODE, gnodes[0], key=ecode, code=code, ref=ref)
                    else:
                        self.graph.add_edge(gnodes[0], self.END_GNODE, key=ecode, code=code, ref=ref)
                # Two port elements:
                elif len(gnodes) == 2:
                    self.graph.add_edge(gnodes[0], gnodes[1], key=ecode, code=code, ref=ref)
                # Three port elements:
                elif len(gnodes) == 3:
                    self.graph.add_edge(gnodes[0], gnodes[1], key=ecode, code=code, ref=ref)
                    self.graph.add_edge(gnodes[0], gnodes[2], key=ecode, code=code, ref=ref)
        log.info('NetworkModel - build_graph - model generated')

    def export_element_graph_matplotlib(self, filename):
        import matplotlib
        import matplotlib.pyplot as plt
        matplotlib.use('Agg')
        figure = plt.figure()
        ax = figure.add_subplot(111)
        pos = nx.spring_layout(self.graph)
        nx.draw_networkx(self.graph, pos, ax=ax)
        edge_labels=dict([((n1, n2), d['ref']) for n1, n2, d in self.graph.edges(data=True)])
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels, ax=ax)
        figure.savefig(filename)

    def export_element_graph_html(self, filename):
        HTML, HEAD, STYLE, BODY, DIV = Tag('html'), Tag('head'), Tag('style'), Tag('body'), Tag('div')
        TABLE, TR, TH, TD, SCRIPT = Tag('table'), Tag('tr'), Tag('th'), Tag('td'), Tag('script')
        H2 = Tag('h2')
        # Style and headers
        style = 'tr:first {background:#e1e1e1;} th,td {text-align:center; border:1px solid #e1e1e1;}'
        nodes = [{'id': int(x), 'label': str(x)} for x in self.graph.nodes]
        edges = [{'from':  int(x), 'to':  int(y), 'label': d['ref']} for (x,y,d) in self.graph.edges(data=True)]
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        script = "var data = {nodes: new vis.DataSet(%s), edges: new vis.DataSet(%s)};" % (nodes_json, edges_json)
        script += "var container = document.getElementById('net');"
        script += "var network = new vis.Network(container, data);"
        script += "network.setOptions({interaction: {zoomView: true}});"
        page = HTML(
            HEAD(STYLE(style)),
            BODY(DIV(id='net', style="border:1px solid #f1f1f1;max-width:90%")),
            SCRIPT(src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.18.1/vis.min.js"),
            SCRIPT(Raw(script))
            )
        with open(filename, 'w') as fp:
            fp.write(page.html)

    # Private functions

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
