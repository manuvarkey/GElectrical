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


class Transformer(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_transformer'
        self.name = 'Transformer'
        self.group = 'Transformers'
        self.icon = misc.abs_path('icons', 'transformer.svg')
        self.database_path = misc.abs_path('database', 'transformer.csv')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[2, 0],
                      [2, 10]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'T?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'sn_mva':        self.get_field_dict('float', 'Sn', 'MVA', 100),
                       'vn_hv_kv':      self.get_field_dict('float', 'Un (HV)', 'kV', 11),
                       'vn_lv_kv':      self.get_field_dict('float', 'Un (LV)', 'kV', 0.415),
                       'vkr_percent':   self.get_field_dict('float', 'Usc (Real)', '%', 0.5),
                       'vk_percent':    self.get_field_dict('float', 'Usc', '%',4.5),
                       'vkr0_percent':  self.get_field_dict('float', 'U₀sc (Real)', '%', 0.5),
                       'vk0_percent':   self.get_field_dict('float', 'U₀sc', '%',4.5),
                       'mag0_percent':  self.get_field_dict('float', 'I₀m', '%',10),
                       'mag0_rx':       self.get_field_dict('float', 'R₀m/X₀m', '',0.4),
                       'si0_hv_partial':self.get_field_dict('float', 'Fraction of U₀ on HV side', '',0.9),
                       'shift_degree':  self.get_field_dict('float', 'Shift Degree', 'deg', 30),
                       'vector_group':  self.get_field_dict('str', 'Vector Group', '', 'Dyn', selection_list=['Dyn','Yyn','Yzn','YNyn']),
                       'pfe_kw':        self.get_field_dict('float', 'Pfe', 'kW', 30),
                       'i0_percent':    self.get_field_dict('float', 'I₀m', '%', 0.1),
                       'sym_hv':        self.get_field_dict('str', 'HV Symbol', '', 'D'),
                       'sym_lv':        self.get_field_dict('str', 'LV Symbol', '', 'Yn')}
        
        self.text_model = [[(5,2.5), "${ref}", True],
                           [(5,None), "${sn_mva}MVA", True],
                           [(5,None), "${vn_hv_kv}/${vn_lv_kv}kV", True],
                           [(5,None), "${name}", True],
                           [(2,3.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_hv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(2,6.5-misc.SCHEM_FONT_SIZE/2/misc.M), "${sym_lv}", True, misc.SCHEM_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center']]
        self.schem_model = [ 
                             ['CIRCLE', (2,3.5), 2, False, []],
                             ['CIRCLE', (2,6.5), 2, False, []],
                             ['LINE',(2,0),(2,1.5), []],
                             ['LINE',(2,8.5),(2,10), []],
                           ]
    
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
        
    def get_power_model(self, code):
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
                                            'shift_degree': self.fields['shift_degree']['value']}),)
        return power_model


class Transformer3w(ElementModel):
    
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_transformer3w'
        self.name = '3W Transformer'
        self.group = 'Transformers'
        self.icon = misc.abs_path('icons', 'transformer3w.svg')
        self.database_path = misc.abs_path('database', 'transformer3w.csv')
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
                       'i0_percent':    self.get_field_dict('float', 'Iom', '%', 0.1),
                       'shift_mv_degree':   self.get_field_dict('float', 'Shift MV Degree', 'deg', 30),
                       'shift_lv_degree':   self.get_field_dict('float', 'Shift LV Degree', 'deg', 30),
                       'sym_hv':        self.get_field_dict('str', 'HV Symbol', '', 'D'),
                       'sym_mv':        self.get_field_dict('str', 'MV Symbol', '', 'Yn'),
                       'sym_lv':        self.get_field_dict('str', 'LV Symbol', '', 'Yn')}
        
        self.text_model = [[(8.5,2.5), "${ref}", True],
                           [(8.5,None), "${sn_hv_mva}/${sn_mv_mva}/${sn_lv_mva}MVA", True],
                           [(8.5,None), "${vn_hv_kv}/${vn_mv_kv}/${vn_lv_kv}kV", True],
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
        
    def get_power_model(self, code):
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
    
