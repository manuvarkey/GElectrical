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

import os, cairo, math
from gi.repository import PangoCairo

# local files import
from .. import misc
from .element import ElementModel


class Load(ElementModel):

    code = 'element_load'
    name = 'Load 3ph'
    group = 'Loads'
    icon = misc.abs_path('icons', 'load.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
                      
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'X?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_kva':        self.get_field_dict('float', 'Rated power', 'kVA', 0),
                       'cos_phi':       self.get_field_dict('float', 'PF', '', 0.8),
                       'scaling':          self.get_field_dict('float', 'DF', '', 1),
                       'mode':          self.get_field_dict('bool', 'Inductive ?', '', True),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'load_profile':  self.get_field_dict('graph', 'Load Profile', '', 'load_prof_1', status_inactivate=True ) }
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
        pftag = 'lag' if self.fields['mode']['value'] else 'lead'
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${sn_kva} kVA", True],
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
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        mode = 'underexcited' if self.fields['mode']['value'] else 'overexcited'
        power_model = (('load', (p0,), {'name': self.fields['ref']['value'],
                                       'sn_mva': self.fields['sn_kva']['value']/1000,
                                       'cos_phi': self.fields['cos_phi']['value'],
                                       'scaling': self.fields['scaling']['value'],
                                       'in_service': self.fields['in_service']['value'],
                                       'mode': mode}),)
        return power_model

    
