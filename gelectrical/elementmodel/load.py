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


class Load(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_load'
        self.name = 'Load'
        self.group = 'Loads'
        self.icon = misc.abs_path('icons', 'load.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
                      
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'X?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_mva':        self.get_field_dict('float', 'Rated power', 'MW', 0),
                       'cos_phi':       self.get_field_dict('float', 'PF', '', 0.8),
                       'scaling':          self.get_field_dict('float', 'DF', '', 1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'mode':          self.get_field_dict('bool', 'Inductive ?', '', True),
                       'load_profile':  self.get_field_dict('graph', 'Load Profile', '', 0, inactivate=True ) }
        self.fields['load_profile']['graph_options'] = (misc.GRAPH_LOAD_TIME_LIMITS, misc.GRAPH_LOAD_CURRENT_LIMITS, 'Time (Hr)', 'DF')
        self.text_model = []
        self.schem_model = [ 
                             ['LINE',(1,0),(1,5), []],
                             ['LINE',(0.5,5),(1.5,5), []],
                             ['LINE',(0.5,5),(1,8), []],
                             ['LINE',(1.5,5),(1,8), []]
                           ]
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        pftag = 'lead' if self.fields['mode']['value'] else 'lag'
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${sn_mva}MVA", True],
                           [(3,None), "${cos_phi} pf " + pftag, True],
                           [(3,None), "${name}", True]]
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
        mode = 'underexcited' if self.fields['mode']['value'] else 'overexcited'
        power_model = (('load', (p0,), {'name': self.fields['ref']['value'],
                                       'sn_mva': self.fields['sn_mva']['value'],
                                       'cos_phi': self.fields['cos_phi']['value'],
                                       'scaling': self.fields['scaling']['value'],
                                       'in_service': self.fields['in_service']['value'],
                                       'mode': mode}),)
        return power_model

