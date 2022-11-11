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


class Grid(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_grid'
        self.name = 'External Grid'
        self.group = 'Sources'
        self.icon = misc.abs_path('icons', 'grid.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[2, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'G?'),
                       'name':     self.get_field_dict('str', 'Name', '', 'EXTERNAL GRID'),
                       'vm_pu':    self.get_field_dict('float', 'Vm', 'pu', 1),
                       'va_degree':    self.get_field_dict('float', 'Vm<', 'degree', 0),
                       'vn_kv':    self.get_field_dict('float', 'Vn', 'kv', 11),
                       's_sc_max_mva':      self.get_field_dict('float', 'Ssc_max', 'MVA', 500),
                       's_sc_min_mva':      self.get_field_dict('float', 'Ssc_min', 'MVA', 100),
                       'rx_max':  self.get_field_dict('float', 'R/X max', '', 0.1),
                       'rx_min':      self.get_field_dict('float', 'R/X min', '',0),
                       'r0x0_max':  self.get_field_dict('float', 'R0/X0 max', '', 0.1),
                       'r0x0_min':  self.get_field_dict('float', 'R0/X0 min', '', 0),
                       'x0x_max':  self.get_field_dict('float', 'X0/X max', '', 1),
                       'x0x_min':  self.get_field_dict('float', 'X0/X min', '', 1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = [[(5,0.5), "${name}, ${ref}", True],
                           [(5,None), "${vm_pu}∠${va_degree}, ${vn_kv}kV", True]]
        self.schem_model = [ 
                             ['RECT', (0,0), 4, 4, False, []],
                             # Hatch
                             ['LINE',(0,0),(4,4), [], 'thin'],
                             ['LINE',(0,4),(4,0), [], 'thin'],
                             ['LINE',(0,2),(2,0), [], 'thin'],
                             ['LINE',(2,0),(4,2), [], 'thin'],
                             ['LINE',(4,2),(2,4), [], 'thin'],
                             ['LINE',(2,4),(0,2), [], 'thin'],
                             # Connect line
                             ['LINE',(2,4),(2,6), []],
                           ]
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        
        # Render
        if self.fields['in_service']['value']:
            self.render_model(context, self.schem_model)
            self.render_text(context, self.text_model)
        else:
            self.render_model(context, self.schem_model, color=misc.COLOR_INACTIVE)
            self.render_text(context, self.text_model, color=misc.COLOR_INACTIVE)
        # Post processing
        self.modify_extends()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        ports = tuple(tuple(x) for x in self.get_ports_global())
        p0 = code + ':0'
        nodes = ((p0, (ports[0],)),)
        return nodes
        
    def get_power_model(self, code):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        power_model = (('ext_grid', (p0,), {'name': self.fields['ref']['value'],
                                       'vm_pu': self.fields['vm_pu']['value'],
                                       'va_degree': self.fields['va_degree']['value'],
                                       's_sc_max_mva': self.fields['s_sc_max_mva']['value'],
                                       's_sc_min_mva': self.fields['s_sc_min_mva']['value'],
                                       'rx_max': self.fields['rx_max']['value'],
                                       'rx_min': self.fields['rx_min']['value'],
                                       'r0x0_max': self.fields['r0x0_max']['value'],
                                       'x0x_max': self.fields['x0x_max']['value'],
                                       'r0x0_min': self.fields['r0x0_min']['value'],
                                       'x0x_min': self.fields['x0x_min']['value'],
                                       'in_service': self.fields['in_service']['value'],}),)
        return power_model

