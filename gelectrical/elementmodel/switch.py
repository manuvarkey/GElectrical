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


class ProtectionDevice(Switch):
    """Generic Fuse element"""
    
    code = 'element_protectiondevice'
    name = 'Protection Device'
    group = 'Switching Devices'
    icon = None

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Switch.__init__(self, cordinates, **kwargs)
        # Set fields
        self.dict_subtype = {}
        self.dict_prot_curve_type = {}
        self.dict_prot_0_curve_type = {}
        self.dict_in = {}
        self.dict_i0 = {}
        self.fields.update({'custom'     : self.get_field_dict('bool', 'Custom ?', '', False, 
                                                            status_enable=False,
                                                            alter_structure=True),
                        'type'       : self.get_field_dict('str', 'Type', '', '',
                                                            alter_structure=True),
                        'subtype':  self.get_field_dict('str', 'Sub Type', '', '',
                                                             alter_structure=True),
                        'prot_curve_type':  self.get_field_dict('str', 'Line Protection curve', '', '',
                                                             alter_structure=True),
                        'prot_0_curve_type':  self.get_field_dict('str', 'Ground Protection curve', '', '',
                                                             alter_structure=True),
                        'poles'      : self.get_field_dict('str', 'Poles', '', 'TP'),
                        'Un'         : self.get_field_dict('float', 'Un', 'kV', 0.415),
                        'In'         : self.get_field_dict('float', 'In', 'A', 63,
                                                            alter_structure=True),
                        'In_set'     : self.get_field_dict('float', 'In_set', 'xIn', 1,
                                                            alter_structure=True),
                        'Isc'        : self.get_field_dict('float', 'Isc', 'kA', 50, 
                                                            alter_structure=True),
                        'pcurve_l'   : self.get_field_dict('data', 'Line Protection', '', None, 
                                                            alter_structure=True),
                        'I0'         : self.get_field_dict('float', 'I0', 'A', 63,
                                                            status_enable=False, 
                                                            alter_structure=True),
                        'I0_set'     : self.get_field_dict('float', 'I0_set', 'xI0', 1, 
                                                            status_enable=False,
                                                            alter_structure=True),
                        'pcurve_g'   : self.get_field_dict('data', 'Ground Protection', '', None,
                                                            status_enable=False,
                                                            alter_structure=True)
                       })
        self.fields['pcurve_l']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, 
                                                    misc.GRAPH_PROT_TIME_LIMITS, 
                                                    'CURRENT IN AMPERES', 
                                                    'TIME IN SECONDS', {})
        self.fields['pcurve_g']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, 
                                                    misc.GRAPH_PROT_TIME_LIMITS, 
                                                    'CURRENT IN AMPERES', 
                                                    'TIME IN SECONDS', {})
        self.line_protection_model = None
        self.ground_protection_model = None

    def get_line_protection_model(self):
        curve_u = []
        curve_l = []
        parameters = dict()
        return parameters, curve_u, curve_l

    def get_ground_protection_model(self):
        curve_u = []
        curve_l = []
        parameters = dict()
        return parameters, curve_u, curve_l

    def set_text_field_value(self, code, value):
        ElementModel.set_text_field_value(self, code, value)
        if code in ('type', 'subtype', 'prot_curve_type', 'prot_0_curve_type'):
            # Set subtype
            if self.fields['type']['value'] in self.dict_subtype:
                self.fields['subtype']['selection_list'] = self.dict_subtype[self.fields['type']['value']]
                self.fields['subtype']['status_enable'] = True
            else:
                self.fields['subtype']['selection_list'] = None
                self.fields['subtype']['value'] = 'None'
                self.fields['subtype']['status_enable'] = False
            if self.fields['subtype']['selection_list'] and self.fields['subtype']['value'] not in self.fields['subtype']['selection_list']:
                self.fields['subtype']['value'] = self.fields['subtype']['selection_list'][0]

            # Set protection curve
            if (self.fields['type']['value'], self.fields['subtype']['value']) in self.dict_prot_curve_type:
                self.fields['prot_curve_type']['selection_list'] = self.dict_prot_curve_type[(self.fields['type']['value'], self.fields['subtype']['value'])]
                self.fields['prot_curve_type']['status_enable'] = True
            else:
                self.fields['prot_curve_type']['selection_list'] = None
                self.fields['prot_curve_type']['value'] = 'None'
                self.fields['prot_curve_type']['status_enable'] = False
            if (self.fields['type']['value'], self.fields['subtype']['value']) in self.dict_prot_0_curve_type:
                self.fields['prot_0_curve_type']['selection_list'] = self.dict_prot_0_curve_type[(self.fields['type']['value'], self.fields['subtype']['value'])]
                self.fields['prot_0_curve_type']['status_enable'] = True
            else:
                self.fields['prot_0_curve_type']['selection_list'] = None
                self.fields['prot_0_curve_type']['value'] = 'None'
                self.fields['prot_0_curve_type']['status_enable'] = False
            if self.fields['prot_curve_type']['selection_list'] and self.fields['prot_curve_type']['value'] not in self.fields['prot_curve_type']['selection_list']:
                self.fields['prot_curve_type']['value'] = self.fields['prot_curve_type']['selection_list'][0]
            if self.fields['prot_0_curve_type']['selection_list'] and self.fields['prot_0_curve_type']['value'] not in self.fields['prot_0_curve_type']['selection_list']:
                self.fields['prot_0_curve_type']['value'] = self.fields['prot_0_curve_type']['selection_list'][0]

            # Set In selection list
            if (self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_curve_type']['value']) in self.dict_in:
                self.fields['In']['selection_list'] = self.dict_in[(self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_curve_type']['value'])]
            elif (self.fields['type']['value'], self.fields['subtype']['value'], '*') in self.dict_in:
                self.fields['In']['selection_list'] = self.dict_in[(self.fields['type']['value'], self.fields['subtype']['value'], '*')]
            else:
                self.fields['In']['selection_list'] = None
            if self.fields['In']['selection_list'] and self.fields['In']['value'] not in self.fields['In']['selection_list']:
                self.fields['In']['value'] = self.fields['In']['selection_list'][0]

            # Set I0 selection list
            if (self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_0_curve_type']['value']) in self.dict_i0:
                self.fields['I0']['selection_list'] = self.dict_i0[(self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_0_curve_type']['value'])]
            elif (self.fields['type']['value'], self.fields['subtype']['value'], '*') in self.dict_i0:
                self.fields['I0']['selection_list'] = self.dict_i0[(self.fields['type']['value'], self.fields['subtype']['value'], '*')]
            else:
                self.fields['I0']['selection_list'] = None
            if self.fields['I0']['selection_list'] and self.fields['I0']['value'] not in self.fields['I0']['selection_list']:
                self.fields['I0']['value'] = self.fields['I0']['selection_list'][0]

            # Enable or disable curves
            if self.fields['custom']['value']:
                self.fields['type']['selection_list'] = None
                if self.fields['pcurve_l']['value']:
                    self.fields['In_set']['status_enable'] = True
                    self.fields['pcurve_l']['status_enable'] = True
                elif self.fields['pcurve_g']['value']:
                    self.fields['I0']['status_enable'] = True
                    self.fields['I0_set']['status_enable'] = True
                    self.fields['pcurve_g']['status_enable'] = True
            else:
                # Line
                if self.fields['prot_curve_type']['value'] in ('Disabled', 'None', ''):
                    self.fields['In_set']['status_enable'] = False
                    self.fields['pcurve_l']['status_enable'] = False
                else:
                    self.fields['In_set']['status_enable'] = True
                    self.fields['pcurve_l']['status_enable'] = True
                # Ground
                if self.fields['prot_0_curve_type']['value'] in ('Disabled', 'None', ''):
                    self.fields['I0']['status_enable'] = False
                    self.fields['I0_set']['status_enable'] = False
                    self.fields['pcurve_g']['status_enable'] = False
                else:
                    self.fields['I0']['status_enable'] = True
                    self.fields['I0_set']['status_enable'] = True
                    self.fields['pcurve_g']['status_enable'] = True
            if not self.model_loading:
                self.calculate_parameters(init=True)
        else:
            if not self.model_loading:
                self.calculate_parameters(init=False)

    def set_model_cleanup(self):
        self.calculate_parameters(init=False)

    def calculate_parameters(self, init=False):
        # Form title
        # if self.fields['custom']['value']:
        #     title = (self.fields['ref']['value'] + ', ' + 
        #         '%g'%(self.fields['In']['value']) + 'A, ' + 
        #             self.fields['type']['value'])
        # else:
        #     title = (self.fields['ref']['value'] + ', ' + 
        #         '%g'%(self.fields['In']['value']) + 'A, ' + 
        #             self.fields['type']['value'] + ' - ' + 
        #             self.fields['subtype']['value'])
        title = self.fields['ref']['value']

        # Set line protection model
        parameters, curve_u, curve_l = self.get_line_protection_model()
        subtitle = title + ' - ' + 'L'
        if curve_l and curve_u:
            self.line_protection_model = ProtectionModel(subtitle, parameters, curve_u, curve_l)
            if not init:
                self.line_protection_model.update_parameters(self.fields['pcurve_l']['value']['parameters'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_l']['value']:
            self.line_protection_model = ProtectionModel(subtitle, {}, 
                                    self.fields['pcurve_l']['value']['data']['curve_u'],
                                    self.fields['pcurve_l']['value']['data']['curve_l'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        else:
            self.fields['pcurve_l']['value'] = None
            
        # Set ground protection model
        parameters, curve_u, curve_l = self.get_ground_protection_model()
        subtitle = title + ' - ' + 'L'
        if curve_l and curve_u:
            self.ground_protection_model = ProtectionModel(subtitle, parameters, curve_u, curve_l)
            if not init:
                self.ground_protection_model.update_parameters(self.fields['pcurve_g']['value']['parameters'])
            self.fields['pcurve_g']['value'] = self.ground_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_g']['value']:
            self.ground_protection_model = ProtectionModel(subtitle, {}, 
                                    self.fields['pcurve_g']['value']['data']['curve_u'],
                                    self.fields['pcurve_g']['value']['data']['curve_l'])
            self.fields['pcurve_g']['value'] = self.ground_protection_model.get_evaluated_model(self.fields)
        else:
            self.fields['pcurve_g']['value'] = None


class Fuse(ProtectionDevice):
    """Generic Fuse element"""
    
    code = 'element_fuse'
    name = 'Fuse'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'fuse.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ProtectionDevice.__init__(self, cordinates, **kwargs)
        self.database_path = misc.open_library('fuse.csv')
        self.ports = [[1, 0],
                      [1, 6]]
        # Data drapdowns
        fuse_types = ['LV fuses', 'MV fuses']
        fuse_subtypes_lv = ['gG']
        fuse_prottypes_gg = ['gG IEC']
        pole_types = ['SP', 'TP']
        current_values = [16,20,25,32,40,50,63,80,100,125,160,200,250,315,400,500,630,800,1000,1250]

        self.dict_in = {('LV fuses', 'gG', 'gG IEC'): current_values}
        self.dict_i0 = {}
        self.dict_subtype = {'LV fuses': fuse_subtypes_lv}
        self.dict_prot_curve_type = {('LV fuses', 'gG'): fuse_prottypes_gg}
        self.dict_prot_0_curve_type = {}

        # Set fields
        self.fields.update({'sdfu'       : self.get_field_dict('bool', 'Switch Disconnector ?', '', True)})
        self.fields['type']['selection_list'] = fuse_types
        self.fields['type']['value'] = fuse_types[0]
        self.fields['subtype']['selection_list'] = fuse_subtypes_lv
        self.fields['subtype']['value'] = fuse_subtypes_lv[0]
        self.fields['prot_curve_type']['selection_list'] = fuse_prottypes_gg
        self.fields['prot_curve_type']['value'] = fuse_prottypes_gg[0]
        self.fields['poles']['selection_list'] = pole_types
        self.fields['poles']['value'] = 'TP'
        self.fields['In']['value'] = 63
        self.fields['Isc']['value'] = 50

        self.text_model = [[(3.5,0.5), "${poles}, ${ref}", True],
                           [(3.5,None), "${'%g'%(In)}A, ${type}", True],
                           [(3.5,None), "${'%g'%(Isc)}kA", True],
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
        self.calculate_parameters(init=True)

    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        if self.fields['sdfu']['value']:
            self.schem_model = self.schem_model_sdfu
            self.ports = [[1, 0], [1, 10]]
        else:
            self.schem_model = self.schem_model_fuse
            self.ports = [[1, 0], [1, 6]]
        # Render
        if self.fields['closed']['value'] == True:
            self.render_model(context, self.schem_model)
            self.render_text(context, self.text_model)
        else:
            self.render_model(context, self.schem_model, color=misc.COLOR_INACTIVE)
            self.render_text(context, self.text_model, color=misc.COLOR_INACTIVE)
        # Post processing
        self.modify_extends()

    def get_line_protection_model(self):
        f = FieldDict(self.fields)
        In = f.In
        Isc = f.Isc        

        curve_u = []
        curve_l = []
        parameters = dict()

        # gG fuse data parameters
        ## IEC 60269-1 - (I_min @ 10s, I_max @ 5s, I_min @ 0.1s, I_max @ 0.1s) in A
        gg_current_gates = {  16: [33,65,85,150],
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
        gg_current_gates_prearc = {   16: [0.3,1],
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
        gg_conv_times = { 16: 1,
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

        if f.type == 'LV fuses':
            # gG fuse
            if f.subtype == 'gG':
                if f.prot_curve_type == 'gG IEC':
                    i_nf = 1.25
                    i_f = 1.6
                    t_conv = gg_conv_times[In]
                    (i_min_10, i_max_5, i_min_0_1, I_max_0_1) = gg_current_gates[In]
                    (i2t_min_0_01, i2t_max_0_01) = gg_current_gates_prearc[In]
                    i_min_0_01 = math.sqrt(i2t_min_0_01*1000/0.01)
                    i_max_0_01 = math.sqrt(i2t_max_0_01*1000/0.01)
                    u_points = [ (In*i_f, t_conv*3600),
                                (i_max_5, 5),
                                (I_max_0_1, 0.1)]
                    curve_u = misc.log_interpolate(u_points, num=10)
                    curve_u += [('point', i_max_0_01, 0.01),
                                ('point', 1000*Isc, 0.01)]
                    l_points = [ (In*i_nf, t_conv*3600),
                                (i_min_10, 10),
                                (i_min_0_1,0.1),
                                (i_min_0_01, 0.01)]
                    curve_l = misc.log_interpolate(l_points, num=10)
                    curve_l += [('point', i_min_0_01, 0.001),
                                ('point', 1000*Isc, 0.001)]
                    # Get protection model
                    parameters = dict()
                elif f.subtype == 'gG':
                    curve_u = [ ('point', 'd.i_f*f.In*f.In_set', 'd.t_conv*3600'),
                                ('iec', 1, 'd.i_f*f.In*f.In_set', 80*1.15, 0, 4, 'd.i_f*f.In*f.In_set*1.05', '1000*f.Isc', 0, 10)]
                    curve_l = [ ('point', 'd.i_nf*f.In*f.In_set', 'd.t_conv*3600'),
                                ('iec', 1, 'd.i_nf*f.In*f.In_set', 80*0.85, 0, 4, 'd.i_nf*f.In*f.In_set*1.05', '1000*f.Isc', 0, 10)]
                    # Get protection model
                    parameters = {  'i_nf'  : ['Non fusing current', 'xIr', 1.35, None],
                                    'i_f'   : ['Fusing current', 'xIr', 1.6, None],
                                    't_conv': ['Convensional time', 'Hrs', gg_conv_times[In], None]}
        return parameters, curve_u, curve_l


class CircuitBreaker(ProtectionDevice):
    """Generic circuit breaker element"""
    
    code = 'element_circuitbreaker'
    name = 'Circuit Breaker'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'circuitbreaker.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ProtectionDevice.__init__(self, cordinates, **kwargs)
        self.ports = [[1, 0],
                      [1, 6]]
        pole_types = ['SP', 'SPN', 'DP', 'TP', 'TPN', 'FP']
        current_values_mcb = [6,10,16,20,25,32,40,50,63,80,100]
        current_values_rccb = [25,32,40,63,80,100]
        current_values_0_rccb = [0.03, 0.1, 0.3, 0.5]
        current_values_mccb = [16,20,25,32,40,50,63,80,100,125,160,200,250,320,400,500,630,800,1000]
        current_values_acb = [630,800,1000,1250,1600,2000,2500,3200]

        breaker_types = ['LV breakers', 'MV breakers']
        subtypes_lv = ['MCB','MCCB','ACB','MPCB','CB','RCCB']
        subtypes_mv = ['VCB']
        prottypes_cb = ['EM Trip', 'Digital Trip', 'Instantaneous Trip', 'IEC Inv', 'IEC V Inv', 'IEC E Inv', 'IEEE M Inv', 'IEEE V Inv', 'IEEE E Inv', 'None']
        prottypes_cb_gf = ['None', 'EF Trip', 'EF Trip I2t']
        prottypes_mcb = ['B Curve', 'C Curve', 'D Curve']
        sub_types_rccb = ['Instantaneous', 'Selective']
        self.dict_in = {('LV breakers', 'MCB', '*'): current_values_mcb,
                        ('LV breakers', 'MCCB', '*'): current_values_mccb,
                        ('LV breakers', 'ACB', '*'): current_values_acb,
                        ('LV breakers', 'MPCB', '*'): None,
                        ('LV breakers', 'CB', '*'): None,
                        ('LV breakers', 'RCCB', '*'): current_values_rccb}
        self.dict_i0 = {('LV breakers', 'RCCB', '*'): current_values_0_rccb}
        self.dict_subtype = {'LV breakers': subtypes_lv,
                            'MV breakers': subtypes_mv}
        self.dict_prot_curve_type = {('LV breakers', 'MCB'): prottypes_mcb,
                                     ('LV breakers', 'MCCB'): prottypes_cb,
                                     ('LV breakers', 'ACB'): prottypes_cb,
                                     ('LV breakers', 'MPCB'): prottypes_cb,
                                     ('LV breakers', 'CB'): prottypes_cb,
                                     ('LV breakers', 'RCCB'): ['None'],
                                     ('MV breakers', 'VCB'): prottypes_cb,}
        self.dict_prot_0_curve_type = {('LV breakers', 'RCCB'): sub_types_rccb,
                                        ('LV breakers', 'MCCB'): prottypes_cb_gf,
                                        ('LV breakers', 'ACB'): prottypes_cb_gf,
                                        ('LV breakers', 'CB'): prottypes_cb_gf,
                                        ('MV breakers', 'VCB'): prottypes_cb_gf,}

        self.fields.update({'drawout':  self.get_field_dict('bool', 'Drawout type ?', '', False)})
        self.fields['type']['selection_list'] = breaker_types
        self.fields['type']['value'] = breaker_types[0]
        self.fields['subtype']['selection_list'] = subtypes_lv
        self.fields['subtype']['value'] = subtypes_lv[0]
        self.fields['prot_curve_type']['selection_list'] = prottypes_mcb
        self.fields['prot_curve_type']['value'] = prottypes_mcb[1]
        self.fields['poles']['selection_list'] = pole_types
        self.fields['poles']['value'] = 'TPN'
        self.fields['In']['value'] = 63
        self.fields['Isc']['value'] = 10

        self.text_model = [[(3.5,0.5), "${subtype}, ${poles}, ${ref}", True],
                           [(3.5,None), "${'%g'%(In) + 'A' if In_set == 1 else '%g'%(In) + 'A(' + str(round(In*In_set)) + 'A)'}", True],
                           [(3.5,None), "${'%g'%(Isc)} kA", True],
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
            if  self.fields['subtype']['value'] in ['RCCB']:
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
            
    def get_line_protection_model(self):
        # Get parameters
        f = FieldDict(self.fields)
        In = f.In
        Isc = f.Isc

        curve_u = []
        curve_l = []
        parameters = dict()

        sub_types_mcb_dict = {  'B Curve'     : (2,5),
                                'C Curve'     : (5,10),
                                'D Curve'     : (10,20),
                            }
        prot_type_params = {'IEC Inv'     : (0.14, 0, 0.02),
                            'IEC V Inv'   : (13.5, 0, 1),
                            'IEC E Inv'   : (80, 0, 2),
                            'IEEE M Inv'   : (0.0515, 0.1140, 0.02),
                            'IEEE V Inv'   : (19.61, 0.491, 2),
                            'IEEE E Inv'   : (28.2, 0.1217, 2),
                            }
        if f.type in ('LV breakers', 'MV breakers'):
            
            # MCB IS/IEC 60898
            if f.subtype in ('MCB',):
                i_m_min, i_m_max = sub_types_mcb_dict[self.fields['prot_curve_type']['value']]
                curve_u = [ ('point', '1.45*f.In*f.In_set', 3600),
                            ('iec', 1, '1.42*f.In*f.In_set', 80, 0, 2, 
                                '1.45*f.In*f.In_set', 'd.i_m_max*f.In', 0, 50),
                            ('point', 'd.i_m_max*f.In', 'd.t_ins_max'),
                            ('point', '1000*f.Isc', 'd.t_ins_max')]
                curve_l = [ ('point', '1.13*f.In*f.In_set', 3600),
                            ('iec', 1, '1.12*f.In*f.In_set', 40, 0, 2, 
                                '1.13*f.In*f.In_set', 'd.i_m_min*f.In', 0, 50),
                            ('point', 'd.i_m_min*f.In', 'd.t_ins_min'),
                            ('point', '1000*f.Isc', 'd.t_ins_min')]
                parameters = {'i_m_min'   : ['Magnetic trip (min)', 'xIn', i_m_min, None],
                              'i_m_max'   : ['Magnetic trip (max)', 'xIn', i_m_max, None],
                              't_ins_min' : ['Instantaneous trip time (min)', 's', 0.001, None],
                              't_ins_max' : ['Instantaneous trip time (max)', 's', 0.01, None]}
            
            # CB generic IS/IEC 60947
            elif f.subtype in ('MCCB','ACB','MPCB','CB','VCB'):

                if f.prot_curve_type in ('Instantaneous Trip'):
                    curve_u = [ ('point', '(d.i_m*(100+d.tol_i)/100)*f.In', 3600),
                                ('point', '(d.i_m*(100+d.tol_i)/100)*f.In', 'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max'),
                                ('point', '1000*f.Isc', 'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max')]
                    curve_l = [ ('point', '(d.i_m*(100-d.tol_i)/100)*f.In', 3600),
                                ('point', '(d.i_m*(100-d.tol_i)/100)*f.In', 'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min'),
                                ('point', '1000*f.Isc', 'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min')]
                    parameters = {'i_m'       : ['Instantaneous pickup current', 'xIn', 8, None],
                                  't_ins_min' : ['Instantaneous trip time (min)', 's', 0.001, None],
                                  't_ins_max' : ['Instantaneous trip time (max)', 's', 0.05, None],
                                  't_delay'   : ['Time delay', 's', 0, None],
                                  'tol_i'     : ['Current pickup tolerance', '%', 20, None],
                                  'tol_t'     : ['Time delay tolerance', '%', 20, None]}

                elif f.prot_curve_type in ('EM Trip',):
                    parameters = {'i_m'       : ['Instantaneous pickup current', 'xIn', 8, None],
                                'i_f'      : ['Conventional fusing current', 'xIr', 1.3, None],
                                'i_nf'      : ['Conventional non fusing current', 'xIr', 1.05, None],
                                'tms'       : ['Time multiplier setting', '', 1, None],
                                't_delay'   : ['Line fault delay', 's', 0, None],
                                't_conv'    : ['Convensional time', 'Hrs', 2, None],
                                't_ins_min' : ['Instantaneous trip time (min)', 's', 0.001, None],
                                't_ins_max' : ['Instantaneous trip time (max)', 's', 0.05, None],
                                'k'         : ['k', '', 80, None],
                                'c'         : ['c', '', 0, None],
                                'alpha'     : ['alpha', '', 2, None],
                                'tol_i'     : ['Current pickup tolerance', '%', 20, None],
                                'tol_t'     : ['Time delay tolerance', '%', 20, None]}
                    curve_u = [ ('point', 'd.i_f*f.In*f.In_set', 'd.t_conv*3600'),
                                ('iec', 1, 'd.i_f*f.In*f.In_set', 'd.k*(100+d.tol_t)/100', 'd.c', 'd.alpha', 
                                    'd.i_f*f.In*f.In_set*1.1', '(d.i_m*(100+d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max', 50),
                                ('point', '(d.i_m*(100+d.tol_i)/100)*f.In', 'd.t_ins_max'),
                                ('point', '1000*f.Isc', 'd.t_ins_max')]
                    curve_l = [ ('point', 'd.i_nf*f.In*f.In_set', 'd.t_conv*3600'),
                                ('iec', 1, 'd.i_nf*f.In*f.In_set', 'd.k*(100-d.tol_t)/100', 'd.c', 'd.alpha', 
                                    'd.i_nf*f.In*f.In_set*1.1', '(d.i_m*(100-d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100-d.tol_t)/100 + d.t_ins_max', 50),
                                ('point', '(d.i_m*(100-d.tol_i)/100)*f.In', 'd.t_ins_min'),
                                ('point', '1000*f.Isc', 'd.t_ins_min')]

                elif f.prot_curve_type in ('IEC Inv', 'IEC V Inv', 'IEC E Inv', 'IEEE M Inv', 'IEEE V Inv', 'IEEE E Inv'):
                    k,c,alpha = prot_type_params[f.prot_curve_type]
                    parameters = {'i_m'       : ['Instantaneous pickup current', 'xIn', 8, None],
                                'i_f'      : ['Conventional fusing current', 'xIr', 1.3, None],
                                'i_nf'      : ['Conventional non fusing current', 'xIr', 1.05, None],
                                'tms'       : ['Time multiplier setting', '', 1, None],
                                't_delay'   : ['Line fault delay', 's', 0, None],
                                't_conv'    : ['Convensional time', 'Hrs', 2, None],
                                't_ins_min' : ['Instantaneous trip time (min)', 's', 0.001, None],
                                't_ins_max' : ['Instantaneous trip time (max)', 's', 0.05, None],
                                'tol_i'     : ['Current pickup tolerance', '%', 15, None],
                                'tol_t'     : ['Time delay tolerance', '%', 15, None]}
                    curve_u = [ ('point', 'd.i_f*f.In*f.In_set', 'd.t_conv*3600'),
                                ('iec', 1, 'd.i_f*f.In*f.In_set', str(k) + '*(100+d.tol_t)/100', c, alpha, 
                                    'd.i_f*f.In*f.In_set*1.1', '(d.i_m*(100+d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max', 50),
                                ('point', '(d.i_m*(100+d.tol_i)/100)*f.In', 'd.t_ins_max'),
                                ('point', '1000*f.Isc', 'd.t_ins_max')]
                    curve_l = [ ('point', 'd.i_nf*f.In*f.In_set', 'd.t_conv*3600'),
                                ('iec', 1, 'd.i_nf*f.In*f.In_set', str(k) + '*(100-d.tol_t)/100', c, alpha, 
                                    'd.i_nf*f.In*f.In_set*1.1', '(d.i_m*(100-d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100-d.tol_t)/100 + d.t_ins_max', 50),
                                ('point', '(d.i_m*(100-d.tol_i)/100)*f.In', 'd.t_ins_min'),
                                ('point', '1000*f.Isc', 'd.t_ins_min')]

                elif f.prot_curve_type in ('Digital Trip',):
                    parameters = {'i_nf'       : ['Conventional non fusing current (L)', 'xIr', 1.15, None],
                                'i_s'       : ['Short time pickup current', 'xIn', 8, None],
                                'i_m'       : ['Instantaneous pickup current', 'xIn', 15, None],
                                'tms1'     : ['Time multiplier setting (L)', '', 1, None],
                                'tms2'     : ['Time multiplier setting (S)', '', 1, None],
                                't_delay'   : ['Short time delay', 's', 0, None],
                                't_conv'    : ['Convensional time', 'Hrs', 2, None],
                                't_ins_min' : ['Instantaneous trip time (min)', 's', 0.001, None],
                                't_ins_max' : ['Instantaneous trip time (max)', 's', 0.05, None],
                                'k1'        : ['k (L)', '', 120, None],
                                'alpha1'    : ['alpha (L)', '', 2, [2,4]],
                                'k2'        : ['k (S)', '', 60, None],
                                'alpha2'    : ['alpha (S)', '', 2, [2,4]],
                                'tol_i'     : ['Current pickup tolerance', '%', 10, None],
                                'tol_t'     : ['Time delay tolerance', '%', 10, None]}
                    curve_u = [ ('point', '(d.i_nf*(100+d.tol_i)/100)*f.In*f.In_set', 'd.t_conv*3600'),
                                ('i2t', 'd.tms1', 'f.In*f.In_set', 'd.k1*(100+d.tol_t)/100', 'd.alpha1', 
                                    '(d.i_nf*(100+d.tol_i)/100)*f.In*f.In_set', '(d.i_s*(100+d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max', 50),
                                ('i2t', 'd.tms2', 'f.In*f.In_set', 'd.k2*(100+d.tol_t)/100', 'd.alpha2', 
                                    '(d.i_s*(100+d.tol_i)/100)*f.In', '(d.i_m*(100+d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max', 50),
                                ('point', '(d.i_m*(100+d.tol_i)/100)*f.In', 'd.t_ins_max'),
                                ('point', '1000*f.Isc', 'd.t_ins_max')]
                    curve_l = [ ('point', '(d.i_nf*(100-d.tol_i)/100)*f.In*f.In_set', 'd.t_conv*3600'),
                                ('i2t', 'd.tms1', 'f.In*f.In_set', 'd.k1*(100-d.tol_t)/100', 'd.alpha1', 
                                    '(d.i_nf*(100-d.tol_i)/100)*f.In*f.In_set', '(d.i_s*(100-d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min', 50),
                                ('i2t', 'd.tms2', 'f.In*f.In_set', 'd.k2*(100-d.tol_t)/100', 'd.alpha2', 
                                    '(d.i_s*(100-d.tol_i)/100)*f.In', '(d.i_m*(100-d.tol_i)/100)*f.In', 
                                    'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min', 50),
                                ('point', '(d.i_m*(100-d.tol_i)/100)*f.In', 'd.t_ins_min'),
                                ('point', '1000*f.Isc', 'd.t_ins_min')]
                                
        return parameters, curve_u, curve_l

    def get_ground_protection_model(self):
        f = FieldDict(self.fields)
        In = f.In*f.In_set
        I0 = f.I0
        Isc = f.Isc

        curve_u = []
        curve_l = []
        parameters = dict()
        
        if f.type in ('LV breakers','MV breakers'):

            if f.subtype in ('RCCB',):
                t_ins_min = 0.001
                t_ins_max = 0.01
                if f.prot_0_curve_type in ('Selective',):
                    t_delay = 0.1
                else:
                    t_delay = 0
                curve_u = [ ('point', 'f.I0*f.I0_set', 3600),
                            ('point', 'f.I0*f.I0_set', 'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max'),
                            ('point', '1000*f.Isc', 'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max')]
                curve_l = [ ('point', 'f.I0*f.I0_set*0.5', 3600),
                            ('point', 'f.I0*f.I0_set*0.5', 'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min'),
                            ('point', '1000*f.Isc', 'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min')]
                parameters = {'t_ins_min' : ['Instantaneous trip time (min)', 's', t_ins_min, None],
                              't_ins_max' : ['Instantaneous trip time (max)', 's', t_ins_max, None],
                              't_delay'   : ['Ground fault delay', 's', t_delay, None],
                              'tol_t'     : ['Time delay tolerance', '%', 20, None]}

            elif f.prot_0_curve_type in ('EF Trip' , 'EF Trip I2t'):
                t_ins_min = 0.001
                t_ins_max = 0.01
                if f.prot_0_curve_type in ('EF Trip',):
                    k = 0
                    t_delay = 0.1
                else:
                    k = 1
                    t_delay = 0.1
                curve_u = [ ('point', 'f.I0*f.I0_set*(100+d.tol_i)/100', 3600),
                            ('i2t', 'd.tms', 'f.I0*f.I0_set', 'd.k*(100+d.tol_t)/100', 2, 
                                'f.I0*f.I0_set*(100+d.tol_i)/100', '1000*f.Isc', 
                                'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max', 50),
                            ('point', '1000*f.Isc', 'd.t_delay*(100+d.tol_t)/100 + d.t_ins_max')]
                curve_l = [ ('point', 'f.I0*f.I0_set*(100-d.tol_i)/100', 3600),
                            ('i2t', 'd.tms', 'f.I0*f.I0_set', 'd.k*(100-d.tol_t)/100', 2, 
                                'f.I0*f.I0_set*(100-d.tol_i)/100', '1000*f.Isc', 
                                'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min', 50),
                            ('point', '1000*f.Isc', 'd.t_delay*(100-d.tol_t)/100 + d.t_ins_min')]
                parameters = {  'tms'       : ['Time multiplier setting', '', 1, None],
                                't_ins_min' : ['Instantaneous trip time (min)', 's', t_ins_min, None],
                                't_ins_max' : ['Instantaneous trip time (max)', 's', t_ins_max, None],
                                't_delay'   : ['Ground fault delay', 's', t_delay, None],
                                'k'         : ['k', '', k, None],
                                'tol_i'     : ['Current pickup tolerance', '%', 10, None],
                                'tol_t'     : ['Time delay tolerance', '%', 15, None],}
        return parameters, curve_u, curve_l


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
                       'In':      self.get_field_dict('float', 'In', 'A', 16),
                       'closed':  self.get_field_dict('bool', 'Closed ?', '', True)}
        self.text_model = [[(3.5,1), "${poles}, ${ref}", True],
                           [(3.5,None), "${'%g'%(In)}A, ${type}", True],
                           [(3.5,None), "${name}", True]]
        self.schem_model = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Circle
                             ['ARC', (1,1.5), 0.5, -90, 90, []],
                           ]
