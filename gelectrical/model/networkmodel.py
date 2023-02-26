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

import logging, json, itertools, copy
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

    def __init__(self, program_state):
        # Data
        self.program_state = program_state
        self.drawing_models = self.program_state['project'].drawing_models

        # Generated
        self.base_elements = dict()  # Addressing by (page, slno)
        self.node_elements = dict()  # Addressing by (page, global_node)
        self.node_elements_bygnode = dict()  # (page, global_node) -> (node_element1, node_element2)
        self.global_nodes = set()  # Unique global node values after collapsing buses
        self.virtual_global_nodes = set()
        self.gnode_element_mapping = dict()  # Maps global_node -> [element1, ..]
        self.gnode_element_mapping_inverted = dict()  # Maps element -> [global_node1, ..]
        self.node_mapping = dict()  # Maps local_node -> global_node i.e. ('(page,element):port') -> global_node
        self.port_mapping = dict()  # Maps (page,x,y) -> global_node
        self.port_mapping_inverted = dict()  # Maps global_node -> (page,x,y)

        # Graph data structures
        # Graph of network elements as edges and gnodes as nodes
        # Sources start from self.START_GNODE
        # Loads terminate in self.END_GNODE
        self.graph = None
        self.graph_with_status = None
        self.graph_source_nodes = set()
        self.graph_source_nodes_with_status = set()
        self.graph_sink_nodes = set()

    # Build models

    def setup_base_elements(self):
        """Populate self.base_elements"""
        self.base_elements = dict()
        for k1, drawing_model in enumerate(self.drawing_models):
            for k2, element in enumerate(drawing_model.elements):
                self.base_elements[(k1, k2)] = element
        log.info('NetworkModel - setup_base_model - model generated')

    def setup_global_nodes(self):
        """Build network model from drawing sheets"""

        self.global_nodes = set()
        self.virtual_global_nodes = set()
        self.gnode_element_mapping = dict()
        self.gnode_element_mapping_inverted = dict()
        self.node_mapping = dict()
        self.port_mapping = dict()
        self.port_mapping_inverted = dict()

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
        self.global_nodes = set(subs_dict.values())

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

        log.info('NetworkModel - setup_global_nodes - updated')

    def setup_node_elements(self):
        """Populate self.node_elements"""
        self.node_elements = dict()
        self.node_elements_bygnode = dict()

        for k1, drawing_model in enumerate(self.drawing_models):
            page_gnodes = set()
            # Prepare node elements
            for k2, element in enumerate(drawing_model.elements):
                gnodes = self.gnode_element_mapping_inverted[(k1,k2)]
                for gnode in gnodes:
                    if gnode not in page_gnodes:
                        ref = str(gnode)
                        # Select a port with coordinates (i.e. exclude reference ports)
                        port = None
                        for eport in self.port_mapping_inverted[gnode]:
                            if len(eport) == 3 and eport[0] == k1:
                                port = eport
                                break
                        if port:
                            DisplayElementNode = self.program_state['element_models']['element_display_node']
                            node_element = DisplayElementNode(port[1:], ref)
                            self.node_elements[(k1, gnode)] = node_element
                            if gnode not in self.node_elements_bygnode:
                                self.node_elements_bygnode[gnode] = []
                            self.node_elements_bygnode[gnode].append(node_element)
                            page_gnodes.add(gnode)
        log.info('NetworkModel - setup_base_model - model generated')
        return self.node_elements

    def build_graph_model(self):
        """Build graph model for network"""
        self.graph = nx.Graph()
        self.graph_source_nodes = set()
        self.graph_source_nodes_with_status = set()
        self.graph_sink_nodes = set()

        disabled_sources = []
        disabled_sources_edges = []
        disabled_lines = []
        disabled_switches = []
        if self.global_nodes:
            term_node_count = max(self.global_nodes) + 1
        else:
            term_node_count = 1
        for ekey, element in self.base_elements.items():
            code = element.code
            if code not in (*misc.NON_ELEMENT_CODES, 'element_busbar'):
                if 'ref' in element.fields:
                    ref = element.fields['ref']['value']
                else:
                    ref = ''
                gnodes = self.gnode_element_mapping_inverted[ekey]
                if code in misc.LINE_ELEMENT_CODES and element.fields['in_service']['value'] == False:
                    disabled_lines.append(gnodes)
                if code in misc.SWITCH_ELEMENT_CODES and element.fields['closed']['value'] == False:
                    disabled_switches.append(gnodes)
                # Single port elements
                if len(gnodes) == 1:
                    if code in misc.SUPPLY_ELEMENT_CODES:
                        self.graph.add_edge(term_node_count, gnodes[0], key=ekey, code=code, ref=ref)
                        self.graph_source_nodes.add(term_node_count)
                        if element.fields['in_service']['value'] == False:
                            disabled_sources.append(term_node_count)
                            disabled_sources_edges.append((term_node_count, gnodes[0]))
                        term_node_count += 1
                    else:
                        self.graph.add_edge(gnodes[0], term_node_count, key=ekey, code=code, ref=ref)
                        self.graph_sink_nodes.add(term_node_count)
                        term_node_count += 1
                # Two port elements:
                elif len(gnodes) == 2:
                    self.graph.add_edge(gnodes[0], gnodes[1], key=ekey, code=code, ref=ref)
                # Three port elements:
                elif len(gnodes) == 3:
                    self.graph.add_edge(gnodes[0], gnodes[1], key=ekey, code=code, ref=ref)
                    self.graph.add_edge(gnodes[0], gnodes[2], key=ekey, code=code, ref=ref)
        # Update self.graph_with_status
        self.graph_with_status = self.graph.copy()
        self.graph_with_status.remove_edges_from(disabled_lines)
        self.graph_with_status.remove_edges_from(disabled_switches)
        self.graph_with_status.remove_edges_from(disabled_sources_edges)
        self.graph_source_nodes_with_status = copy.copy(self.graph_source_nodes)
        self.graph_source_nodes_with_status -= set(disabled_sources)
        log.info('NetworkModel - build_graph - model generated')

    # Graph analysis functions

    def get_upstream_nodes(self, ekey, source_node=None, ignore_disabled=True):
        # Select graph
        if ignore_disabled:
            graph = self.graph_with_status
            graph_source_nodes = self.graph_source_nodes_with_status
        else:
            graph = self.graph
            graph_source_nodes = self.graph_source_nodes
        # Setup
        gnodes = self.gnode_element_mapping_inverted[ekey]
        g0 = gnodes[0]
        result = set()
        # Search in a path from g0 to selected sources
        search_set = [source_node] if source_node else graph_source_nodes
        for source in search_set:
            simple_paths = nx.all_simple_paths(graph, g0, source)
            paths_comb = set(itertools.chain(*simple_paths))
            result = result | paths_comb
        # If upstream nodes do not include selected gnode, remove gnode from set
        adj_nodes_g0 = set(graph.adj[g0]) - set(gnodes)
        if result and not adj_nodes_g0:  # If adj nodes of g0 is null
            result.remove(g0)
        return result

    def get_upstream_element(self, ekey, codes=None, ignore_disabled=True):
        # Select graph
        if ignore_disabled:
            graph = self.graph_with_status
            graph_source_nodes = self.graph_source_nodes_with_status
        else:
            graph = self.graph
            graph_source_nodes = self.graph_source_nodes
        # Setup
        gnodes = self.gnode_element_mapping_inverted[ekey]
        element = self.base_elements[ekey]
        results = dict()
        # If source node, return null
        if element.code in misc.SUPPLY_ELEMENT_CODES:
            return results
        # Search in a path from g0 to all sources
        for source in graph_source_nodes:
            simple_paths = nx.all_simple_paths(graph, gnodes[0], source)
            for path in map(nx.utils.pairwise, simple_paths):  # For all elements in path
                for e_pair in path:
                    ekey_check = graph.edges[e_pair[0], e_pair[1]]['key']
                    element_check = self.base_elements[ekey_check]
                    # Case 1 - 1 node load elements; break as cannot be upstream
                    if set(e_pair) & self.graph_sink_nodes:
                        break
                    # Case 2 - 1 node supply elements; no need to check if current element
                    elif set(e_pair) & graph_source_nodes:
                        if (codes is None) or (element_check.code in codes):
                            results[ekey_check] = element_check
                            break
                    # Case 3 - 2+ node elements; check if same as current element
                    elif not set(e_pair).issubset(set(gnodes)):
                        if (codes is None) or (element_check.code in codes):
                            results[ekey_check] = element_check
                            break
        return results

    def get_downstream_element(self, ekey, codes=None, ignore_disabled=True):
        # Select graph
        if ignore_disabled:
            graph = self.graph_with_status
            graph_source_nodes = self.graph_source_nodes_with_status
        else:
            graph = self.graph
            graph_source_nodes = self.graph_source_nodes
        # Setup
        gnodes = self.gnode_element_mapping_inverted[ekey]
        element = self.base_elements[ekey]
        results = dict()
        # If load node, return null
        if len(gnodes) == 1 and element.code not in misc.SUPPLY_ELEMENT_CODES:
            return results
        # Search in sink paths by excluding each path to source
        for source in graph_source_nodes:
            # If source element is selected, do not exclude upstream nodes
            if element.code in misc.SUPPLY_ELEMENT_CODES:
                upstream_nodes = set()
                start_gnodes = [gnodes[0]]
            else:
                upstream_nodes = self.get_upstream_nodes(ekey, source_node=source, ignore_disabled=ignore_disabled)
                if not upstream_nodes:  # If upstream nodes in null, skip source for calculation
                    continue
                # Select start nodes from nodes not in upstream_nodes
                start_gnodes = [gnode for gnode in gnodes if gnode not in upstream_nodes]
            for start_gnode in start_gnodes:
                simple_paths = nx.all_simple_paths(graph, start_gnode, self.graph_sink_nodes)
                for path in map(nx.utils.pairwise, simple_paths):
                    path_it1, path_it2 =  itertools.tee(path, 2)
                    path_nodes = set(itertools.chain(*path_it1))
                    # If path shares nodes with upstream skip path
                    if not(path_nodes & upstream_nodes):
                        for e_pair in path_it2:
                            ekey_check = graph.edges[e_pair[0], e_pair[1]]['key']
                            element_check = self.base_elements[ekey_check]
                            # Case 1 - 1 node source elements; break as cannot be downstream
                            if set(e_pair) & graph_source_nodes:
                                break
                            # Case 2 - 1 node load elements; no need to check if current element
                            elif set(e_pair) & self.graph_sink_nodes:
                                if (codes is None) or (element_check.code in codes):
                                    results[ekey_check] = element_check
                                    break
                            # Case 3 - 2+ node elements; check if same as current element
                            elif not set(e_pair).issubset(set(gnodes)):
                                # Add element and break path if <codes not specified> or <code matches>
                                if (codes is None) or (element_check.code in codes):
                                    results[ekey_check] = element_check
                                    break
        return results

    def get_upstream_node_of_element(self, ekey, ignore_disabled=True):
        gnodes = set(self.gnode_element_mapping_inverted[ekey])
        results = dict()
        if len(gnodes) == 1:
            upstream_nodes_element = gnodes
        else:
            upstream_nodes = self.get_upstream_nodes(ekey, ignore_disabled=ignore_disabled)
            upstream_nodes_element = upstream_nodes & gnodes
        for gnode in upstream_nodes_element:
            key = (ekey[0], gnode)
            if key in self.node_elements:
                results[key] = self.node_elements[key]
        return results

    def get_downstream_node_of_element(self, ekey, ignore_disabled=True):
        gnodes = set(self.gnode_element_mapping_inverted[ekey])
        results = dict()
        if len(gnodes) == 1:
            downstream_nodes_element = gnodes
        else:
            upstream_nodes = self.get_upstream_nodes(ekey, ignore_disabled=ignore_disabled)
            upstream_nodes_element = upstream_nodes & gnodes
            downstream_nodes_element = gnodes - upstream_nodes_element
        for gnode in downstream_nodes_element:
            key = (ekey[0], gnode)
            if key in self.node_elements:
                results[key] = self.node_elements[key]
        return results
    
    # Export results routines

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
