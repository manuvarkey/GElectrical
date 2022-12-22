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
import numpy as np
from shapely import Polygon, Point, LineString

# local files import
from .. import misc
from ..misc import FieldDict
from .element import ElementModel


class ProtectionBase():
    """Generic protection base element"""

    def __init__(self, curve_upper, curve_lower, fields):
        """ARGUMENTS:
            curve_upper : Upper t vs I protection curve as string of list expression 
                            ex: "[(f.i_m, t_conv), ... , (i_max, f.t_min)]"
            curve_lower : Lower t vs I protection curve as string of list expression
            fields      : Fields to be used in evaluation of curves
        """
        self.curve_upper = curve_upper
        self.curve_lower = curve_lower
        self.fields = FieldDict(fields)
        # Generated variables
        self.polygon = None
        self.linestring_upper = None
        self.linestring_lower = None
        # Set mandatory fields
        self.i_f = self.fields.i_f  # Convensional fusing current
        self.i_nf = self.fields.i_nf  # Convensional non-fusing current
        self.i_max = self.fields.i_max  # Maximum current rating
        self.t_conv = self.fields.t_conv  # Convensional breaking time
        self.evaluate_curves()

    def evaluate_curves(self):
        # Evaluate
        var_dict = {'f':self.fields,
                    'i_f':self.i_f,
                    'i_nf':self.i_nf,
                    'i_max':self.i_max,
                    't_conv':self.t_conv}
        curve_upper = eval(self.curve_upper, var_dict)
        curve_lower = eval(self.curve_lower, var_dict)
        self.linestring_upper = LineString(reversed(curve_upper))
        self.linestring_lower = LineString(curve_lower)
        self.polygon = Polygon(list(reversed(curve_upper)) + curve_lower)

    def get_graph(self, title):
        polygon_pnts = np.array((self.polygon.exterior.coords))
        xval = polygon_pnts[:,0]
        yval = polygon_pnts[:,1]
        graph_model = ['Protection Curve', [{'mode':misc.GRAPH_DATATYPE_POLYGON, 'title':title, 'xval':xval, 'yval': yval},]]
        return graph_model

class Switch(ElementModel):
    """Generic switching element"""

    code = 'element_switch'
    name = 'Switch'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'switch.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
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


class Fuse(Switch):
    """Generic Fuse element"""
    
    code = 'element_fuse'
    name = 'Fuse'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'fuse.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Switch.__init__(self, cordinates, **kwargs)
        self.ports = [[1, 0],
                      [1, 6]]
        self.fuse_types = ['gG']
        self.pole_types = ['SP', 'TP']
        self.current_values = [16,20,25,32,40,50,63,80,100,125,160,200,250,315,400,500,630,800,1000,1250]
        self.fields = {'ref'        : self.get_field_dict('str', 'Reference', '', 'Q?'),
                       'type'       : self.get_field_dict('str', 'Type', '', 'gG', selection_list=self.fuse_types),
                       'poles'      : self.get_field_dict('str', 'Poles', '', 'TP', selection_list=self.pole_types),
                       'Un'         : self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In'         : self.get_field_dict('int', 'In', 'A', 63, selection_list=self.current_values,
                                                          alter_structure=True),
                       'pcurve_l'   : self.get_field_dict('graph', 'Line Protection', '', None, inactivate=True ),
                       'In_set'     : self.get_field_dict('float', 'In_set', 'xIn', 1, status_enable=False),
                       'Isc'        : self.get_field_dict('float', 'Isc', 'kA', 100),
                       'sdfu'       : self.get_field_dict('bool', 'Switch Disconnector ?', '', True),
                       'closed'     : self.get_field_dict('bool', 'Closed ?', '', True),
                       # Breaker fields
                       'i_f'    : self.get_field_dict('float', 'If', 'A', 63, status_enable=False),
                       'i_nf'   : self.get_field_dict('float', 'Inf', 'A', 63*1.25, status_enable=False),
                       'i_max'  : self.get_field_dict('float', 'I_f', 'A', 100000, status_enable=False),
                       't_conv' : self.get_field_dict('float', 'I_f', 's', 3600, status_enable=False),
                       }
        self.fields['pcurve_l']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, misc.GRAPH_PROT_TIME_LIMITS, 'I (A)', 'Time (s)')
        self.text_model = [[(3.5,0.5), "${poles}, ${ref}", True],
                           [(3.5,None), "${str(In)} A, ${type}", True],
                           [(3.5,None), "${Isc}kA", True]]
        self.schem_model_fuse = [ 
                             ['LINE',(1,0),(1,6), []],
                             ['RECT', (0.5,1.5), 1, 3, False, []]
                           ]
        self.schem_model_sdfu = [ 
                             ['LINE',(1,0),(1,1.4), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,5), []],
                             # Round and bar
                             ['LINE',(0.5,2),(1.5,2), []],
                             ['CIRCLE', (1,1.7), 0.3, False, []],
                             # Fuse
                             ['LINE',(1,5),(1,10), []],
                             ['RECT', (0.5,6), 1, 3, False, []]
                           ]
        self.line_protection_model = None
        self.calculate_parameters()

    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        if self.fields['sdfu']['value']:
            self.schem_model = self.schem_model_sdfu
        else:
            self.schem_model = self.schem_model_fuse
        # Render
        if self.fields['closed']['value'] == True:
            self.render_model(context, self.schem_model)
            self.render_text(context, self.text_model)
        else:
            self.render_model(context, self.schem_model, color=misc.COLOR_INACTIVE)
            self.render_text(context, self.text_model, color=misc.COLOR_INACTIVE)
        # Post processing
        self.modify_extends()

    def set_text_field_value(self, code, value):
        ElementModel.set_text_field_value(self, code, value)
        self.calculate_parameters()

    def calculate_parameters(self):
        # Get parameters
        In = self.fields['In']['value']
        Isc = self.fields['Isc']['value']*1000
        # General fields
        self.fields['i_max']['value'] = Isc
        # gG fuse
        if self.fields['type']['value'] == self.fuse_types[0]:
            self.fields['i_f']['value'] = 1.6*In
            self.fields['i_nf']['value'] = 1.25*In
            self.fields['t_conv']['value'] = 3600
            curve_upper = """[(i_f, t_conv), 
                              (i_max, 0.01)]"""
            curve_lower = """[(i_nf, t_conv), 
                              (i_max, 0.001)]"""
        # Get breaker model
        self.line_protection_model = ProtectionBase(curve_upper, curve_lower, self.fields)
        graph = self.line_protection_model.get_graph('Line Protection')
        self.fields['pcurve_l']['value'] = graph

        

