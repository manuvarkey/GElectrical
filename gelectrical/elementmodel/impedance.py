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


class Impedance(ElementModel):
    """Series impedence element"""
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_impedance'
        self.name = 'Impedance'
        self.group = 'Components'
        self.icon = misc.abs_path('icons', 'impedance.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0], [1, 8]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'Z?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'rft_pu':     self.get_field_dict('float', 'R', 'pu', 0.01),
                       'xft_pu':  self.get_field_dict('float', 'X', 'pu', 0.01),
                       'sn_mva':  self.get_field_dict('float', 'Base MVA', 'MVA', 1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = []
        self.schem_model = [ 
                             ['LINE',(1,0),(1,1.5), []],
                             ['RECT', (0.25,1.5), 1.5, 5, False, []],
                             ['LINE',(1,6.5),(1,8), []],
                           ]
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${rft_pu}+j${xft_pu}pu", True],
                           [(3,None), "${sn_mva}MVA", True],
                           [(3,None), "${name}", True]]
    
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
        p1 = code + ':1'
        nodes = ((p0, (ports[0],)),(p1, (ports[1],)))
        return nodes
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        p1 = code + ':1'
        power_model = (('impedance', (p0,p1), {'name': self.fields['ref']['value'],
                                       'rft_pu': self.fields['rft_pu']['value'],
                                       'xft_pu': self.fields['xft_pu']['value'],
                                       'sn_mva': self.fields['sn_mva']['value'],
                                       'in_service': self.fields['in_service']['value'],}),)
        return power_model


class Inductance(Impedance):
    """Series inductance element"""
    def __init__(self, cordinates=(0,0)):
        # Global
        Impedance.__init__(self, cordinates)
        self.code = 'element_inductance'
        self.name = 'Inductance'
        self.group = 'Components'
        self.icon = misc.abs_path('icons', 'inductance.svg')
        self.ports = [[1, 0], [1, 8]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'L?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'rft_pu':     self.get_field_dict('float', 'R', 'pu', 0),
                       'xft_pu':  self.get_field_dict('float', 'X', 'pu', 0.07),
                       'sn_mva':  self.get_field_dict('float', 'Base MVA', 'MVA', 1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = []
        self.schem_model = [ 
                             ['LINE',(1,0),(1,1.75), []],
                             # Core
                             ['LINE',(2.5,1.5),(2.5,6.5), [], 'thin'],
                             # Body
                             ['ARC', (1,2.5), 0.75, -90, 90, []],
                             ['ARC', (1,4), 0.75, -90, 90, []],
                             ['ARC', (1,5.5), 0.75, -90, 90, []],
                             
                             ['LINE',(1,6.25),(1,8), []],
                           ]
        self.text_model = [[(3.5,1), "${ref}", True],
                           [(3.5,None), "j${xft_pu}pu", True],
                           [(3.5,None), "${sn_mva}MVA", True],
                           [(3.5,None), "${name}", True]]
