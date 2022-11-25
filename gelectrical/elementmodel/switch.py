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


class Switch(ElementModel):
    """Generic switching element"""
    def __init__(self, cordinates=(0,0)):
        # Global
        ElementModel.__init__(self, cordinates)
        self.code = 'element_switch'
        self.name = 'Switch'
        self.group = 'Switching Devices'
        self.icon = misc.abs_path('icons', 'switch.svg')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[1, 0],
                      [1, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'Q?'),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,1.5), "${ref}", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                           ]
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        
        # Render
        if self.fields['closed']['value'] == True:
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
        nodes = ((p0, (ports[0],)),
                 (p1, (ports[1],)))
        return nodes
        
    def get_power_model(self, code, mode=misc.POWER_MODEL_POWERFLOW):
        """Return pandapower model for analysis"""
        p0 = code + ':0'
        p1 = code + ':1'
        power_model = (('switch', (p0, p1), {'name': self.fields['ref']['value'],
                                             'closed': self.fields['closed']['value'],
                                             'et': 'b'}),)
        return power_model


class CircuitBreaker(Switch):
    """Generic circuit breaker element"""
    def __init__(self, cordinates=(0,0)):
        # Global
        Switch.__init__(self, cordinates)
        self.code = 'element_circuitbreaker'
        self.name = 'Circuit Breaker'
        self.group = 'Switching Devices'
        self.icon = misc.abs_path('icons', 'circuitbreaker.svg')
        self.ports = [[1, 0],
                      [1, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'Q?'),
                       'type':    self.get_field_dict('str', 'Type', '', 'CB'),
                       'poles':   self.get_field_dict('str', 'Poles', '', 'TPN'),
                       'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In':      self.get_field_dict('int', 'In', 'A', 16),
                       'In_set':  self.get_field_dict('int', 'In_set', 'A', 10),
                       'Im':      self.get_field_dict('float', 'Im', 'xIn',10),
                       'Isc':     self.get_field_dict('float', 'Isc', 'kA', 10),
                       'I0n':     self.get_field_dict('float', 'I0n', 'A', -1),
                       'I0m':     self.get_field_dict('float', 'I0m', 'A', -1),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,0.5), "${type}, ${poles}, ${ref}", True],
                           [(3.5,None), "${str(In) + 'A' if In == In_set else str(In) + 'A(' + str(In_set) + 'A)'}", True],
                           [(3.5,None), "${Isc}kA", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Cross
                             ['LINE',(0.625,1.625),(1.375,2.375), []],
                             ['LINE',(0.625,2.375),(1.375,1.625), []],
                           ]


class Contactor(Switch):
    """Generic circuit breaker element"""
    def __init__(self, cordinates=(0,0)):
        # Global
        Switch.__init__(self, cordinates)
        self.code = 'element_contactor'
        self.name = 'Contactor'
        self.group = 'Switching Devices'
        self.icon = misc.abs_path('icons', 'contactor.svg')
        self.ports = [[1, 0],
                      [1, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'K?'),
                       'type':    self.get_field_dict('str', 'Type', '', 'AC3'),
                       'poles':   self.get_field_dict('str', 'Poles', '', 'TP'),
                       'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In':      self.get_field_dict('int', 'In', 'A', 16),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,1), "${poles}, ${ref}", True],
                           [(3.5,None), "${In}A, ${type}", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Circle
                             ['ARC', (1,1.5), 0.5, -90, 90, []],
                           ]
