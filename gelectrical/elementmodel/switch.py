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
from ..model.protection import ProtectionModel


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
                       'name':     self.get_field_dict('str', 'Name', '', ''),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,1.5), "${ref}", True],
                           [(3.5,None), "${name}", True]]
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
                       'name'       : self.get_field_dict('str', 'Name', '', ''),
                       'type'       : self.get_field_dict('str', 'Type', '', 'gG', 
                                                            selection_list=self.fuse_types),
                       'poles'      : self.get_field_dict('str', 'Poles', '', 'TP', 
                                                            selection_list=self.pole_types),
                       'Un'         : self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In'         : self.get_field_dict('int', 'In', 'A', 63, 
                                                            selection_list=self.current_values,
                                                            alter_structure=True),
                       'In_set'     : self.get_field_dict('float', 'In_set', 'xIn', 1, 
                                                            status_enable=False),
                       'Isc'        : self.get_field_dict('float', 'Isc', 'kA', 50, 
                                                            alter_structure=True),
                       'pcurve_l'   : self.get_field_dict('data', 'Line Protection', '', None,
                                                            alter_structure=True),
                       'sdfu'       : self.get_field_dict('bool', 'Switch Disconnector ?', '', True),
                       'closed'     : self.get_field_dict('bool', 'Closed ?', '', True)
                       }
        self.text_model = [[(3.5,0.5), "${poles}, ${ref}", True],
                           [(3.5,None), "${str(In)} A, ${type}", True],
                           [(3.5,None), "${Isc}kA", True],
                           [(3.5,None), "${name}", True]]
        self.schem_model_fuse = [ 
                             ['LINE',(1,0),(1,6), []],
                             ['RECT', (0.5,1.5), 1, 3, False, []]
                           ]
        self.schem_model_sdfu = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,5), []],
                             # Round and bar
                             ['LINE',(0.5,2),(1.5,2), []],
                             ['CIRCLE', (1,2.3), 0.3, False, []],
                             # Fuse
                             ['LINE',(1,5),(1,10), []],
                             ['RECT', (0.5,6), 1, 3, False, []]
                           ]
        self.line_protection_model = None
        self.calculate_parameters(init=True)

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
        if code in ('type'):
            self.calculate_parameters(init=True)
        else:
            self.calculate_parameters(init=False)

    def calculate_parameters(self, init=False):
        # Get parameters
        In = self.fields['In']['value']
        Isc = self.fields['Isc']['value']*1000
        
        if init:
            # gG fuse
            if self.fields['type']['value'] == self.fuse_types[0]:
                (i_min_10, i_max_5, i_min_0_1, I_max_0_1) = self.gg_current_gates[In]
                (i2t_min_0_01, i2t_max_0_01) = self.gg_current_gates_prearc[In]
                i_min_0_01 = math.sqrt(i2t_min_0_01*1000/0.01)
                i_max_0_01 = math.sqrt(i2t_max_0_01*1000/0.01)
                curve_u = [ ('point', 'd.i_f*f.In', 'd.t_conv*3600'),
                                ('point', i_max_5, 5),
                                ('point', I_max_0_1, 0.1),
                                ('point', i_max_0_01, 0.01),
                                ('point', '1000*f.Isc', 0.01)]
                curve_l = [ ('point', 'd.i_nf*f.In', 'd.t_conv*3600'),
                                ('point', i_min_10, 10),
                                ('point', i_min_0_1,0.1),
                                ('point', i_min_0_01, 0.01),
                                ('point', '1000*f.Isc', 0.01)]
                # Get protection model
                parameters = {  'i_nf'  : ['Non fusing current', 'xIn', 1.25, None],
                                'i_f'   : ['Fusing current', 'xIn', 1.6, None],
                                't_conv': ['Convensional time', 'Hrs', self.gg_conv_times[In], None]}
                title = str(self.fields['In']['value']) + 'A, ' + self.fields['type']['value']
            
            self.line_protection_model = ProtectionModel(title, parameters, curve_u, curve_l)
        else:
            self.line_protection_model = ProtectionModel.new_from_data(self.fields['pcurve_l']['value'])
        self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)


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
        self.breaker_types = ['MCB','MCCB','ACB','MPCB','CB','RCCB']
        self.sub_types_mcb = ['B Curve', 'C Curve', 'D Curve']
        self.sub_types_mcb_dict = {'B Curve'     : (2,5),
                                   'C Curve'     : (5,10),
                                   'D Curve'     : (10,20),
                                   }
        self.sub_types_rccb = ['30 mA', '100 mA', '300 mA', '500 mA']
        self.sub_types_rccb_dict = {'30 mA'     : (0.03,0.015,0.03),
                                    '100 mA'    : (0.1,0.05,0.1),
                                    '300 mA'    : (0.3,0.15,0.3),
                                    '500 mA'    : (0.5,0.25,0.5),
                                   }
        self.current_values_mcb = [6,10,16,20,25,32,40,50,63,80,100]
        self.current_values_rccb = [25,32,40,63,80,100]
        self.current_values = [6,10,16,20,25,32,40,50,63,80,100,125,160,200,250,320,400,500,630,800,1000,1250,1600,2000,2500,3200]
        self.fields = { 'ref':      self.get_field_dict('str', 'Reference', '', 'Q?'),
                        'name':     self.get_field_dict('str', 'Name', '', ''),
                        'type':     self.get_field_dict('str', 'Type', '', 'CB',
                                                             selection_list=self.breaker_types,
                                                             alter_structure=True),
                        'subtype':  self.get_field_dict('str', 'Sub Type', '', '',
                                                             selection_list=None,
                                                             alter_structure=True),
                        'poles':    self.get_field_dict('str', 'Poles', '', 'TPN',
                                                        selection_list=self.pole_types),
                        'Un':       self.get_field_dict('float', 'Un', 'kV', 0.415),
                        'In':       self.get_field_dict('int', 'In', 'A', 63,
                                                        selection_list=self.current_values,
                                                        alter_structure=True),
                        'In_set':    self.get_field_dict('float', 'In_set', 'xIn', 1,
                                                      alter_structure=True, status_enable=True),
                        'Im_min':   self.get_field_dict('float', 'Im (min)', 'xIn', 5,
                                                        alter_structure=True, status_enable=True),
                        'Im_max':   self.get_field_dict('float', 'Im (max)', 'xIn', 10,
                                                        alter_structure=True, status_enable=True),
                        't_mag':    self.get_field_dict('float', 't (inst)', 's', 0.001,
                                                        alter_structure=True, status_enable=True),
                        'pcurve_l': self.get_field_dict('data', 'Line Protection', '', None),
                        'I0n':      self.get_field_dict('float', 'I0n', 'xIn', 1,
                                                        alter_structure=True, status_enable=True),
                        'I0m_min':  self.get_field_dict('float', 'I0m (min)', 'xIn', 5,
                                                        alter_structure=True, status_enable=True),
                        'I0m_max':  self.get_field_dict('float', 'I0m (max)', 'xIn', 10,
                                                        alter_structure=True, status_enable=True),
                        't0_mag':    self.get_field_dict('float', 't0 (inst)', 's', 0.001,
                                                        alter_structure=True, status_enable=True),
                        'Isc':      self.get_field_dict('int', 'Isc', 'kA', 10,
                                                        alter_structure=True),
                        'drawout':  self.get_field_dict('bool', 'Drawout type ?', '', False, status_enable=True),
                        'closed':   self.get_field_dict('bool', 'Closed ?', '', True)}
        self.fields['pcurve_l']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, misc.GRAPH_PROT_TIME_LIMITS, 'I (A)', 'Time (s)')
        self.text_model = [[(3.5,0.5), "${type}, ${poles}, ${ref}", True],
                           [(3.5,None), "${str(In) + 'A' if In_set == 1 else str(In) + 'A(' + str(round(In*In_set)) + 'A)'}, ${subtype}", True],
                           [(3.5,None), "${Isc}kA", True],
                           [(3.5,None), "${name}", True]]
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
        self.schem_model_rccb = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Round and bar
                             ['LINE',(0.5,2),(1.5,2), []],
                             ['CIRCLE', (1,2.3), 0.3, False, []],
                             # Arrow
                             ['LINE',(1.75,3),(2.75,3.75), [], 'thin'],
                             ['LINE',(2.325,3.275),(2.75,3.75), []],
                             ['LINE',(2.175,3.475),(2.75,3.75), []],
                             # RCCB symbol
                             ['LINE',(2.95,3.9),(3.35,4.2), [], 'thin'],
                             ['LINE',(3.1,3.7),(2.8,4.1), [], 'thin'],
                           ]
        self.calculate_parameters(init=True)

    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        if self.fields['drawout']['value']:
            self.schem_model = self.schem_model_do
        else:
            if  self.fields['type']['value'] in ['RCCB']:
                self.schem_model = self.schem_model_rccb
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

    def set_text_field_value(self, code, value):
        if self.fields and code in self.fields:
            self.fields[code]['value'] = value
            # Modify variables based on selection
            if code == 'type':
                if value in ['MCB']:
                    self.fields['In']['selection_list'] = self.current_values_mcb
                    if self.fields['In']['value'] not in self.current_values_mcb:
                        self.fields['In']['value'] = self.current_values_mcb[0]
                    self.fields['subtype']['selection_list'] = self.sub_types_mcb
                    self.fields['subtype']['value'] = self.sub_types_mcb[0]

                    self.fields['In_set']['status_enable'] = False
                    self.fields['Im_min']['status_enable'] = False
                    self.fields['Im_max']['status_enable'] = False
                    self.fields['t_mag']['status_enable'] = False
                    self.fields['I0n']['status_enable'] = False
                    self.fields['I0m_min']['status_enable'] = False
                    self.fields['I0m_max']['status_enable'] = False
                    self.fields['t0_mag']['status_enable'] = False
                    self.fields['drawout']['status_enable'] = False

                elif value in ['RCCB']:
                    self.fields['In']['selection_list'] = self.current_values_rccb
                    if self.fields['In']['value'] not in self.current_values_rccb:
                        self.fields['In']['value'] = self.current_values_rccb[0]
                    self.fields['subtype']['selection_list'] = self.sub_types_rccb
                    self.fields['subtype']['value'] = self.sub_types_rccb[0]

                    self.fields['In_set']['status_enable'] = False
                    self.fields['Im_min']['status_enable'] = False
                    self.fields['Im_max']['status_enable'] = False
                    self.fields['t_mag']['status_enable'] = False
                    self.fields['I0n']['status_enable'] = False
                    self.fields['I0m_min']['status_enable'] = False
                    self.fields['I0m_max']['status_enable'] = False
                    self.fields['t0_mag']['status_enable'] = False
                    self.fields['drawout']['status_enable'] = False

                elif value in ['MCCB','ACB']:
                    self.fields['In']['selection_list'] = self.current_values
                    if self.fields['In']['value'] not in self.current_values:
                        self.fields['In']['value'] = self.current_values[0]
                    self.fields['subtype']['selection_list'] = None
                    self.fields['subtype']['value'] = ''

                    self.fields['In_set']['status_enable'] = True
                    self.fields['Im_min']['status_enable'] = True
                    self.fields['Im_max']['status_enable'] = True
                    self.fields['t_mag']['status_enable'] = True
                    self.fields['I0n']['status_enable'] = True
                    self.fields['I0m_min']['status_enable'] = True
                    self.fields['I0m_max']['status_enable'] = True
                    self.fields['t0_mag']['status_enable'] = True
                    self.fields['drawout']['status_enable'] = True

                elif value in ['MPCB', 'CB']:
                    self.fields['In']['selection_list'] = None
                    self.fields['subtype']['selection_list'] = None
                    self.fields['subtype']['value'] = ''

                    self.fields['In_set']['status_enable'] = True
                    self.fields['Im_min']['status_enable'] = True
                    self.fields['Im_max']['status_enable'] = True
                    self.fields['t_mag']['status_enable'] = True
                    self.fields['I0n']['status_enable'] = True
                    self.fields['I0m_min']['status_enable'] = True
                    self.fields['I0m_max']['status_enable'] = True
                    self.fields['t0_mag']['status_enable'] = True
                    self.fields['drawout']['status_enable'] = True
            
            if code in ('type'):
                self.calculate_parameters(init=True)
            else:
                self.calculate_parameters(init=False)

    def calculate_parameters(self, init=False):
        # Get parameters
        In = self.fields['In']['value']
        Isc = self.fields['Isc']['value']*1000
        
        if init:
            # MCB IS/IEC 60898
            if self.fields['type']['value'] in ('MCB'):
                i_f = 1.45
                i_nf = 1.13
                t_ins_min = 0.001
                t_ins_max = 0.008
                t_conv = 1
                curve_u = [ ('point', 'd.i_f*f.In', 'd.t_conv*3600'),
                            ('point', '1000*f.Isc', 'd.t_ins_max')]
                curve_l = [ ('point', 'd.i_nf*f.In', 'd.t_conv*3600'),
                            ('point', '1000*f.Isc', 'd.t_ins_min')]
            # CB generic IS/IEC 60947
            else:
                i_f = 1.3
                i_nf = 1.05
                if self.fields['In']['value'] <= 63:
                    t_conv = 1
                else:
                    t_conv = 2
                t_ins_min = 0.01
                t_ins_max = 0.02
                curve_u = [ ('point', 'd.i_f*f.In', 'd.t_conv*3600'),
                            ('point', '1000*f.Isc', 'd.t_ins_max')]
                curve_l = [ ('point', 'd.i_nf*f.In', 'd.t_conv*3600'),
                            ('point', '1000*f.Isc', 'd.t_ins_min')]
            # Get protection model
            parameters = {  'i_nf'      : ['Non fusing current', 'xIn', i_nf, None],
                            'i_f'       : ['Fusing current', 'xIn', i_f, None],
                            't_conv'    : ['Convensional time', 'Hrs', t_conv, None],
                            't_ins_min' : ['Instantaneous trip time (min)', 's', t_ins_min, None],
                            't_ins_max' : ['Instantaneous trip time (max)', 's', t_ins_max, None]}
            title = (self.fields['type']['value'] + ', ' + 
                    (self.fields['subtype']['value']  + ', ' if self.fields['subtype']['value'] else '') +
                    str(self.fields['In']['value']) + 'A')
            self.line_protection_model = ProtectionModel(title, parameters, curve_u, curve_l)
        else:
            self.line_protection_model = ProtectionModel.new_from_data(self.fields['pcurve_l']['value'])
        self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)


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
                       'name':     self.get_field_dict('str', 'Name', '', ''),
                       'type':    self.get_field_dict('str', 'Type', '', 'AC-3'),
                       'poles':   self.get_field_dict('str', 'Poles', '', 'TP'),
                       'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In':      self.get_field_dict('int', 'In', 'A', 16),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,1), "${poles}, ${ref}", True],
                           [(3.5,None), "${In}A, ${type}", True],
                           [(3.5,None), "${name}", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Circle
                             ['ARC', (1,1.5), 0.5, -90, 90, []],
                           ]
