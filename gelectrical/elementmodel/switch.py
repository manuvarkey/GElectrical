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
from ..model.protection import get_protection_model, get_thermal_protection_models


# # Common trip curves to be used accross classes
# def get_trip_curve(curve_type, ground_trip=False):
#     values = ['EM Trip', 'Digital', 'Inverse definite minimum time', 'Inverse Time', 'Definite time', 'Instantaneous', 'None']




class Switch(ElementModel):
    """Generic switching element"""

    code = 'element_switch'
    name = 'Switch'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'switch.svg')
    tooltip = """<b>Switch</b>

Adds a generic switch element.
    
Two elements that are connected through a closed switche are fused in the power flow if the switch is closed or separated if the switch is open.
"""

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
        self.assign_tootltips()
    
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
                        'prot_curve_type':  self.get_field_dict('str', 'Line trip unit', '', '',
                                                             alter_structure=True),
                        'prot_0_curve_type':  self.get_field_dict('str', 'Ground trip unit', '', '',
                                                             alter_structure=True),
                        'poles'      : self.get_field_dict('str', 'Poles', '', 'TP'),
                        'Un'         : self.get_field_dict('float', 'Un', 'kV', 0.415),
                        'In'         : self.get_field_dict('float', 'In', 'A', 63,
                                                            alter_structure=True),
                        'Isc'        : self.get_field_dict('float', 'Isc', 'kA', 50, 
                                                            alter_structure=True),
                        'pcurve_l'   : self.get_field_dict('data', 'Line Protection', '', None, 
                                                            alter_structure=True),
                        'I0'         : self.get_field_dict('float', 'I0', 'A', 63,
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
        self.assign_tootltips()

    def get_line_protection_model(self):
        curves = {}
        parameters = dict()
        return parameters, curves

    def get_ground_protection_model(self):
        curves = {}
        parameters = dict()
        return parameters, curves

    def set_text_field_value(self, code, value):
        ElementModel.set_text_field_value(self, code, value)
        if code in ('type', 'subtype', 'prot_curve_type', 'prot_0_curve_type'):
            # Set subtype
            if self.fields['type']['value'] in self.dict_subtype:
                misc.set_field_selection_list(self.fields, 'subtype', self.dict_subtype[self.fields['type']['value']])
                self.fields['subtype']['status_enable'] = True
            else:
                self.fields['subtype']['selection_list'] = None
                self.fields['subtype']['value'] = 'None'
                self.fields['subtype']['status_enable'] = False

            # Set protection curve
            if (self.fields['type']['value'], self.fields['subtype']['value']) in self.dict_prot_curve_type:
                misc.set_field_selection_list(self.fields, 'prot_curve_type',
                        self.dict_prot_curve_type[(self.fields['type']['value'], self.fields['subtype']['value'])])
                self.fields['prot_curve_type']['status_enable'] = True
            else:
                self.fields['prot_curve_type']['selection_list'] = None
                self.fields['prot_curve_type']['value'] = 'None'
                self.fields['prot_curve_type']['status_enable'] = False
            if (self.fields['type']['value'], self.fields['subtype']['value']) in self.dict_prot_0_curve_type:
                misc.set_field_selection_list(self.fields, 'prot_0_curve_type',
                        self.dict_prot_0_curve_type[(self.fields['type']['value'], self.fields['subtype']['value'])])
                self.fields['prot_0_curve_type']['status_enable'] = True
            else:
                self.fields['prot_0_curve_type']['selection_list'] = None
                self.fields['prot_0_curve_type']['value'] = 'None'
                self.fields['prot_0_curve_type']['status_enable'] = False

            # Set In selection list
            if (self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_curve_type']['value']) in self.dict_in:
                misc.set_field_selection_list(self.fields, 'In', 
                        self.dict_in[(self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_curve_type']['value'])])
            elif (self.fields['type']['value'], self.fields['subtype']['value'], '*') in self.dict_in:
                misc.set_field_selection_list(self.fields, 'In', 
                        self.dict_in[(self.fields['type']['value'], self.fields['subtype']['value'], '*')])
            else:
                self.fields['In']['selection_list'] = None

            # Set I0 selection list
            if (self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_0_curve_type']['value']) in self.dict_i0:
                misc.set_field_selection_list(self.fields, 'I0', 
                        self.dict_i0[(self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_0_curve_type']['value'])])
            elif (self.fields['type']['value'], self.fields['subtype']['value'], '*') in self.dict_i0:
                misc.set_field_selection_list(self.fields, 'I0', 
                        self.dict_i0[(self.fields['type']['value'], self.fields['subtype']['value'], '*')])
            else:
                self.fields['I0']['selection_list'] = None

            # Enable or disable curves
            if self.fields['custom']['value']:
                self.fields['type']['selection_list'] = None
                if self.fields['pcurve_l']['value']:
                    self.fields['pcurve_l']['status_enable'] = True
                elif self.fields['pcurve_g']['value']:
                    self.fields['I0']['status_enable'] = True
                    self.fields['pcurve_g']['status_enable'] = True
            else:
                # Line
                if self.fields['prot_curve_type']['value'] in ('Disabled', 'None', ''):
                    self.fields['pcurve_l']['status_enable'] = False
                else:
                    self.fields['pcurve_l']['status_enable'] = True
                # Ground
                if self.fields['prot_0_curve_type']['value'] in ('Disabled', 'None', ''):
                    self.fields['I0']['status_enable'] = False
                    self.fields['pcurve_g']['status_enable'] = False
                else:
                    self.fields['I0']['status_enable'] = True
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
        parameters, curves = self.get_line_protection_model()
        subtitle = title + ' - ' + 'L'
        if curves:
            self.line_protection_model = ProtectionModel(subtitle, parameters, curves)
            if not init and self.fields['pcurve_l']['value'] is not None:
                self.line_protection_model.update_parameters(self.fields['pcurve_l']['value']['parameters'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_l']['value']:
            self.line_protection_model = ProtectionModel(subtitle, {}, 
                                    self.fields['pcurve_l']['value']['data'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        else:
            self.fields['pcurve_l']['value'] = None
            self.line_protection_model = None
            
        # Set ground protection model
        parameters, curves = self.get_ground_protection_model()
        subtitle = title + ' - ' + 'G'
        if curves:
            self.ground_protection_model = ProtectionModel(subtitle, parameters, curves)
            if not init and self.fields['pcurve_g']['value'] is not None:
                self.ground_protection_model.update_parameters(self.fields['pcurve_g']['value']['parameters'])
            self.fields['pcurve_g']['value'] = self.ground_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_g']['value'] is not None:
            self.ground_protection_model = ProtectionModel(subtitle, {}, 
                                    self.fields['pcurve_g']['value']['data'])
            self.fields['pcurve_g']['value'] = self.ground_protection_model.get_evaluated_model(self.fields)
        else:
            self.fields['pcurve_g']['value'] = None
            self.ground_protection_model = None


class Fuse(ProtectionDevice):
    """Generic Fuse element"""
    
    code = 'element_fuse'
    name = 'Fuse'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'fuse.svg')
    tooltip = """<b>Fuse</b>

Adds a fuse element used for the protection of circuit elements.
"""

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

        self.text_model = [[(3.5,0.5), "${ref}", True],
                           [(3.5,None), "${'%g'%(In) + 'A'}, ${'%g'%(Isc)}kA", True],
                           [(3.5,None), "${poles}, ${type}", True],
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
        self.assign_tootltips()

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
        curves = {}
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
                    curves = {'curve_u': curve_u, 'curve_l': curve_l}
        return parameters, curves


class CircuitBreaker(ProtectionDevice):
    """Generic circuit breaker element"""
    
    code = 'element_circuitbreaker'
    name = 'Circuit Breaker'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'circuitbreaker.svg')
    tooltip = """<b>Circuit Breaker</b>

Adds a circuit breaker element used for the protection of circuit elements.
"""

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
        subtypes_lv = ['MCB','MCCB','ACB','CB', 'MPCB','RCCB']
        subtypes_mv = ['VCB']
        prottypes_mpcb = ['Class 10A', 'Class 10', 'Class 20', 'Class 30']
        prottypes_cb = ['Thermal Magnetic', 'Thermal', 'Magnetic', 'Microprocessor', 'None']
        prottypes_cb_gf = ['None', 'Magnetic']
        prottypes_cb_mv = ['Microprocessor', 'Thermal Magnetic', 'Thermal', 'Magnetic', 'None']
        prottypes_cb_mvgf = ['None', 'Microprocessor', 'Thermal Magnetic', 'Thermal', 'Magnetic']
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
                                     ('LV breakers', 'MPCB'): prottypes_mpcb,
                                     ('LV breakers', 'CB'): prottypes_cb,
                                     ('LV breakers', 'RCCB'): ['None'],
                                     ('MV breakers', 'VCB'): prottypes_cb_mv,}
        self.dict_prot_0_curve_type = {('LV breakers', 'RCCB'): sub_types_rccb,
                                        ('LV breakers', 'MCCB'): prottypes_cb_gf,
                                        ('LV breakers', 'ACB'): prottypes_cb_gf,
                                        ('LV breakers', 'CB'): prottypes_cb_gf,
                                        ('MV breakers', 'VCB'): prottypes_cb_mvgf,}

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

        self.text_model = [[(3.5,0.5), "${ref}", True],
                           [(3.5,None), "${'%g'%(In) + 'A'}, ${'%g'%(Isc)}kA", True],
                           [(3.5,None), "${poles}, ${subtype}", True],
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
        self.assign_tootltips()

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
        f = FieldDict(self.fields)
        curves = {}
        parameters = dict()

        if f.type in ('LV breakers', 'MV breakers'):
            
            # MCB IS/IEC 60898
            if f.subtype in ('MCB',):
                sub_types_mcb_dict = {  'B Curve'     : (2,5),
                                        'C Curve'     : (5,10),
                                        'D Curve'     : (10,20),
                                    }
                i_m_min, i_m_max = sub_types_mcb_dict[self.fields['prot_curve_type']['value']]
                curve_u = [ ('point', '1.45*f.In', 3600),
                            ('IEC', 1, '1.42*f.In', '1.45*f.In', 'd.i_m_max*f.In', 0, 50,
                                80, 0, 2),
                            ('point', 'd.i_m_max*f.In', 'd.t_m_max'),
                            ('point', '1000*f.Isc', 'd.t_m_max')]
                curve_l = [ ('point', '1.13*f.In', 3600),
                            ('IEC', 1, '1.12*f.In', '1.13*f.In', 'd.i_m_min*f.In', 0, 50,
                                40, 0, 2,),
                            ('point', 'd.i_m_min*f.In', 'd.t_m_min'),
                            ('point', '1000*f.Isc', 'd.t_m_min')]
                parameters = {'i_m_min'   : ['Magnetic trip (min)', 'xIn', i_m_min, None],
                              'i_m_max'   : ['Magnetic trip (max)', 'xIn', i_m_max, None],
                              't_m_min' : ['Instantaneous trip time (min)', 's', 0.001, None],
                              't_m_max' : ['Instantaneous trip time (max)', 's', 0.01, None]}
                curves = {'curve_u': curve_u, 'curve_l': curve_l}

            # Thermal overload relay as per IS/IEC 60947-4-1    
            elif f.subtype in ('MPCB',):
                parameters, curves = get_thermal_protection_models(f.prot_curve_type, magnetic=True)
            
            # CB generic IS/IEC 60947    
            elif f.prot_curve_type in ('Thermal',):
                parameters, curves = get_protection_model('Thermal')
            elif f.prot_curve_type in ('Magnetic'):
                parameters, curves = get_protection_model('Magnetic')
            elif f.prot_curve_type in ('Thermal Magnetic',):
                parameters, curves = get_protection_model('Thermal Magnetic')
            elif f.prot_curve_type in ('Microprocessor',):
                parameters, curves = get_protection_model('Microprocessor')

        return parameters, curves

    def get_ground_protection_model(self):
        f = FieldDict(self.fields)
        curves = {}
        parameters = dict()
        
        if f.type in ('LV breakers','MV breakers'):

            if f.subtype in ('RCCB',):
                t_m_min = 0.001
                t_m_max = 0.01
                if f.prot_0_curve_type in ('Selective',):
                    t_delay = 0.1
                    t_delay_enable = True
                    t_inst_enable = False
                else:
                    t_delay = 0
                    t_delay_enable = False
                    t_inst_enable = True
                curve_u = [ ('point', 'f.I0', 3600),
                            ('point', 'f.I0', 'd.t_delay*(100+d.tol_t_p)/100 + d.t_m_max'),
                            ('point', '1000*f.Isc', 'd.t_delay*(100+d.tol_t_p)/100 + d.t_m_max')]
                curve_l = [ ('point', 'f.I0*0.5', 3600),
                            ('point', 'f.I0*0.5', 'd.t_delay*(100-d.tol_t_m)/100 + d.t_m_min'),
                            ('point', '1000*f.Isc', 'd.t_delay*(100-d.tol_t_m)/100 + d.t_m_min')]
                parameters = {'t_m_min' : ['Instantaneous trip time (min)', 's', t_m_min, None, '', 'float', t_inst_enable],
                              't_m_max' : ['Instantaneous trip time (max)', 's', t_m_max, None, '', 'float', t_inst_enable],
                              't_delay' : ['Ground fault delay', 's', t_delay, None, '', 'float', t_delay_enable],
                              'tol_t_p' : ['Time delay tolerance (+)', '%', 10, None],
                              'tol_t_m' : ['Time delay tolerance (-)', '%', 10, None]}
                curves = {'curve_u': curve_u, 'curve_l': curve_l}

            # CB generic IS/IEC 60947    
            elif f.prot_0_curve_type in ('Thermal',):
                parameters, curves = get_protection_model('Thermal', ground_model=True)
            elif f.prot_0_curve_type in ('Magnetic',):
                parameters, curves = get_protection_model('Magnetic', ground_model=True)
            elif f.prot_0_curve_type in ('Thermal Magnetic',):
                parameters, curves = get_protection_model('Thermal Magnetic', ground_model=True)
            elif f.prot_0_curve_type in ('Microprocessor',):
                parameters, curves = get_protection_model('Microprocessor', ground_model=True)
                      
        return parameters, curves


class Contactor(Switch):
    """Generic circuit breaker element"""

    code = 'element_contactor'
    name = 'Contactor'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'contactor.svg')
    tooltip = """<b>Contactor</b>

Adds a contactor element used for on-load switching of loads.
"""

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Switch.__init__(self, cordinates, **kwargs)
        self.ports = [[1, 0],
                      [1, 6]]
        # Data dropdowns
        prottypes_ol = ['Class 10A', 'Class 10', 'Class 20', 'Class 30']
        self.fields = {'custom'     : self.get_field_dict('bool', 'Custom ?', '', False, 
                                                            status_enable=False,
                                                            alter_structure=True),
                        'ref':     self.get_field_dict('str', 'Reference', '', 'K?'),
                        'name':     self.get_field_dict('str', 'Name', '', ''),
                        'type':    self.get_field_dict('str', 'Type', '', 'AC-3'),
                        'poles':   self.get_field_dict('str', 'Poles', '', 'TP'),
                        'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                        'In':      self.get_field_dict('float', 'In', 'A', 16),
                        'closed':  self.get_field_dict('bool', 'Closed ?', '', True),
                        'trip_unit':  self.get_field_dict('bool', 'Trip unit ?', '', False,
                                                          alter_structure=True),
                        'prot_curve_type':  self.get_field_dict('str', 'Trpping class', '', 'Class 10A', 
                                                            selection_list=prottypes_ol,
                                                            alter_structure=True,
                                                            status_enable=False),
                        'Isc'        : self.get_field_dict('float', 'Isc', 'kA', 5, 
                                                            alter_structure=True,
                                                            status_enable=False),
                        'pcurve_l'   : self.get_field_dict('data', 'Line Protection', '', None, 
                                                            alter_structure=True),
                        'pcurve_g'   : self.get_field_dict('data', 'Ground Protection', '', None,
                                                            status_enable=False,
                                                            alter_structure=True)}
        self.fields['pcurve_l']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, 
                                                    misc.GRAPH_PROT_TIME_LIMITS, 
                                                    'CURRENT IN AMPERES', 
                                                    'TIME IN SECONDS', {})
        self.fields['pcurve_g']['graph_options'] = (misc.GRAPH_PROT_CURRENT_LIMITS, 
                                                    misc.GRAPH_PROT_TIME_LIMITS, 
                                                    'CURRENT IN AMPERES', 
                                                    'TIME IN SECONDS', {})
        self.text_model = [[(3.5,1), "${ref}", True],
                           [(3.5,None), "${'%g'%(In)}A, ${type}", True],
                           [(3.5,None), "${poles}", True],
                           [(3.5,None), "${name}", True]]
        self.schem_model_plain = [ 
                             ['LINE',(1,0),(1,2), []],
                             ['LINE',(1,4),(2.5,2), []],
                             ['LINE',(1,4),(1,6), []],
                             # Circle
                             ['ARC', (1,1.5), 0.5, -90, 90, []],
                           ]
        self.schem_model_ol = self.schem_model_plain + [ 
                            # Symbol
                             ['LINE',(1.75,3),(2.15,3.3), [], 'thin'],
                             ['LINE',(2.15,3.3),(2.45,2.9), [], 'thin'],
                             ['LINE',(2.45,2.9), (2.85,3.2), [], 'thin'],
                             ['LINE', (2.85,3.2),(2.55,3.6), [], 'thin'],
                             ['LINE',(2.55,3.6),(2.95,3.9), [], 'thin']]
        self.schem_model = self.schem_model_plain
        self.calculate_parameters(init=True)
        self.assign_tootltips()

    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        if self.fields['trip_unit']['value'] == True:
            self.schem_model = self.schem_model_ol
        else:
            self.schem_model = self.schem_model_plain
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
        # Enable or disable curves
        if self.fields['custom']['value']:
            if self.fields['pcurve_l']['value']:
                self.fields['pcurve_l']['status_enable'] = True
        else:
            # Line
            if self.fields['trip_unit']['value']:
                self.fields['prot_curve_type']['status_enable'] = True
                self.fields['Isc']['status_enable'] = True
                self.fields['pcurve_l']['status_enable'] = True
            else:
                self.fields['prot_curve_type']['status_enable'] = False
                self.fields['Isc']['status_enable'] = False
                self.fields['pcurve_l']['status_enable'] = False
        if not self.model_loading:
            self.calculate_parameters(init=True)


    def set_model_cleanup(self):
        self.calculate_parameters(init=False)

    def calculate_parameters(self, init=False):
        f = FieldDict(self.fields)
        title = self.fields['ref']['value']
        # Set line protection model
        if f.trip_unit:
            parameters, curves = get_thermal_protection_models(f.prot_curve_type, magnetic=False)
        else:
            parameters, curves = {}, {}

        subtitle = title + ' - ' + 'L'
        if curves:
            self.line_protection_model = ProtectionModel(subtitle, parameters, curves)
            if not init and self.fields['pcurve_l']['value'] is not None:
                self.line_protection_model.update_parameters(self.fields['pcurve_l']['value']['parameters'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_l']['value']:
            self.line_protection_model = ProtectionModel(subtitle, {}, 
                                    self.fields['pcurve_l']['value']['data'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        else:
            self.fields['pcurve_l']['value'] = None
            self.line_protection_model = None
        # Set ground protection model
        self.ground_protection_model = None


class ChangeOver(ElementModel):
    """Generic circuit breaker element"""

    code = 'element_co_switch'
    name = 'Changeover switch'
    group = 'Switching Devices'
    icon = misc.abs_path('icons', 'coswitch.svg')
    tooltip = """<b>Changeover switch</b>

Adds a changeover switch element used for on-load switching of sources/ loads.
"""

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.fields = {'ref':     self.get_field_dict('str', 'Reference', '', 'K?'),
                       'name':     self.get_field_dict('str', 'Name', '', ''),
                       'type':    self.get_field_dict('str', 'Type', '', 'AC-23a'),
                       'poles':   self.get_field_dict('str', 'Poles', '', 'TP'),
                       'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                       'In':      self.get_field_dict('float', 'In', 'A', 63),
                       'model':  self.get_field_dict('str', 'Model', '', 'Model 1',
                                                    selection_list=['Model 1', 'Model 2']),
                       'position':  self.get_field_dict('int', 'Position', '', 1,
                                                        selection_list=[1,2])}
        self.text_model = [[(5.5,1), "${ref}", True],
                           [(5.5,None), "${'%g'%(In)}A, ${type}", True],
                           [(5.5,None), "${poles}", True],
                           [(5.5,None), "${name}", True]]
        self.calculate_parameters()
        self.assign_tootltips()
        
    def set_text_field_value(self, code, value):
        ElementModel.set_text_field_value(self, code, value)
        self.calculate_parameters()

    def calculate_parameters(self, init=False):
        if self.fields['model']['value'] == 'Model 1':
            self.ports = [[2, 0],
                        [0, 6],
                        [4, 6]]
            if self.fields['position']['value'] == 1:
                self.schem_model = [ 
                             ['LINE',(2,0),(2,1.5), []],
                             ['LINE',(0,4.5),(0,6), []],
                             ['LINE',(4,4.5),(4,6), []],
                             ['LINE',(2,2),(0,4), []],
                             ['LINE',(2,2),(4,4), [5,5], 'thin'],
                             # Circle
                             ['CIRCLE', (2,2), 0.5, False, []],
                             ['CIRCLE', (0,4), 0.5, False, []],
                             ['CIRCLE', (4,4), 0.5, False, []],
                           ]
            else:
                self.schem_model = [ 
                             ['LINE',(2,0),(2,1.5), []],
                             ['LINE',(0,4.5),(0,6), []],
                             ['LINE',(4,4.5),(4,6), []],
                             ['LINE',(2,2),(0,4), [5,5], 'thin'],
                             ['LINE',(2,2),(4,4), []],
                             # Circle
                             ['CIRCLE', (2,2), 0.5, False, []],
                             ['CIRCLE', (0,4), 0.5, False, []],
                             ['CIRCLE', (4,4), 0.5, False, []],
                           ]
        elif self.fields['model']['value'] == 'Model 2':
            self.ports = [[2, 6],
                        [0, 0],
                        [4, 0]]
            if self.fields['position']['value'] == 1:
                self.schem_model = [ 
                             ['LINE',(2,6),(2,4.5), []],
                             ['LINE',(0,1.5),(0,0), []],
                             ['LINE',(4,1.5),(4,0), []],
                             ['LINE',(2,4),(0,2), []],
                             ['LINE',(2,4),(4,2), [5,5], 'thin'],
                             # Circle
                             ['CIRCLE', (2,4), 0.5, False, []],
                             ['CIRCLE', (0,2), 0.5, False, []],
                             ['CIRCLE', (4,2), 0.5, False, []],
                           ]
            else:
                self.schem_model = [ 
                              ['LINE',(2,6),(2,4.5), []],
                             ['LINE',(0,1.5),(0,0), []],
                             ['LINE',(4,1.5),(4,0), []],
                             ['LINE',(2,4),(0,2), [5,5], 'thin'],
                             ['LINE',(2,4),(4,2), []],
                             # Circle
                             ['CIRCLE', (2,4), 0.5, False, []],
                             ['CIRCLE', (0,2), 0.5, False, []],
                             ['CIRCLE', (4,2), 0.5, False, []],
                           ]
        
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
        power_model = ( ('switch', (p0, p1), {'name': self.fields['ref']['value'],
                                             'closed': self.fields['position']['value'] == 1,
                                             'et': 'b'}),
                        ('switch', (p0, p2), {'name': self.fields['ref']['value'],
                                             'closed': self.fields['position']['value'] == 2,
                                             'et': 'b'}))
        return power_model
