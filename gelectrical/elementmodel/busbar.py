#  
#  Copyright 2019 Manu Varkey <manuvarkey@gmail.com>
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

import os, cairo
from gi.repository import PangoCairo

# local files import
from .. import misc
from .element import ElementModel


class BusBar(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_busbar'
        self.name = 'Bus Bar'
        self.group = 'Components'
        self.icon = misc.abs_path('icons', 'busbar.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = []
        self.text_model = []
        self.schem_model = []
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'B?'),
                       'In':      self.get_field_dict('int', 'In', 'A', 200),
                       'Isc':     self.get_field_dict('float', 'Isc', 'kA', 16),
                       'n_top':   self.get_field_dict('int', '#P(T)', '', 1, status_floating=True, status_live=True, max_chars=2),
                       'n_btm':   self.get_field_dict('int', '#P(B)', '', 3, status_floating=True, status_live=True, max_chars=2),
                       'width':   self.get_field_dict('int', 'Bay Width', 'pt', 12),}
        self.widths = []
        # Set parameters
        self.set_model_from_param()
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        self.set_model_from_param()
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
        p0 = code + ':0'
        power_model = (('bus', (p0,), {'name': self.fields['ref']['value'],
                                     'vn_kv': 0,
                                     'type': 'b'}),)
        return power_model
        
    # Private functions
    
    def set_model_from_param(self):
        width = self.fields['width']['value']
        self.ports = []
        self.widths = [width]*(max(self.fields['n_top']['value'], self.fields['n_btm']['value']) - 1)
        bus_width = sum(self.widths)
        max_num_ports = max(self.fields['n_top']['value'], self.fields['n_btm']['value'])
        # Draw bus 
        self.schem_model = [['LINE',(1,2),(1+bus_width,2), [],'thicker']]
        # Add top ports
        min_num_port = int((max_num_ports-self.fields['n_top']['value'])/2)
        max_num_port = min_num_port + self.fields['n_top']['value']
        for i in range(min_num_port, max_num_port):
            x = 1 + sum(self.widths[0:i])
            self.ports.append([x, 0])
            self.schem_model.append(['LINE',(x,0),(x,2), []])
        # Add bottom ports
        min_num_port = int((max_num_ports-self.fields['n_btm']['value'])/2)
        max_num_port = min_num_port + self.fields['n_btm']['value']
        for i in range(min_num_port, max_num_port):
            x = 1 + sum(self.widths[0:i])
            self.ports.append([x, 4])
            self.schem_model.append(['LINE',(x,2),(x,4), []])
        # Set text model
        self.text_model = [[(bus_width+2,0.5), "${ref}", True],
                           [(bus_width+2,None), "${In}A, ${Isc}kA", True]]
                           
