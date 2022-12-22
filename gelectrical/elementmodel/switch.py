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
import numpy as np
from shapely import Polygon, Point, LineString

# local files import
from .. import misc
from ..misc import FieldDict
from .element import ElementModel


class ProtectionBase():
    """Generic protection base element"""

    def __init__(self, curve_upper, curve_lower):
        """ARGUMENTS:
            curve_upper : Upper t vs I protection curve as list of tuples
            curve_lower : Lower t vs I protection curve as list of tuples
            fields      : Fields to be used in evaluation of curves
        """
        self.curve_upper = curve_upper
        self.curve_lower = curve_lower
        # Generated variables
        self.polygon = None
        self.linestring_upper = None
        self.linestring_lower = None
        self.evaluate_curves()

    def evaluate_curves(self):
        self.linestring_upper = LineString(reversed(self.curve_upper))
        self.linestring_lower = LineString(self.curve_lower)
        self.polygon = Polygon(list(reversed(self.curve_upper)) + self.curve_lower)

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
    name = 'Fuse (LV)'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'fuse.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Switch.__init__(self, cordinates, **kwargs)
        self.ports = [[1, 0],
                      [1, 6]]
        # Data drapdowns
        self.fuse_types = ['gG']
        self.pole_types = ['SP', 'TP']
        self.current_values = [16,20,25,32,40,50,63,80,100,125,160,200,250,315,400,500,630,800,1000,1250]

        # gG fuse data parameters
        ## IEC 60269-1 - (I_min @ 10s, I_max @ 5s, I_min @ 0.1s, I_max @ 0.1s) in A
        self.gg_current_gates = {  16: [33,65,85,150],
                                20: [42,85,110,200],
                                25: [52,110,150,260],

                                32: [75,150,200,350],
                                40: [95,190,260,450],
                                50: [125,250,350,610],
                                63: [160,320,450,820],
                                80: [215,425,610,1100],

                                100: [290,580,820,1450],
                                125: [355,715,1100,1910],
                                160: [460,950,1450,2590],
                                200: [610,1250,1910,3420],
                                250: [750,1650,2590,4500],

                                315: [1050,2200,3420,6000],
                                400: [1420,2840,4500,8060],
                                500: [1780,3800,4500,8060],
                                630: [2200,5100,8060,14140],
                                800: [3060,7000,10600,19000],

                                1000: [4000,9500,14140,24000],
                                1250: [5000,13000,19000,35000]}
        ## IEC 60269-1 - (I2t_min, I2t_max) @ 0.01 s in 1e3 A2/s
        self.gg_current_gates_prearc = {   16: [0.3,1],
                                        20: [0.5,1.8],
                                        25: [1,3],
                                        32: [1.8,5],
                                        40: [3,9],
                                        50: [5,16],
                                        63: [9,27],
                                        80: [16,46],
                                        100: [27,86],
                                        125: [46,140],
                                        160: [86,250],
                                        200: [140,400],
                                        250: [250,760],
                                        315: [400,1300],
                                        400: [760,2250],
                                        500: [1300,3800],
                                        630: [2250,7500],
                                        800: [3800,13600],
                                        1000: [7840,25000],
                                        1250: [13700,47000]}
        ## IEC 60269-1 - Conventional time in Hrs
        self.gg_conv_times = { 16: 1,
                            20: 1,
                            25: 1,
                            32: 1,
                            40: 1,
                            50: 1,
                            63: 1,
                            80: 2,
                            100: 2,
                            125: 2,
                            160: 2,
                            200: 3,
                            250: 3,
                            315: 3,
                            400: 3,
                            500: 4,
                            630: 4,
                            800: 4,
                            1000: 4,
                            1250: 4}

        # Set fields
        self.fields = {'ref'        : self.get_field_dict('str', 'Reference', '', 'Q?'),
                       'type'       : self.get_field_dict('str', 'Type', '', 'gG', selection_list=self.fuse_types),
                       'poles'      : self.get_field_dict('str', 'Poles', '', 'TP', selection_list=self.pole_types),
                       'Un'         : self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In'         : self.get_field_dict('int', 'In', 'A', 63, selection_list=self.current_values,
                                                          alter_structure=True),
                       'pcurve_l'   : self.get_field_dict('graph', 'Line Protection', '', None, inactivate=True ),
                       'In_set'     : self.get_field_dict('float', 'In_set', 'xIn', 1, status_enable=False),
                       'Isc'        : self.get_field_dict('float', 'Isc', 'kA', 50, alter_structure=True),
                       'sdfu'       : self.get_field_dict('bool', 'Switch Disconnector ?', '', True),
                       'closed'     : self.get_field_dict('bool', 'Closed ?', '', True)
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
        i_max = Isc
        # gG fuse
        if self.fields['type']['value'] == self.fuse_types[0]:
            i_f = 1.6*In
            i_nf = 1.25*In
            t_conv = self.gg_conv_times[In]*3600
            (i_min_10, i_max_5, i_min_0_1, I_max_0_1) = self.gg_current_gates[In]
            (i2t_min_0_01, i2t_max_0_01) = self.gg_current_gates_prearc[In]
            i_min_0_01 = math.sqrt(i2t_min_0_01*1000/0.01)
            i_max_0_01 = math.sqrt(i2t_max_0_01*1000/0.01)
            curve_upper = [ (i_f, t_conv),
                            (i_max_5, 5),
                            (I_max_0_1, 0.1),
                            (i_max_0_01, 0.01),
                            (i_max, 0.01)]
            curve_lower = [ (i_nf, t_conv),
                            (i_min_10, 10),
                            (i_min_0_1,0.1),
                            (i_min_0_01, 0.01),
                            (i_max, 0.01)]
        # Get protection model
        self.line_protection_model = ProtectionBase(curve_upper, curve_lower)
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
