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


class Shunt(ElementModel):
    """Shunt impedence element"""

    code = 'element_shunt'
    name = 'Shunt'
    group = 'Loads'
    icon = misc.abs_path('icons', 'shunt.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'Z?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'p_kw':        self.get_field_dict('float', 'P', 'kW', 10),
                       'q_kvar':       self.get_field_dict('float', 'Q', 'kVAr', 0),
                       'vn_kv':       self.get_field_dict('float', 'Vn', 'kV', 0.415),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${p_kw}+j${q_kvar}kVA", True],
                           [(3,None), "${name}", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,1), []],
                             ['RECT', (0.25,1), 1.5, 5, False, []],
                             ['LINE',(1,6),(1,7), []],
                             # Earth
                             ['LINE',(0.25,7),(1.75,7), []],
                             ['LINE',(0.5,7.5),(1.5,7.5), []],
                             ['LINE',(0.75,8),(1.25,8), []],
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
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        power_model = (('shunt', (p0,), {'name': self.fields['ref']['value'],
                                       'p_mw': self.fields['p_kw']['value']/1000,
                                       'q_mvar': self.fields['q_kvar']['value']/1000,
                                       'vn_kv': self.fields['vn_kv']['value'],
                                       'in_service': self.fields['in_service']['value']}),)
        return power_model


class ShuntCapacitor(Shunt):
    """Shunt capacitor element"""

    code = 'element_shunt_cap'
    name = 'Shunt Capacitor'
    group = 'Loads'
    icon = misc.abs_path('icons', 'shuntcap.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Shunt.__init__(self, cordinates, **kwargs)
        self.fields['ref']['value'] = 'C?'
        self.fields['p_kw']['value'] = 0
        self.fields['q_kvar']['value'] = -10
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${-q_kvar}kVAr", True],
                           [(3,None), "${name}", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,3), []],
                             ['LINE',(0,3),(2,3), [], 'thick'],
                             ['LINE',(0,4),(2,4), [], 'thick'],
                             ['LINE',(1,4),(1,7), []],
                             # Earth
                             ['LINE',(0.25,7),(1.75,7), []],
                             ['LINE',(0.5,7.5),(1.5,7.5), []],
                             ['LINE',(0.75,8),(1.25,8), []],
                           ]

