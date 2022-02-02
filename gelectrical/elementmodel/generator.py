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


class Generator(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_generator'
        self.name = 'Generator'
        self.group = 'Sources'
        self.icon = misc.abs_path('icons', 'generator.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[2, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'G?'),
                       'name':     self.get_field_dict('str', 'Name', '', 'GENERATOR'),
                       'vm_pu':    self.get_field_dict('str', 'Vm', 'pu', 1),
                       'vn_kv':    self.get_field_dict('float', 'Vn', 'kV', 0.415),
                       'p_mw':    self.get_field_dict('float', 'P', 'MW', 0.5),
                       'sn_mva':    self.get_field_dict('float', 'Sn', 'MVA', 1),
                       'cos_phi':    self.get_field_dict('float', 'PF', '', 0),
                       'xdss_pu':      self.get_field_dict('float', 'Xdss', 'pu', 0.12),
                       'rdss_pu':      self.get_field_dict('float', 'Rdss', 'pu', 0.01),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'slack':    self.get_field_dict('bool', 'Slack ?', '', True)}
        self.text_model = [[(5,0), "${name}, ${ref}", True],
                           [(5,None), "${sn_mva}MVA, ${cos_phi}pf", True],
                           [(5,None), "${vm_pu}pu, ${vn_kv}kV", True]]
        self.schem_model = [ 
                             ['CIRCLE', (2,2), 2, False, []],
                             # Sine
                             ['ARC', (2.5,2), 0.5, 0, -180, [], 'thin'],
                             ['ARC', (1.5,2), 0.5, -180, -360, [], 'thin'],
                             # Connecting line
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
        power_model = (('gen', (p0,), {'name': self.fields['ref']['value'],
                                       'vm_pu': self.fields['vm_pu']['value'],
                                       'vn_kv': self.fields['vn_kv']['value'],
                                       'p_mw': self.fields['p_mw']['value'],
                                       'sn_mva': self.fields['sn_mva']['value'],
                                       'cos_phi': self.fields['cos_phi']['value'],
                                       'xdss_pu': self.fields['xdss_pu']['value'],
                                       'rdss_pu': self.fields['rdss_pu']['value'],
                                       'in_service': self.fields['in_service']['value'],
                                       'slack': self.fields['slack']['value'],}),)
        return power_model


class StaticGenerator(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_staticgenerator'
        self.name = 'Static Generator'
        self.group = 'Sources'
        self.icon = misc.abs_path('icons', 'generator.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[2, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'G?'),
                       'name':     self.get_field_dict('str', 'Name', '', 'S.GENERATOR'),
                       'p_mw':    self.get_field_dict('float', 'P', 'MW', 0.5),
                       'q_mvar':    self.get_field_dict('float', 'Q', 'MVAr', 0),
                       'k':    self.get_field_dict('float', 'In/Isc', '', 0.1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'load_profile':  self.get_field_dict('graph', 'Generation Profile', '', 0, inactivate=True ) }
        self.fields['load_profile']['graph_options'] = (misc.GRAPH_LOAD_TIME_LIMITS, misc.GRAPH_LOAD_CURRENT_LIMITS, 'Time (Hr)', 'DF')
        self.text_model = [[(5,0), "${name}, ${ref}", True],
                           [(5,None), "${p_mw}+j${q_mvar}MVA", True]]
        self.schem_model = [ 
                             ['CIRCLE', (2,2), 2, False, []],
                             # Sine
                             ['ARC', (2.5,2), 0.5, 0, -180, [], 'thin'],
                             ['ARC', (1.5,2), 0.5, -180, -360, [], 'thin'],
                             # Connecting line
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
        p_mw = self.fields['p_mw']['value']
        q_mvar = self.fields['q_mvar']['value']
        sn_mva = (p_mw*p_mw+q_mvar*q_mvar)**0.5
        power_model = (('sgen', (p0,), {'name': self.fields['ref']['value'],
                                       'sn_mva': sn_mva,
                                       'p_mw': p_mw,
                                       'q_mvar': q_mvar,
                                       'k': self.fields['k']['value'],
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model


class Motor(StaticGenerator):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        StaticGenerator.__init__(self, cordinates)
        self.code = 'element_async_motor'
        self.name = 'Asynchronous Motor'
        self.group = 'Loads'
        self.icon = misc.abs_path('icons', 'motor.svg')
        self.database_path = misc.abs_path('database', 'motor.csv')
        self.ports = [[2, 0]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'M?'),
                       'name':     self.get_field_dict('str', 'Name', '', 'MOTOR'),
                       'p_kw':    self.get_field_dict('float', 'P', 'kW', 25),
                       'cos_phi':    self.get_field_dict('float', 'PF', '', 0.8),
                       'k':    self.get_field_dict('float', 'Isc/In', '', 7),
                       'rx':      self.get_field_dict('float', 'R/X', '', 0.42),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'load_profile':  self.get_field_dict('graph', 'Load Profile', '', 0, inactivate=True ) }
        self.fields['load_profile']['graph_options'] = (misc.GRAPH_LOAD_TIME_LIMITS, misc.GRAPH_LOAD_CURRENT_LIMITS, 'Time (Hr)', 'DF')
        self.text_model = [[(5,2), "${name}, ${ref}", True],
                           [(5,None), "${p_kw}kW, ${cos_phi}pf", True],]
        self.schem_model = [ 
                             ['CIRCLE', (2,4), 2, False, []],
                             # M
                             ['LINE',(1.5,4),(1.75,3), [], 'thin'],
                             ['LINE',(1.75,3),(2,4), [], 'thin'],
                             ['LINE',(2,4),(2.25,3), [], 'thin'],
                             ['LINE',(2.25,3),(2.5,4), [], 'thin'],
                             # Sine
                             ['ARC', (2.25,5), 0.25, 0, -180, [], 'thin'],
                             ['ARC', (1.75,5), 0.25, -180, -360, [], 'thin'],
                             # Connecting line
                             ['LINE',(2,0),(2,2), []],
                           ]
        
    def get_power_model(self, code):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        p_mw = self.fields['p_kw']['value']/1000
        pf = self.fields['cos_phi']['value']
        q_mvar = p_mw/pf*(1-pf**2)**0.5
        sn_mva = p_mw/pf
        power_model = (('sgen', (p0,), {'name': self.fields['ref']['value'],
                                       'p_mw': -p_mw,
                                       'q_mvar': -q_mvar,
                                       'type': 'motor',
                                       'k': self.fields['k']['value'],
                                       'rx': self.fields['rx']['value'],
                                       'sn_mva': sn_mva,
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model
