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
        self.list_types = []
        self.dict_subtype = {}
        self.dict_prot_curve_type = {}
        self.dict_prot_0_curve_type = {}
        self.dict_in = {}
        self.dict_i0 = {}
        self.fields.update({'custom'     : self.get_field_dict('bool', 'Custom ?', '', False,
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
        modified = {}

        # If custom enabled, remove protection models
        if code == 'custom' and value is True:
            self.fields['pcurve_l']['value'] = misc.get_blank_data_struct('protection')
            self.fields['pcurve_g']['value'] = misc.get_blank_data_struct('protection')

        # Enable or disable curves based on value of custom
        if self.fields['custom']['value']:
            self.fields['In']['selection_list'] = None
            self.fields['I0']['selection_list'] = None
            self.fields['type']['selection_list'] = None
            self.fields['subtype']['selection_list'] = None
            self.fields['prot_curve_type']['selection_list'] = None
            self.fields['prot_0_curve_type']['selection_list'] = None
            self.fields['type']['status_enable'] = True
            self.fields['subtype']['status_enable'] = True
            self.fields['pcurve_l']['status_inactivate'] = False
            self.fields['pcurve_g']['status_inactivate'] = False
            if self.fields['pcurve_l']['value'] is not None:
                self.fields['pcurve_l']['status_enable'] = True
                self.fields['prot_curve_type']['status_enable'] = True
            else:
                self.fields['pcurve_l']['status_enable'] = False
                self.fields['prot_curve_type']['status_enable'] = False
            if self.fields['pcurve_g']['value'] is not None:
                self.fields['I0']['status_enable'] = True
                self.fields['pcurve_g']['status_enable'] = True
                self.fields['prot_0_curve_type']['status_enable'] = True
            else:
                self.fields['I0']['status_enable'] = False
                self.fields['pcurve_g']['status_enable'] = False
                self.fields['prot_0_curve_type']['status_enable'] = False
        else:
            # Set types
            misc.set_field_selection_list(self.fields, 'type', self.list_types, modified)

            # Set sub type
            if self.fields['type']['value'] in self.dict_subtype:
                misc.set_field_selection_list(self.fields, 'subtype', self.dict_subtype[self.fields['type']['value']],
                                               modified)
                self.fields['subtype']['status_enable'] = True
            else:
                self.fields['subtype']['selection_list'] = None
                self.fields['subtype']['value'] = 'None'
                self.fields['subtype']['status_enable'] = False

            # Set protection curve
            if (self.fields['type']['value'], self.fields['subtype']['value']) in self.dict_prot_curve_type:
                misc.set_field_selection_list(self.fields, 'prot_curve_type',
                        self.dict_prot_curve_type[(self.fields['type']['value'], self.fields['subtype']['value'])], 
                        modified)
                self.fields['prot_curve_type']['status_enable'] = True
            else:
                self.fields['prot_curve_type']['selection_list'] = None
                self.fields['prot_curve_type']['value'] = 'None'
                self.fields['prot_curve_type']['status_enable'] = False
            if (self.fields['type']['value'], self.fields['subtype']['value']) in self.dict_prot_0_curve_type:
                misc.set_field_selection_list(self.fields, 'prot_0_curve_type',
                        self.dict_prot_0_curve_type[(self.fields['type']['value'], self.fields['subtype']['value'])], 
                        modified)
                self.fields['prot_0_curve_type']['status_enable'] = True
            else:
                self.fields['prot_0_curve_type']['selection_list'] = None
                self.fields['prot_0_curve_type']['value'] = 'None'
                self.fields['prot_0_curve_type']['status_enable'] = False

            # Set In selection list
            if (self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_curve_type']['value']) in self.dict_in:
                misc.set_field_selection_list(self.fields, 'In', 
                        self.dict_in[(self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_curve_type']['value'])], 
                        modified)
            elif (self.fields['type']['value'], self.fields['subtype']['value'], '*') in self.dict_in:
                misc.set_field_selection_list(self.fields, 'In', 
                        self.dict_in[(self.fields['type']['value'], self.fields['subtype']['value'], '*')], 
                        modified)
            else:
                self.fields['In']['selection_list'] = None

            # Set I0 selection list
            if (self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_0_curve_type']['value']) in self.dict_i0:
                misc.set_field_selection_list(self.fields, 'I0', 
                        self.dict_i0[(self.fields['type']['value'], self.fields['subtype']['value'], self.fields['prot_0_curve_type']['value'])], 
                        modified)
            elif (self.fields['type']['value'], self.fields['subtype']['value'], '*') in self.dict_i0:
                misc.set_field_selection_list(self.fields, 'I0', 
                        self.dict_i0[(self.fields['type']['value'], self.fields['subtype']['value'], '*')], 
                        modified)
            else:
                self.fields['I0']['selection_list'] = None


            # Line protection model status
            if self.fields['prot_curve_type']['value'] in ('Disabled', 'None', ''):
                self.fields['pcurve_l']['status_enable'] = False
            else:
                self.fields['pcurve_l']['status_enable'] = True
            self.fields['pcurve_l']['status_inactivate'] = True

            # Ground protection model status
            if self.fields['prot_0_curve_type']['value'] in ('Disabled', 'None', ''):
                self.fields['I0']['status_enable'] = False
                self.fields['pcurve_g']['status_enable'] = False
            else:
                self.fields['I0']['status_enable'] = True
                self.fields['pcurve_g']['status_enable'] = True
            self.fields['pcurve_g']['status_inactivate'] = True

        # Update models
        if code in ('custom', 'type', 'subtype', 'prot_curve_type', 'prot_0_curve_type'):
            if not self.model_loading:
                self.calculate_parameters(init=True)
        else:
            if not self.model_loading:
                self.calculate_parameters()

        return modified

    def set_model_cleanup(self):
        self.calculate_parameters()

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
        if self.fields['custom']['value'] is False and curves:
            self.line_protection_model = ProtectionModel(subtitle, parameters, curves)
            # Update parameters if already set
            if self.fields['pcurve_l']['value'] is not None and init is False:
                self.line_protection_model.update_parameters(self.fields['pcurve_l']['value']['parameters'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_l']['value']:
            self.line_protection_model = ProtectionModel(subtitle, self.fields['pcurve_l']['value']['parameters'], 
                                    self.fields['pcurve_l']['value']['data'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        else:
            self.fields['pcurve_l']['value'] = None
            self.line_protection_model = None
            
        # Set ground protection model
        parameters, curves = self.get_ground_protection_model()
        subtitle = title + ' - ' + 'G'
        if self.fields['custom']['value'] is False and curves:
            self.ground_protection_model = ProtectionModel(subtitle, parameters, curves)
            # Update parameters if already set
            if self.fields['pcurve_g']['value'] is not None and init is False:
                self.ground_protection_model.update_parameters(self.fields['pcurve_g']['value']['parameters'])
            self.fields['pcurve_g']['value'] = self.ground_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_g']['value'] is not None:
            self.ground_protection_model = ProtectionModel(subtitle, self.fields['pcurve_g']['value']['parameters'], 
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
        fuse_subtypes_lv = ['gG', 'aM']
        fuse_prottypes_gg = ['gG IEC']
        fuse_prottypes_am = ['aM IEC']
        pole_types = ['SP', 'TP']
        current_values = [2,4,6,10,16,20,25,32,40,50,63,80,100,125,160,200,250,315,400,500,630,800,1000,1250]

        self.dict_in = {('LV fuses', 'gG', 'gG IEC'): current_values,
                        ('LV fuses', 'aM', 'aM IEC'): current_values}
        self.dict_i0 = {}
        self.list_types = fuse_types
        self.dict_subtype = {'LV fuses': fuse_subtypes_lv}
        self.dict_prot_curve_type = {('LV fuses', 'gG'): fuse_prottypes_gg,
                                     ('LV fuses', 'aM'): fuse_prottypes_am}
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
        self.calculate_parameters()
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
        Un = f.Un
        Isc = f.Isc        

        curve_u = []
        curve_l = []
        curves = {}
        parameters = dict()

        # gG fuse data parameters
        ## IEC 60269-1 - (I_min @ 10s, I_max @ 5s, I_min @ 0.1s, I_max @ 0.1s) in A
        gg_current_gates = {    2:  [3.7,9.2,6,23],
                                4:  [7.8,18.5,14,47],
                                6:  [11,28,26,72],
                                10:  [22,46.5,58,110],
            
                                16: [33,65,85,150],
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
        gg_current_gates_prearc = {     2:  [0.001, 0.023],
                                        4:  [0.00625, 0.09025],
                                        6:  [0.024, 0.225],
                                        10: [0.1, 0.576],
                                        16: [0.3,1],
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
        gg_conv_times = {   2:  1,
                            4:  1,
                            6:  1,
                            10: 1,
                            16: 1,
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

        if f.custom is False:
            if f.type == 'LV fuses':
                # gG fuse
                if f.subtype == 'gG':
                    if f.prot_curve_type == 'gG IEC':
                        i_nf = 1.5 if In < 16 else 1.25
                        i_f = 2.1 if In <= 4 else (1.9 if In < 16 else 1.6)
                        t_conv = gg_conv_times[In]
                        (i_min_10, i_max_5, i_min_0_1, I_max_0_1) = gg_current_gates[In]
                        (i2t_min_0_01, i2t_max_0_01) = gg_current_gates_prearc[In]
                        i_min_0_01 = math.sqrt(i2t_min_0_01*1000/0.01)
                        i_max_0_01 = math.sqrt(i2t_max_0_01*1000/0.01)
                        u_points = [ (In*i_f, t_conv*3600),
                                    (i_max_5, 5),
                                    (I_max_0_1, 0.1),
                                    (i_max_0_01, 0.01)]
                        curve_u = [('point', *row) for row in u_points]
                        l_points = [ (In*i_nf, t_conv*3600),
                                    (i_min_10, 10),
                                    (i_min_0_1,0.1),
                                    (i_min_0_01, 0.01)]
                        curve_l = [('point', *row) for row in l_points]
                        # Get protection model
                        parameters = dict()
                        curves = {'curve_u': curve_u, 'curve_l': curve_l}
                if f.subtype == 'aM':
                    if f.prot_curve_type == 'aM IEC':
                        i_nf = 4
                        i_f = 6.3
                        t_conv = gg_conv_times[In]
                        i2t_max_0_01 = 18*In**2 if Un < 400 else (24*In**2 if Un <= 500 else 35*In**2)
                        i_max_0_01 = math.sqrt(i2t_max_0_01/0.01)
                        u_points = [(In*i_f, t_conv*3600),
                                    (6.3*In, 60),
                                    (12.5*In, 0.5),
                                    (19*In, 0.1),
                                    (i_max_0_01, 0.01)]
                        curve_u = [('point', *row) for row in u_points]
                        l_points = [(In*i_nf, t_conv*3600),
                                    (4*In, 60),
                                    (8*In, 0.5),
                                    (10*In, 0.2),
                                    (10*In, 0.01)]
                        curve_l = [('point', *row) for row in l_points]
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
        self.database_path = misc.open_library('cb.csv')
        self.ports = [[1, 0],
                      [1, 6]]
        pole_types = ['SP', 'SPN', 'DP', 'TP', 'TPN', 'FP']
        current_values_mcb = [6,10,16,20,25,32,40,50,63,80,100]
        current_values_rccb = current_values_mcb[:]
        current_values_0_rccb_i = [0.006, 0.01, 0.03, 0.1, 0.3, 0.5, 1, 3, 10, 30]
        current_values_0_rccb_s = [0.1, 0.3, 0.5, 1, 3, 10, 30]
        current_values_mccb = [16,20,25,32,40,50,63,80,100,125,160,200,250,320,400,500,630,800,1000,1250,1600]
        current_values_acb = [630,800,1000,1250,1600,2000,2500,3200,4000,5000,6300]

        breaker_types = ['LV breakers', 'MV breakers']
        subtypes_lv = ['MCB','MCCB','ACB','MPCB','RCCB','RCBO','CB']
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
                        ('LV breakers', 'RCCB', '*'): current_values_rccb,
                        ('LV breakers', 'RCBO', '*'): current_values_rccb}
        self.dict_i0 = {('LV breakers', 'RCCB', 'Instantaneous'): current_values_0_rccb_i,
                        ('LV breakers', 'RCCB', 'Selective'): current_values_0_rccb_s,
                        ('LV breakers', 'RCBO', 'Instantaneous'): current_values_0_rccb_i,
                        ('LV breakers', 'RCBO', 'Selective'): current_values_0_rccb_s}
        self.list_types = breaker_types
        self.dict_subtype = {'LV breakers': subtypes_lv,
                            'MV breakers': subtypes_mv}
        self.dict_prot_curve_type = {('LV breakers', 'MCB'): prottypes_mcb,
                                     ('LV breakers', 'MCCB'): prottypes_cb,
                                     ('LV breakers', 'ACB'): prottypes_cb,
                                     ('LV breakers', 'MPCB'): prottypes_mpcb,
                                     ('LV breakers', 'CB'): prottypes_cb,
                                     ('MV breakers', 'VCB'): prottypes_cb_mv,
                                     ('LV breakers', 'RCBO'): prottypes_mcb,}
        self.dict_prot_0_curve_type = {('LV breakers', 'RCCB'): sub_types_rccb,
                                       ('LV breakers', 'RCBO'): sub_types_rccb,
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
        self.calculate_parameters()
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

        if f.custom is False:
            if f.type in ('LV breakers', 'MV breakers'):
                
                # MCB IS/IEC 60898
                if f.subtype in ('MCB', 'RCBO'):
                    sub_types_mcb_dict = {  'B Curve'     : (3,5),
                                            'C Curve'     : (5,10),
                                            'D Curve'     : (10,20),
                                        }
                    i_m_min, i_m_max = sub_types_mcb_dict[self.fields['prot_curve_type']['value']]
                    i_m_min_s = str(i_m_min)+'*f.In'
                    i_m_max_s = str(i_m_max)+'*f.In'
                    T_conv = '3600 if f.In <= 63  else 2*3600'
                    ku = '125 if f.In <= 32  else 250'
                    kl = 4
                    alphau = 2
                    alphal = 2
                    curve_u = [ ('point', '1.45*f.In', T_conv),
                                ('IEC', 1, '1.45*f.In', '1.5*f.In', i_m_max_s, 0, 50,
                                    ku, 0, alphau),
                                ('point', i_m_max_s, 'd.t_m_max'),
                                ('point', '1000*f.Isc', 'd.t_m_max')]
                    curve_l = [ ('point', '1.13*f.In', T_conv),
                                ('IEC', 1, '1.13*f.In', '1.2*f.In', i_m_min_s, 0, 50,
                                    kl, 0, alphal),
                                ('point', i_m_min_s, 0.001),
                                ('point', '1000*f.Isc', 0.001)]
                    parameters = {'t_m_max' : ['Instantaneous trip time (max)', 's', 0.01, None]}
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
        
        if f.custom is False:
            if f.type in ('LV breakers','MV breakers'):

                if f.subtype in ('RCCB','RCBO'):
                    if f.prot_0_curve_type in ('Selective',):
                        curve_u = [ ('point', 'f.I0', 3600),
                                    ('point', 'f.I0', 0.5),
                                    ('point', '2*f.I0', 0.2),
                                    ('point', '5*f.I0', 0.15),
                                    ('point', '10*f.I0', 0.15),
                                    ('point', '1000*f.Isc', 0.15)]
                        curve_l = [ ('point', 'f.I0*0.5', 3600),
                                ('point', 'f.I0*0.5', 0.06),
                                ('point', '1000*f.Isc', 0.06)]
                        parameters = {}
                    else:
                        curve_u = [ ('point', 'f.I0', 3600),
                                    ('point', 'f.I0', 0.3),
                                    ('point', '2*f.I0', 0.15),
                                    ('point', '5*f.I0 if f.I0 > 0.03 else 0.25', 0.04),
                                    ('point', '10*f.I0 if f.I0 > 0.03 else 0.5', 0.04),
                                    ('point', '1000*f.Isc', 0.04)]
                        curve_l = [ ('point', 'f.I0*0.5', 3600),
                                    ('point', 'f.I0*0.5', 0.001),
                                    ('point', '1000*f.Isc', 0.001)]
                        parameters = {}
                    
                    
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
        self.prottypes_ol = ['Class 10A', 'Class 10', 'Class 20', 'Class 30']
        self.fields = { 'ref':     self.get_field_dict('str', 'Reference', '', 'K?'),
                        'name':     self.get_field_dict('str', 'Name', '', ''),
                        'type':    self.get_field_dict('str', 'Type', '', 'AC-3'),
                        'poles':   self.get_field_dict('str', 'Poles', '', 'TP'),
                        'Un':      self.get_field_dict('float', 'Un', 'kV', 0.415),
                        'In':      self.get_field_dict('float', 'In', 'A', 16),
                        'closed':  self.get_field_dict('bool', 'Closed ?', '', True),
                        'custom'     : self.get_field_dict('bool', 'Custom ?', '', False, 
                                                            alter_structure=True),
                        'trip_unit':  self.get_field_dict('bool', 'Trip unit ?', '', False,
                                                          alter_structure=True),
                        'prot_curve_type':  self.get_field_dict('str', 'Trpping class', '', 'Class 10A', 
                                                            selection_list=self.prottypes_ol,
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
        self.calculate_parameters()
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
        modified = {}
        # If custom enabled, remove protection models
        if code == 'custom' and value is True:
            self.fields['pcurve_l']['value'] = misc.get_blank_data_struct('protection')

        # Handle case when custom is enabled
        if self.fields['custom']['value']:
            self.fields['prot_curve_type']['selection_list'] = None
        else:
            misc.set_field_selection_list(self.fields, 'prot_curve_type', self.prottypes_ol, modified)

        # Handle case when trip unit is enabled
        if self.fields['trip_unit']['value']:
            self.fields['prot_curve_type']['status_enable'] = True
            self.fields['Isc']['status_enable'] = True
            self.fields['pcurve_l']['status_enable'] = True
        else:
            self.fields['prot_curve_type']['status_enable'] = False
            self.fields['Isc']['status_enable'] = False
            self.fields['pcurve_l']['status_enable'] = False

        if not self.model_loading:
            self.calculate_parameters()
        return modified


    def set_model_cleanup(self):
        self.calculate_parameters()

    def calculate_parameters(self):
        f = FieldDict(self.fields)
        title = self.fields['ref']['value']
        # Set line protection model
        if f.trip_unit is True and f.custom is False:
            parameters, curves = get_thermal_protection_models(f.prot_curve_type, magnetic=False)
        else:
            parameters, curves = {}, {}

        subtitle = title + ' - ' + 'L'
        if self.fields['custom']['value'] is False and curves:
            self.line_protection_model = ProtectionModel(subtitle, parameters, curves)
            # Use parameters from saved model if available
            if self.fields['pcurve_l']['value'] is not None:
                self.line_protection_model.update_parameters(self.fields['pcurve_l']['value']['parameters'])
            self.fields['pcurve_l']['value'] = self.line_protection_model.get_evaluated_model(self.fields)
        elif self.fields['custom']['value'] and self.fields['pcurve_l']['value']:
            self.line_protection_model = ProtectionModel(subtitle, self.fields['pcurve_l']['value']['parameters'], 
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

    def calculate_parameters(self):
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
