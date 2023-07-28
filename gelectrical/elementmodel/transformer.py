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

import math
from gi.repository import PangoCairo

# local files import
from .. import misc
from .element import ElementModel
from ..model.protection import ProtectionModel


class Transformer(ElementModel):

    code = 'element_transformer'
    name = 'Transformer'
    group = 'Transformers'
    icon = misc.abs_path('icons', 'transformer.svg')
    tooltip = """<b>Two-winding Transformer</b>

Creates a two-winding transformer.
"""

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.database_path = misc.open_library('transformer.csv')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[2, 0],
                      [2, 10]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'T?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_mva':        self.get_field_dict('float', 'Sn', 'MVA', 1),
                       'vn_hv_kv':      self.get_field_dict('float', 'Un (HV)', 'kV', 11),
                       'vn_lv_kv':      self.get_field_dict('float', 'Un (LV)', 'kV', 0.415),
                       'vkr_percent':   self.get_field_dict('float', 'Usc (Real)', '%', 0.5),
                       'vk_percent':    self.get_field_dict('float', 'Usc', '%',4.5),
                       'vkr0_percent':  self.get_field_dict('float', 'U0sc (Real)', '%', 0.5),
                       'vk0_percent':   self.get_field_dict('float', 'U0sc', '%',4.5),
                       'mag0_percent':  self.get_field_dict('float', 'Zm0/Z0', '',10),
                       'mag0_rx':       self.get_field_dict('float', 'R0m/X0m', '',0),
                       'si0_hv_partial':self.get_field_dict('float', 'Fraction of U0 on HV side', '',0.1),
                       'shift_degree':  self.get_field_dict('float', 'Shift Degree', 'deg', 30),
                       'vector_group':  self.get_field_dict('str', 'Vector Group', '', 'Dyn', selection_list=['Dyn','Yyn','Yzn','YNyn']),
                       'pfe_kw':        self.get_field_dict('float', 'Pfe', 'kW', 30),
                       'i0_percent':    self.get_field_dict('float', 'I0', '%', 0.1),
                       'sym_hv':        self.get_field_dict('str', 'HV Symbol', '', 'D'),
                       'sym_lv':        self.get_field_dict('str', 'LV Symbol', '', 'Yn'),
                       'tap_side':      self.get_field_dict('str', 'Tap side', '', 'hv',
                                                            selection_list=['hv','lv']),
                       'tap_min':       self.get_field_dict('int', 'Minimum tap position', '', -2),
                       'tap_max':       self.get_field_dict('int', 'Maximum tap position', '', 4),
                       'tap_pos':       self.get_field_dict('int', 'Current tap position', '', 0),
                       'tap_step_percent': self.get_field_dict('float', 'Tap step size', '%', 2.5),
                       'oltc':          self.get_field_dict('bool', 'OLTC provided ?', '', False),
                       'xn_ohm': self.get_field_dict('float', 'Impedance of the grounding reactor', 'Ohm', 0),
                       'dcurve': self.get_field_dict('data', 'Damage curve', '', None,
                                                                    alter_structure=True),}
        self.fields['dcurve']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, 
                                                    misc.GRAPH_PROT_TIME_LIMITS, 
                                                    'CURRENT IN AMPERES', 
                                                    'TIME IN SECONDS', {})
        
        self.text_model = [[(5,2.5), "${ref}", True],
                           [(5,None), "${sn_mva}MVA", True],
                           [(5,None), "${'%g'%(vn_hv_kv)}/${'%g'%(vn_lv_kv)}kV", True],
                           [(5,None), "${name}", True],
                           [(2,3.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_hv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(2,6.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_lv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center']]
        self.schem_model = [ 
                             ['CIRCLE', (2,3.5), 2, False, []],
                             ['CIRCLE', (2,6.5), 2, False, []],
                             ['LINE',(2,0),(2,1.5), []],
                             ['LINE',(2,8.5),(2,10), []],
                           ]
        self.calculate_parameters(init=True)
        self.assign_tootltips()
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        
        # Render
        self.render_model(context, self.schem_model)
        self.render_text(context, self.text_model)
        # Post processing
        self.modify_extends()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        ports = tuple(tuple(x) for x in self.get_ports_global())
        p0 = code + ':0'
        p1 = code + ':1'
        nodes = ((p0, (ports[0],)),
                 (p1, (ports[1],)))
        return nodes
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        p1 = code + ':1'
        power_model = (('trafo', (p0, p1), {'name': self.fields['ref']['value'],
                                            'sn_mva': self.fields['sn_mva']['value'],
                                            'vn_hv_kv': self.fields['vn_hv_kv']['value'],
                                            'vn_lv_kv': self.fields['vn_lv_kv']['value'],
                                            'vkr_percent': self.fields['vkr_percent']['value'],
                                            'vk_percent': self.fields['vk_percent']['value'],
                                            'pfe_kw': self.fields['pfe_kw']['value'],
                                            'i0_percent': self.fields['i0_percent']['value'],
                                            'vector_group': self.fields['vector_group']['value'],
                                            'vk0_percent': self.fields['vk0_percent']['value'],
                                            'vkr0_percent': self.fields['vkr0_percent']['value'],
                                            'mag0_percent': self.fields['mag0_percent']['value'],
                                            'mag0_rx': self.fields['mag0_rx']['value'],
                                            'si0_hv_partial': self.fields['si0_hv_partial']['value'],
                                            'tap_side': self.fields['tap_side']['value'],
                                            'tap_max': self.fields['tap_max']['value'],
                                            'tap_min': self.fields['tap_min']['value'],
                                            'tap_pos': self.fields['tap_pos']['value'],
                                            'tap_neutral': 0,
                                            'tap_step_percent': self.fields['tap_step_percent']['value'],
                                            'oltc': self.fields['oltc']['value'],
                                            'shift_degree': self.fields['shift_degree']['value'],
                                            'xn_ohm': self.fields['xn_ohm']['value']}),)
        return power_model
    
    def set_text_field_value(self, code, value):
        ElementModel.set_text_field_value(self, code, value)
        if not self.model_loading:
            self.calculate_parameters(init=False)

    def set_model_cleanup(self):
        self.calculate_parameters(init=False)

    def calculate_parameters(self, init=False):
        # Damage curve
        title = (self.fields['ref']['value'])
        i_n = self.fields['sn_mva']['value']*1e3 / (1.732*self.fields['vn_lv_kv']['value'])
        i_sc = i_n / self.fields['vk_percent']['value'] * 100
        curve_u = [('point', 'd.i_e*'+str(i_n), 3600),
                    ('point', i_sc, 'd.t_sc')]
        curve_l = [('point', 'd.i_100ms*'+str(i_n), 0.1),
                    ('point', 'd.i_10ms*'+str(i_n), 0.01),]
        param = {'i_e'  : ['Short time emergency load', 'xIn', 2, None],
                't_sc'  : ['Short circuit withstand time', 's', 2, None],
                'i_100ms'  : ['Inrush current @ 0.1 s', 'xIn', 12, None],
                'i_10ms'  : ['Inrush current @ 0.01 s', 'xIn', 25, None],}
        self.damage_model = ProtectionModel(title, param, curve_u, curve_l, element_type='damage')
        if not init:
            self.damage_model.update_parameters(self.fields['dcurve']['value']['parameters'])
        self.fields['dcurve']['value'] = self.damage_model.get_evaluated_model(self.fields)


class Transformer3w(ElementModel):
    
    code = 'element_transformer3w'
    name = '3W Transformer'
    group = 'Transformers'
    icon = misc.abs_path('icons', 'transformer3w.svg')
    tooltip = """<b>Three-winding Transformer</b>

Creates a three-winding transformer.
"""

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.database_path = misc.open_library('transformer3w.csv')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[4, 0],
                      [2, 10],
                      [6, 10]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'T?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_hv_mva':     self.get_field_dict('float', 'Sn (HV)', 'MVA', 40),
                       'sn_mv_mva':     self.get_field_dict('float', 'Sn (MV)', 'MVA', 20),
                       'sn_lv_mva':     self.get_field_dict('float', 'Sn (LV)', 'MVA', 20),
                       'vn_hv_kv':      self.get_field_dict('float', 'Un (HV)', 'kV', 110),
                       'vn_mv_kv':      self.get_field_dict('float', 'Un (MV)', 'kV', 20),
                       'vn_lv_kv':      self.get_field_dict('float', 'Un (LV)', 'kV', 10),
                       'vk_hv_percent':    self.get_field_dict('float', 'Usc (HV)', '%',10),
                       'vk_mv_percent':    self.get_field_dict('float', 'Usc (MV)', '%',11),
                       'vk_lv_percent':    self.get_field_dict('float', 'Usc (LV)', '%',12),
                       'vkr_hv_percent':   self.get_field_dict('float', 'Usc (Real) (HV)', '%', 0.3),
                       'vkr_mv_percent':   self.get_field_dict('float', 'Usc (Real) (MV)', '%', 0.31),
                       'vkr_lv_percent':   self.get_field_dict('float', 'Usc (Real) (LV)', '%', 0.32),
                       'pfe_kw':        self.get_field_dict('float', 'Pfe', 'kW', 30),
                       'i0_percent':    self.get_field_dict('float', 'I0m', '%', 0.1),
                       'shift_mv_degree':   self.get_field_dict('float', 'Shift MV Degree', 'deg', 30),
                       'shift_lv_degree':   self.get_field_dict('float', 'Shift LV Degree', 'deg', 30),
                       'sym_hv':        self.get_field_dict('str', 'HV Symbol', '', 'D'),
                       'sym_mv':        self.get_field_dict('str', 'MV Symbol', '', 'Yn'),
                       'sym_lv':        self.get_field_dict('str', 'LV Symbol', '', 'Yn')}
        
        self.text_model = [[(8.5,2.5), "${ref}", True],
                           [(8.5,None), "${sn_hv_mva}/${sn_mv_mva}/${sn_lv_mva}MVA", True],
                           [(8.5,None), "${'%g'%(vn_hv_kv)}/${'%g'%(vn_mv_kv)}/${'%g'%(vn_lv_kv)}kV", True],
                           [(8.5,None), "${name}", True],
                           [(4,3.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_hv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(2,6.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_mv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(6,6.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_lv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center']]
        self.schem_model = [ 
                             ['CIRCLE', (4,3.5), 2, False, []],
                             ['CIRCLE', (2,6.5), 2, False, []],
                             ['CIRCLE', (6,6.5), 2, False, []],
                             ['LINE',(4,0),(4,1.5), []],
                             ['LINE',(2,8.5),(2,10), []],
                             ['LINE',(6,8.5),(6,10), []],
                           ]
        self.assign_tootltips()
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        
        # Render
        self.render_model(context, self.schem_model)
        self.render_text(context, self.text_model)
        # Post processing
        self.modify_extends()
        
    def get_nodes(self, code):
        """Return nodes for analysis"""
        ports = tuple(tuple(x) for x in self.get_ports_global())
        p0 = code + ':0'
        p1 = code + ':1'
        p2 = code + ':2'
        nodes = ((p0, (ports[0],)),
                 (p1, (ports[1],)),
                 (p2, (ports[2],)))
        return nodes
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        p1 = code + ':1'
        p2 = code + ':2'
        power_model = (('trafo3w', (p0, p1, p2), {'name': self.fields['ref']['value'],
                                            'sn_hv_mva': self.fields['sn_hv_mva']['value'],
                                            'sn_mv_mva': self.fields['sn_mv_mva']['value'],
                                            'sn_lv_mva': self.fields['sn_lv_mva']['value'],
                                            'vn_hv_kv': self.fields['vn_hv_kv']['value'],
                                            'vn_mv_kv': self.fields['vn_mv_kv']['value'],
                                            'vn_lv_kv': self.fields['vn_lv_kv']['value'],
                                            'vk_hv_percent': self.fields['vk_hv_percent']['value'],
                                            'vk_mv_percent': self.fields['vk_mv_percent']['value'],
                                            'vk_lv_percent': self.fields['vk_lv_percent']['value'],
                                            'vkr_hv_percent': self.fields['vkr_hv_percent']['value'],
                                            'vkr_mv_percent': self.fields['vkr_mv_percent']['value'],
                                            'vkr_lv_percent': self.fields['vkr_lv_percent']['value'],
                                            'shift_mv_degree': self.fields['shift_mv_degree']['value'],
                                            'shift_lv_degree': self.fields['shift_lv_degree']['value'],
                                            'pfe_kw': self.fields['pfe_kw']['value'],
                                            'i0_percent': self.fields['i0_percent']['value']}),)
        return power_model
    