class CircuitBreaker(Switch):
    """Generic circuit breaker element"""
    
    code = 'element_circuitbreaker'
    name = 'Circuit Breaker'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'circuitbreaker.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Switch.__init__(self, cordinates, **kwargs)
        self.ports = [[1, 0],
                      [1, 6]]
        self.pole_types = ['SP', 'SPN', 'DP', 'TP', 'TPN', 'FP']
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'Q?'),
                       'type':    self.get_field_dict('str', 'Type', '', 'CB'),
                       'poles':   self.get_field_dict('str', 'Poles', '', 'TPN', selection_list=self.pole_types),
                       'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In':      self.get_field_dict('int', 'In', 'A', 63),
                       'In_set':  self.get_field_dict('float', 'In_set', 'xIn', 1),
                       'Im_min':  self.get_field_dict('float', 'Im (min)', 'xIn', 5),
                       'Im_max':  self.get_field_dict('float', 'Im (max)', 'xIn', 10),
                       'I0n':     self.get_field_dict('float', 'I0n', 'xIn', 1),
                       'I0m_min': self.get_field_dict('float', 'I0m (min)', 'xIn', 5),
                       'I0m_max': self.get_field_dict('float', 'I0m (max)', 'xIn', 10),
                       'Isc':     self.get_field_dict('float', 'Isc', 'kA', 10),
                       'drawout': self.get_field_dict('bool', 'Drawout type ?', '', False),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,0.5), "${type}, ${poles}, ${ref}", True],
                           [(3.5,None), "${str(In) + 'A' if In_set == 1 else str(In) + 'A(' + str(round(In*In_set)) + 'A)'}", True],
                           [(3.5,None), "${Isc}kA", True]]
        self.schem_model_do = [ 
                             ['LINE',(1,0.5),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,5.5), []],
                             # Cross
                             ['LINE',(0.625,1.625),(1.375,2.375), []],
                             ['LINE',(0.625,2.375),(1.375,1.625), []],
                             # Drawout symbol
                             ['LINE',(1,0),(1.5,0.5), []],
                             ['LINE',(1,0.5),(1.5,1), []],
                             ['LINE',(1,0),(0.5,0.5), []],
                             ['LINE',(1,0.5),(0.5,1), []],
                             ['LINE',(1,6),(1.5,5.5), []],
                             ['LINE',(1,5.5),(1.5,5), []],
                             ['LINE',(1,6),(0.5,5.5), []],
                             ['LINE',(1,5.5),(0.5,5), []],
                           ]
        self.schem_model_ndo = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Cross
                             ['LINE',(0.625,1.625),(1.375,2.375), []],
                             ['LINE',(0.625,2.375),(1.375,1.625), []],
                           ]

    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        if self.fields['drawout']['value']:
            self.schem_model = self.schem_model_do
        else:
            self.schem_model = self.schem_model_ndo
        # Render
        if self.fields['closed']['value'] == True:
            self.render_model(context, self.schem_model)
            self.render_text(context, self.text_model)
        else:
            self.render_model(context, self.schem_model, color=misc.COLOR_INACTIVE)
            self.render_text(context, self.text_model, color=misc.COLOR_INACTIVE)
        # Post processing
        self.modify_extends()


class Contactor(Switch):
    """Generic circuit breaker element"""

    code = 'element_contactor'
    name = 'Contactor'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'contactor.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Switch.__init__(self, cordinates, **kwargs)
        self.ports = [[1, 0],
                      [1, 6]]
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'K?'),
                       'type':    self.get_field_dict('str', 'Type', '', 'AC-3'),
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