class AsymmetricLoad(ElementModel):
    
    code = 'element_asymmetric_load'
    name = 'Load 3ph Asymmetric'
    group = 'Loads'
    icon = misc.abs_path('icons', 'load.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
                      
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'X?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_kva':        self.get_field_dict('float', 'Rated power', 'kVA', 0),
                       'p_a_kw':       self.get_field_dict('float', 'Pa', 'kW', 0),
                       'p_b_kw':       self.get_field_dict('float', 'Pb', 'kW', 0),
                       'p_c_kw':       self.get_field_dict('float', 'Pc', 'kW', 0),
                       'q_a_kvar':       self.get_field_dict('float', 'Qa', 'kVAr', 0),
                       'q_b_kvar':       self.get_field_dict('float', 'Qb', 'kVAr', 0),
                       'q_c_kvar':       self.get_field_dict('float', 'Qc', 'kVAr', 0),
                       'scaling':          self.get_field_dict('float', 'DF', '', 1),
                       'type':          self.get_field_dict('str', 'Connection Type', '', 'wye', selection_list=['wye','delta']),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'load_profile':  self.get_field_dict('graph', 'Load Profile', '', 'load_prof_1', status_inactivate=True )}
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
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${sn_kva} kVA", True],
                           [(3,None), "(${p_a_kw}, ${p_b_kw}, ${p_c_kw}) kW", True],
                           [(3,None), "(${q_a_kvar}, ${q_b_kvar}, ${q_c_kvar}) kVAr", True],
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
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        power_model = (('asymmetric_load', (p0,), {'name': self.fields['ref']['value'],
                                       'sn_mva': self.fields['sn_kva']['value']/1000,
                                       'p_a_mw': self.fields['p_a_kw']['value']/1000,
                                       'p_b_mw': self.fields['p_b_kw']['value']/1000,
                                       'p_c_mw': self.fields['p_c_kw']['value']/1000,
                                       'q_a_mvar': self.fields['q_a_kvar']['value']/1000,
                                       'q_b_mvar': self.fields['q_b_kvar']['value']/1000,
                                       'q_c_mvar': self.fields['q_c_kvar']['value']/1000,
                                       'type': self.fields['type']['value'],
                                       'scaling': self.fields['scaling']['value'],
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model
    

class SinglePhaseLoad(Load):
    
    code = 'element_single_phase_load'
    name = 'Load 1ph'
    group = 'Loads'
    icon = misc.abs_path('icons', 'load.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Load.__init__(self, cordinates, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
                      
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'X?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_kva':        self.get_field_dict('float', 'Rated power', 'kVA', 0),
                       'cos_phi':       self.get_field_dict('float', 'PF', '', 0.8),
                       'scaling':          self.get_field_dict('float', 'DF', '', 1),
                       'phase':          self.get_field_dict('str', 'Phase', '', 'A', selection_list=['A','B','C']),
                       'mode':          self.get_field_dict('bool', 'Inductive ?', '', True),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True),
                       'load_profile':  self.get_field_dict('graph', 'Load Profile', '', 'load_prof_1', status_inactivate=True )}
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
        pftag = 'lag' if self.fields['mode']['value'] else 'lead'
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${sn_kva} kVA", True],
                           [(3,None), "${cos_phi} pf " + pftag, True],
                           [(3,None), "${name}", True],
                           [(2,7.5), "${phase}", True]]
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
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        pf = self.fields['cos_phi']['value']
        p_mw = self.fields['sn_kva']['value']*pf/1000
        # Inductive load
        if self.fields['mode']['value'] is True:
            q_mvar = self.fields['sn_kva']['value']*math.sqrt(1-pf**2)/1000
        # Capacitive load
        else:
            q_mvar = -self.fields['sn_kva']['value']*math.sqrt(1-pf**2)/1000
        p_a_mw = p_b_mw = p_c_mw = 0
        q_a_mvar = q_b_mvar = q_c_mvar = 0
        if self.fields['phase']['value'] == 'A':
            p_a_mw = p_mw
            q_a_mvar = q_mvar
        elif self.fields['phase']['value'] == 'B':
            p_b_mw = p_mw
            q_b_mvar = q_mvar
        elif self.fields['phase']['value'] == 'C':
            p_c_mw = p_mw
            q_c_mvar = q_mvar

        power_model = (('asymmetric_load', (p0,), {'name': self.fields['ref']['value'],
                                       'sn_mva': self.fields['sn_kva']['value']/1000,
                                       'p_a_mw': p_a_mw,
                                       'p_b_mw': p_b_mw,
                                       'p_c_mw': p_c_mw,
                                       'q_a_mvar': q_a_mvar,
                                       'q_b_mvar': q_b_mvar,
                                       'q_c_mvar': q_c_mvar,
                                       'type': 'wye',
                                       'scaling': self.fields['scaling']['value'],
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model


# Motor models suitable for assymetric calculations


class Motor3ph(Load):
    
    code = 'element_async_motor_3ph'
    name = 'Motor 3ph'
    group = 'Loads'
    icon = misc.abs_path('icons', 'motor.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Load.__init__(self, cordinates, **kwargs)
        self.database_path = misc.abs_path('database', 'motor.csv')
        self.ports = [[2, 0]]
        self.fields['ref']['value'] = 'M?'
        self.fields['sn_kva']['status_enable'] = False
        self.fields['mode']['status_enable'] = False
        self.fields['ref'] = self.get_field_dict('str', 'Reference', '', 'M?')
        self.fields.update({'p_kw':    self.get_field_dict('float', 'P', 'kW', 25),
                       'k':    self.get_field_dict('float', 'Isc/In', '', 7),
                       'rx':      self.get_field_dict('float', 'R/X', '', 0.42)})
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
        self.calculate_parameters()

    def set_text_field_value(self, code, value):
        if code in self.fields:
            self.fields[code]['value'] = value
        self.calculate_parameters()

    def calculate_parameters(self):
        self.fields['sn_kva']['value'] = self.fields['p_kw']['value']/self.fields['cos_phi']['value']
        self.fields['mode']['value'] = True

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


class Motor1ph(SinglePhaseLoad):
    
    code = 'element_async_motor_1ph'
    name = 'Motor 1ph'
    group = 'Loads'
    icon = misc.abs_path('icons', 'motor.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        SinglePhaseLoad.__init__(self, cordinates, **kwargs)
        self.database_path = None
        self.ports = [[2, 0]]
        self.fields['ref']['value'] = 'M?'
        self.fields['sn_kva']['status_enable'] = False
        self.fields['mode']['status_enable'] = False
        self.fields['ref'] = self.get_field_dict('str', 'Reference', '', 'M?')
        self.fields.update({'p_kw':    self.get_field_dict('float', 'P', 'kW', 25),
                       'k':    self.get_field_dict('float', 'Isc/In', '', 7),
                       'rx':      self.get_field_dict('float', 'R/X', '', 0.42)})
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
        self.calculate_parameters()

    def set_text_field_value(self, code, value):
        if code in self.fields:
            self.fields[code]['value'] = value
        self.calculate_parameters()

    def calculate_parameters(self):
        self.fields['sn_kva']['value'] = self.fields['p_kw']['value']/self.fields['cos_phi']['value']
        self.fields['mode']['value'] = True

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