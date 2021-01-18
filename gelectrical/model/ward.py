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
from .drawing import ElementModel
from .. import misc


class Ward(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_ward'
        self.name = 'Ward Equivalent'
        self.group = 'Loads'
        self.icon = misc.abs_path('icons', 'ward.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'X?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'ps_mw':        self.get_field_dict('float', 'Ps', 'MW', 0),
                       'qs_mvar':       self.get_field_dict('float', 'Qs', 'MVAr', 0),
                       'pz_mw':        self.get_field_dict('float', 'Pz', 'MW', 0),
                       'qz_mvar':       self.get_field_dict('float', 'Qz', 'MVAr', 0),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = []
        self.schem_model = [ 
                             ['LINE',(1,0),(1,1), []],
                             ['RECT', (0.25,1), 1.5, 5, True, []],
                             ['LINE',(1,6),(1,7), []],
                             # Earth
                             ['LINE',(0.25,7),(1.75,7), []],
                             ['LINE',(0.5,7.5),(1.5,7.5), []],
                             ['LINE',(0.75,8),(1.25,8), []],
                           ]
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        self.text_model = [[(3,0.5), "${ref}", True],
                           [(3,None), "Ss=${ps_mw}+j${qs_mvar}MVA", True],
                           [(3,None), "Sz=${pz_mw}+j${qz_mvar}MVA", True],
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
        power_model = (('ward', (p0,), {'name': self.fields['ref']['value'],
                                       'ps_mw': self.fields['ps_mw']['value'],
                                       'qs_mvar': self.fields['qs_mvar']['value'],
                                       'pz_mw': self.fields['pz_mw']['value'],
                                       'qz_mvar': self.fields['qz_mvar']['value'],
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model


class XWard(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_xward'
        self.name = 'XWard Equivalent'
        self.group = 'Loads'
        self.icon = misc.abs_path('icons', 'ward.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'X?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'ps_mw':        self.get_field_dict('float', 'Ps', 'MW', 0),
                       'qs_mvar':       self.get_field_dict('float', 'Qs', 'MVAr', 0),
                       'pz_mw':        self.get_field_dict('float', 'Pz', 'MW', 0),
                       'qz_mvar':       self.get_field_dict('float', 'Qz', 'MVAr', 0),
                       'r_ohm':       self.get_field_dict('float', 'R', 'Ohm', 0),
                       'x_ohm':       self.get_field_dict('float', 'X', 'Ohm', 0),
                       'vm_pu':       self.get_field_dict('float', 'Vm', 'pu', 1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = []
        self.schem_model = [ 
                             ['LINE',(1,0),(1,1), []],
                             ['RECT', (0.25,1), 1.5, 5, True, []],
                             ['LINE',(1,6),(1,7), []],
                             # Earth
                             ['LINE',(0.25,7),(1.75,7), []],
                             ['LINE',(0.5,7.5),(1.5,7.5), []],
                             ['LINE',(0.75,8),(1.25,8), []],
                           ]
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        self.text_model = [[(3,0.5), "${ref}", True],
                           [(3,None), "Ss=${ps_mw}+j${qs_mvar}MVA", True],
                           [(3,None), "Sz=${pz_mw}+j${qz_mvar}MVA", True],
                           [(3,None), "${vm_pu}pu, ${r_ohm}+j${x_ohm}Ohm", True],
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
        power_model = (('xward', (p0,), {'name': self.fields['ref']['value'],
                                       'ps_mw': self.fields['ps_mw']['value'],
                                       'qs_mvar': self.fields['qs_mvar']['value'],
                                       'pz_mw': self.fields['pz_mw']['value'],
                                       'qz_mvar': self.fields['qz_mvar']['value'],
                                       'r_ohm': self.fields['r_ohm']['value'],
                                       'x_ohm': self.fields['x_ohm']['value'],
                                       'vm_pu': self.fields['vm_pu']['value'],
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model
