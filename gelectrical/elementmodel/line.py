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

import os, cairo, math, copy
from gi.repository import PangoCairo

# local files import
from .. import misc
from .element import ElementModel


class Line(ElementModel):
    
    code = 'element_line'
    name = 'Line'
    group = 'Components'
    icon = misc.abs_path('icons', 'line.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        ElementModel.__init__(self, cordinates, **kwargs)
        self.database_path = misc.abs_path('database', 'line.csv')
        self.model_width = 0
        self.model_height = 0
        self.ports = [[2, 0], [2, 8]]
        self.fields = {'ref':           self.get_field_dict('str', 'Reference', '', 'W?'),
                       'name':          self.get_field_dict('str', 'Name', '', ''),
                       'length_km':     self.get_field_dict('float', 'Length', 'km', 1),
                       'r_ohm_per_km':  self.get_field_dict('float', 'R', 'Ohm/km', 0.1),
                       'x_ohm_per_km':  self.get_field_dict('float', 'X', 'Ohm/km', 0.1),
                       'c_nf_per_km':   self.get_field_dict('float', 'C', 'nF/km', 0),
                       'g_us_per_km':   self.get_field_dict('float', 'G', 'uS/km', 0),
                       'r0n_ohm_per_km': self.get_field_dict('float', 'R0n', 'Ohm/km', 0),
                       'x0n_ohm_per_km': self.get_field_dict('float', 'X0n', 'Ohm/km', 0),
                       'c0n_nf_per_km':  self.get_field_dict('float', 'C0n', 'nF/km', 0),
                       'r0g_ohm_per_km': self.get_field_dict('float', 'R0g', 'Ohm/km', 0),
                       'x0g_ohm_per_km': self.get_field_dict('float', 'X0g', 'Ohm/km', 0),
                       'c0g_nf_per_km':  self.get_field_dict('float', 'C0g', 'nF/km', 0),
                       'endtemp_degree':self.get_field_dict('float', 'Tf', 'degC', 160),
                       'max_i_ka':      self.get_field_dict('float', 'Imax', 'kA', 1),
                       'phase_sc_current_rating': self.get_field_dict('float', 'Isc phase (1s)', 'kA', 0),
                       'cpe_sc_current_rating': self.get_field_dict('float', 'Isc cpe (1s)', 'kA', 0),
                       'df':            self.get_field_dict('float', 'DF', '', 1),
                       'designation':   self.get_field_dict('str', 'Designation', '', ''),
                       'type':          self.get_field_dict('str', 'Type of Line', '', 'Under Ground', selection_list=['Over Head','Under Ground']),
                       'parallel':      self.get_field_dict('int', '# Parallel Lines', '', 1),
                       'in_service':    self.get_field_dict('bool', 'In Service ?', '', True)}
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "${length_km}km", True],
                           [(3,None), "${name}", True]]
    
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        if self.fields['type']['value'] == 'Over Head':
            self.schem_model = [ 
                             ['LINE',(2,0),(2,8), []],
                             # Symbol
                             ['CIRCLE', (2,4), 0.5, False, [], 'thin']
                           ]
        else:
            self.schem_model = [ 
                             ['LINE',(2,0),(2,8), []],
                             # Symbol
                             ['LINE',(0.5,3.25),(0.5,4.75), [], 'thin'],
                             ['LINE',(1,3.5),(1,4.5), [], 'thin'],
                             ['LINE',(1.5,3.75),(1.5,4.25), [], 'thin'],
                           ]
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
        line_type = self.fields['r_ohm_per_km']['value']
        if line_type == 'Over Head':
            line_type_code = 'ol'
        else:
            line_type_code = 'cs'
        p0 = code + ':0'
        p1 = code + ':1'
        if mode == misc.POWER_MODEL_POWERFLOW:
            power_model = (('line', (p0,p1), {'name': self.fields['ref']['value'],
                                        'length_km': self.fields['length_km']['value'],
                                        'r_ohm_per_km': self.fields['r_ohm_per_km']['value'],
                                        'x_ohm_per_km': self.fields['x_ohm_per_km']['value'],
                                        'c_nf_per_km': self.fields['c_nf_per_km']['value'],
                                        'r0_ohm_per_km': self.fields['r0n_ohm_per_km']['value'],
                                        'x0_ohm_per_km': self.fields['x0n_ohm_per_km']['value'],
                                        'c0_nf_per_km': self.fields['c0n_nf_per_km']['value'],
                                        'g_us_per_km': self.fields['g_us_per_km']['value'],
                                        'endtemp_degree': self.fields['endtemp_degree']['value'],
                                        'max_i_ka': self.fields['max_i_ka']['value'],
                                        'df': self.fields['df']['value'],
                                        'type': line_type_code,
                                        'parallel': self.fields['parallel']['value'],
                                        'in_service': self.fields['in_service']['value'],}),)
        elif mode == misc.POWER_MODEL_GROUNDFAULT:
            power_model = (('line', (p0,p1), {'name': self.fields['ref']['value'],
                                        'length_km': self.fields['length_km']['value'],
                                        'r_ohm_per_km': self.fields['r_ohm_per_km']['value'],
                                        'x_ohm_per_km': self.fields['x_ohm_per_km']['value'],
                                        'c_nf_per_km': self.fields['c_nf_per_km']['value'],
                                        'r0_ohm_per_km': self.fields['r0g_ohm_per_km']['value'],
                                        'x0_ohm_per_km': self.fields['x0g_ohm_per_km']['value'],
                                        'c0_nf_per_km': self.fields['c0g_nf_per_km']['value'],
                                        'g_us_per_km': self.fields['g_us_per_km']['value'],
                                        'endtemp_degree': self.fields['endtemp_degree']['value'],
                                        'max_i_ka': self.fields['max_i_ka']['value'],
                                        'df': self.fields['df']['value'],
                                        'type': line_type_code,
                                        'parallel': self.fields['parallel']['value'],
                                        'in_service': self.fields['in_service']['value'],}),)
            
        return power_model


class LTCableIEC(Line):
    """Cable element"""

    code = 'element_line_cable'
    name = 'LV Cable (IEC)'
    group = 'Components'
    icon = misc.abs_path('icons', 'line.svg')
        
    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Line.__init__(self, cordinates, **kwargs)
        self.database_path = misc.abs_path('database', 'cable_iec.csv')
        self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        
        # Data dropdowns
        self.laying_types = ['Reference method A1 - \nInsulated conductors in conduit \nin a thermally insulated wall', 
                        'Reference method A2 - \nMulti-core cable in conduit \nin a thermally insulated wall',
                        'Reference method B1 - \nInsulated conductors in conduit \non a wooden wall', 
                        'Reference method B2 - \nMulti-core cable in conduit \non a wooden wall',
                        'Reference method C - \nMulti-core cable \non a wooden wall',
                        'Reference method D1 - \nMulti-core cable in ducts \nin the ground',
                        'Reference method D2 - \nMulti-core cable\nin the ground',
                        'Reference method E - \nMulti-core cable \nin free air',]
        self.laying_types_images = ['cable_iec_a1.svg',
                                    'cable_iec_a2.svg',
                                    'cable_iec_b1.svg',
                                    'cable_iec_b2.svg',
                                    'cable_iec_c.svg',
                                    'cable_iec_d1.svg',
                                    'cable_iec_d2.svg',
                                    'cable_iec_e.svg']
        self.conductor_materials = ['Copper','Aluminium']
        self.insulation_materials = ['PVC', 'XLPE/EPR']
        self.cpe_list = ['None', 'Neutral', 'As an additional core\nin cable/ conduit', 
                         'Cable armour', 'External CPE conductor', 
                         'Armour in parallel\nwith external CPC conductor']
        self.cpe_materials = ['Copper','Aluminium','Steel']
        self.cpe_insulation = ['PVC','XLPE/EPR']
        self.material_code = {'Copper':'Cu','Aluminium':'Al','Steel':'Fe'}
        self.insulation_code = {'PVC':'Y', 'XLPE/EPR':'2X'}
        self.insulation_max_working_temp_dict = {'PVC': 70, 'XLPE/EPR': 90}
        self.insulation_ultimate_working_temp_dict = {'PVC': 160, 'XLPE/EPR': 250}
        self.conductor_ultimate_working_temp_dict = {'Copper': 395, 'Aluminium': 325, 'Steel': 500}
        self.conductor_B_dict = {'Copper':234.5,'Aluminium':228,'Steel':202}
        self.conductor_Qc_dict = {'Copper':3.45e-3,'Aluminium':2.5e-3,'Steel':3.8e-3}
        self.conductor_delta20_dict = {'Copper':17.241e-6,'Aluminium':28.264e-6,'Steel':138e-6}
        ground_arrangements_1 = ['Ducts touching', 'Spaced 0.25m', 'Spaced 0.5m', 'Spaced 1.0m']
        ground_arrangements_2 = ['Cables touching', 'Spaced one cable dia', 'Spaced 0.125m', 'Spaced 0.25m', 'Spaced 0.5m']
        surface_arrangements = ['Bunched', 'Single layer on wall, floor',  'Single layer fixed directly\nunder a wooden ceiling']
        air_arrangements = ['Perforated cable tray\n(Touching)', 
                            'Perforated cable tray\n(Spaced)',
                            'Vertical Perforated cable tray\n(Touching)',
                            'Vertical Perforated cable tray\n(Spaced)', 
                            'Unperforated cable tray\n(Touching)', 
                            'Cable ladder/ cleats\n(Touching)',
                            'Cable ladder/ cleats\n(Spaced)']
        self.laying_arrangements_dict = {self.laying_types[0]: ['Bunched'],
                                 self.laying_types[1]: ['Bunched'],
                                 self.laying_types[2]: ['Bunched'],
                                 self.laying_types[3]: ['Bunched'],
                                 self.laying_types[4]: surface_arrangements,
                                 self.laying_types[5]: ground_arrangements_1,
                                 self.laying_types[6]: ground_arrangements_2,
                                 self.laying_types[7]: air_arrangements}
        cross_sections_cu = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
        cross_sections_al = [2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240, 300]
        self.cross_section_dict = {self.conductor_materials[0]: cross_sections_cu,
                                   self.conductor_materials[1]: cross_sections_al,}
        ambient_temps_pvc = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        ambient_temps_xlpe = [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80]
        self.ambient_temp_dict = {self.insulation_materials[0]: ambient_temps_pvc,
                                  self.insulation_materials[1]: ambient_temps_xlpe}
        no_groups_abc_1 = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '12', '16', '20']
        no_groups_abc_2 = ['1', '2', '3', '4', '5', '6', '7', '8', '>8']
        no_groups_d = ['1', '2', '3', '4', '5', '6']
        no_groups_e_1 = ['1', '2', '3', '4', '6', '9']
        no_groups_e_2 = ['1', '2', '3', '4', '6']
        self.no_groups_dict = {(0,0) : no_groups_abc_1,
                               (1,0) : no_groups_abc_1,
                               (2,0) : no_groups_abc_1,
                               (3,0) : no_groups_abc_1,
                               (4,0) : no_groups_abc_2,
                               (4,1) : no_groups_abc_2,
                               (4,2) : no_groups_abc_2,
                               (5,0) : no_groups_d,
                               (5,1) : no_groups_d,
                               (5,2) : no_groups_d,
                               (5,3) : no_groups_d,
                               (6,0) : no_groups_d,
                               (6,1) : no_groups_d,
                               (6,2) : no_groups_d,
                               (6,3) : no_groups_d,
                               (6,4) : no_groups_d,
                               (7,0) : no_groups_e_1,
                               (7,1) : no_groups_e_2,
                               (7,2) : no_groups_e_1,
                               (7,3) : no_groups_e_2,
                               (7,4) : no_groups_e_1,
                               (7,5) : no_groups_e_1,
                               (7,6) : no_groups_e_2}
        self.no_layers_dict = {(0,0) : ['1'],
                               (1,0) : ['1'],
                               (2,0) : ['1'],
                               (3,0) : ['1'],
                               (4,0) : ['1'],
                               (4,1) : ['1'],
                               (4,2) : ['1'],
                               (5,0) : ['1'],
                               (5,1) : ['1'],
                               (5,2) : ['1'],
                               (5,3) : ['1'],
                               (6,0) : ['1'],
                               (6,1) : ['1'],
                               (6,2) : ['1'],
                               (6,3) : ['1'],
                               (6,4) : ['1'],
                               (7,0) : ['1', '2', '3', '6'],
                               (7,1) : ['1', '2', '3'],
                               (7,2) : ['1', '2'],
                               (7,3) : ['1', '2'],
                               (7,4) : ['1', '2', '3', '6'],
                               (7,5) : ['1', '2', '3', '6'],
                               (7,6) : ['1', '2', '3']}
        self.soil_thermal_resistivities = [0.5, 0.8, 1, 1.5, 2, 2.5, 3]
        
        # Data current ratings (table)
        #                PVC    XLPE/EPR
        # Laying type 1
        # Laying type 2
        #    ...
        # Laying type n
        #
        self.current_rating_table_al_1ph = [[ [[0,300,8.61,0.616]], [[0,300,11.6,0.615]] ],
                                            [ [[0,120,8.361,0.6025],[120,300,7.84,0.616]], [[0,120,11.26,0.602],[120,300,10.56,0.615]] ],
                                            [ [[0,300,10.51,0.6254]], [[0,300,13.95,0.627]] ],
                                            [ [[0,300,10.24,0.5994]], [[0,300,13.5,0.603]] ],
                                            [ [[0,16,11.6,0.625],[16,300,10.55,0.640]], [[0,16,14.8,0.625],[16,300,12.6,0.648]] ],
                                            [ [[0,300,13.6,0.540]], [[0,300,15.82,0.541]] ],
                                            [ [[0,300,1.1*13.6,0.540]], [[0,300,1.1*15.82,0.541]] ],
                                            [ [[0,16,12.8,0.627],[16,300,11.4,0.64]], [[0,16,16.0,0.625],[16,300,13.4,0.649]] ],
                                           ]
        self.current_rating_table_al_3ph = [[ [[0,300,7.94,0.612]], [[0,300,10.9,0.605]] ],
                                            [ [[0,120,7.712,0.5984],[120,300,7.225,0.612]], [[0,120,10.58,0.592],[120,300,9.92,0.605]] ],
                                            [ [[0,300,9.265,0.627]], [[0,300,12.3,0.630]] ],
                                            [ [[0,300,9.03,0.601]], [[0,300,11.95,0.605]] ],
                                            [ [[0,16,10.5,0.625],[16,300,9.536,0.6324]], [[0,16,13.5,0.625],[16,300,11.5,0.639]] ],
                                            [ [[0,300,11.2,0.542]], [[0,300,13.2,0.539]] ],
                                            [ [[0,300,1.1*11.2,0.542]], [[0,300,1.1*13.2,0.539]] ],
                                            [ [[0,16,11.0,0.62],[16,300,9.9,0.64]], [[0,16,13.7,0.623],[16,300,12.6,0.635]] ],
                                           ]
        self.current_rating_table_cu_1ph = [[ [[0,300,11.2,0.6118]], [[0,300,14.9,0.611]] ],
                                            [ [[0,120,10.8,0.6015],[120,300,10.19,0.6118]], [[0,120,14.46,0.598],[120,300,13.56,0.611]] ],
                                            [ [[0,300,13.5,0.625]], [[0,300,17.76,0.6250]] ],
                                            [ [[0,300,13.1,0.600]], [[0,300,17.25,0.600]] ],
                                            [ [[0,16,15.0,0.625],[16,300,15.0,0.625]], [[0,16,18.77,0.628],[16,300,17.0,0.650]] ],
                                            [ [[0,300,17.42,0.540]], [[0,300,20.25,0.542]] ],
                                            [ [[0,300,1.1*17.42,0.540]], [[0,300,1.1*20.25,0.542]] ],
                                            [ [[0,16,16.8,0.62],[16,300,14.9,0.646]], [[0,16,20.5,0.623],[16,300,18.6,0.646]] ],
                                           ]
        self.current_rating_table_cu_3ph = [[ [[0,300,10.4,0.605]], [[0,300,13.34,0.611]] ],
                                            [ [[0,120,10.1,0.592],[120,300,9.462,0.605]], [[0,120,12.95,0.598],[120,300,12.14,0.611]] ],
                                            [ [[0,300,11.84,0.628]], [[0,300,15.62,0.6252]] ],
                                            [ [[0,300,11.65,0.6005]], [[0,300,15.17,0.6]] ],
                                            [ [[0,16,13.5,0.625],[16,300,12.4,0.635]], [[0,16,17,0.623],[16,300,15.4,0.635]] ],
                                            [ [[0,300,14.34,0.542]], [[0,300,16.88,0.539]] ],
                                            [ [[0,300,1.1*14.34,0.542]], [[0,300,1.1*16.88,0.539]] ],
                                            [ [[0,16,14.3,0.62],[16,300,12.9,0.64]], [[0,16,17.8,0.623],[16,300,16.4,0.637]] ],
                                           ]
                                                                                      
        # Data reduction factors
        df_ab_1 = [[1,0.8,0.7,0.65,0.6,0.57,0.54,0.52,0.5,0.45,0.41,0.38]]
        df_c_1 = [[1,0.85,0.79,0.75,0.73,0.72,0.72,0.71,0.7]]
        df_c_2 = [[0.95,0.81,0.72,0.68,0.66,0.64,0.63,0.62,0.61]]            
        df_c_3 = [[1,0.88,0.82,0.77,0.75,0.73,0.73,0.72,0.72]]            
        df_d_11 = [[1,0.75,0.65,0.6,0.55,0.5]]
        df_d_12 = [[1,0.8,0.7,0.6,0.55,0.55]]
        df_d_13 = [[1,0.85,0.75,0.7,0.65,0.6]]
        df_d_14 = [[1,0.9,0.8,0.75,0.7,0.7]]
        df_d_15 = [[1,0.9,0.85,0.8,0.8,0.8]]
        df_d_21 = [[1,0.85,0.75,0.7,0.65,0.6]]
        df_d_22 = [[1,0.9,0.85,0.8,0.8,0.8]]
        df_d_23 = [[1,0.95,0.9,0.85,0.85,0.8]]
        df_d_24 = [[1,0.95,0.95,0.9,0.9,0.9]]
        df_e_1 = [[1,0.88,0.82,0.79,0.76,0.73],[1,0.87,0.8,0.77,0.73,0.68],[1,0.86,0.79,0.76,0.71,0.66],[1,0.84,0.77,0.73,0.68,0.64]]
        df_e_2 = [[1,1,0.98,0.95,0.91],[1,0.99,0.96,0.92,0.87],[1,0.98,0.95,0.91,0.85]]
        df_e_3 = [[1,0.88,0.82,0.78,0.73,0.72],[1,0.88,0.81,0.76,0.71,0.7]]
        df_e_4 = [[1,0.91,0.89,0.88,0.87],[1,0.91,0.88,0.87,0.85]]
        df_e_5 = [[0.97,0.84,0.78,0.75,0.71,0.68],[0.97,0.83,0.76,0.72,0.68,0.63],[0.97,0.82,0.75,0.71,0.66,0.61],[0.97,0.81,0.73,0.69,0.63,0.58]]
        df_e_6 = [[1,0.87,0.82,0.8,0.79,0.78],[1,0.86,0.8,0.78,0.76,0.73],[1,0.85,0.79,0.76,0.73,0.7],[1,0.84,0.77,0.73,0.68,0.64]]
        df_e_7 = [[1,1,1,1,1],[1,0.99,0.98,0.97,0.96],[1,0.98,0.97,0.96,0.93]]
        self.df_dict = {(0,0) : df_ab_1,
                        (1,0) : df_ab_1,
                        (2,0) : df_ab_1,
                        (3,0) : df_ab_1,
                        (4,0) : df_c_1,
                        (4,1) : df_c_2,
                        (4,2) : df_c_3,
                        (5,0) : df_d_21,
                        (5,1) : df_d_22,
                        (5,2) : df_d_23,
                        (5,3) : df_d_24,
                        (6,0) : df_d_11,
                        (6,1) : df_d_12,
                        (6,2) : df_d_13,
                        (6,3) : df_d_14,
                        (6,4) : df_d_15,
                        (7,0) : df_e_1,
                        (7,1) : df_e_2,
                        (7,2) : df_e_3,
                        (7,3) : df_e_4,
                        (7,4) : df_e_5,
                        (7,5) : df_e_6,
                        (7,6) : df_e_7}
        self.ambient_temp_pvc_df = [1.22,1.17,1.12,1.06,1,0.94,0.87,0.79,0.71,0.61,0.5]
        self.ambient_temp_xlpe_df = [1.15,1.12,1.08,1.04,1,0.96,0.91,0.87,0.82,0.76,0.71,0.65,0.58,0.5,0.41]
        self.ground_temp_pvc_df = [1.1,1.05,1,0.95,0.89,0.84,0.77,0.71,0.63,0.55,0.45]
        self.ground_temp_xlpe_df = [1.07,1.04,1,0.96,0.93,0.89,0.85,0.8,0.76,0.71,0.65,0.6,0.53,0.46,0.38]
        self.soil_resistivity_direct_df = [1.88,1.62,0.15,1.28,1.12,1,0.9]
        self.soil_resistivity_duct_df = [1.28,1.2,1.18,1.1,1.05,1,0.96]
        
        # Schematic models
        self.schem_model_ug = [ ['LINE',(2,0),(2,8), []],
                                # Symbol
                                ['LINE',(0.5,3.25),(0.5,4.75), [], 'thin'],
                                ['LINE',(1,3.5),(1,4.5), [], 'thin'],
                                ['LINE',(1.5,3.75),(1.5,4.25), [], 'thin'] ]
        self.schem_model_conduit = [ ['LINE',(2,0),(2,8), []],
                                     # Symbol
                                     ['CIRCLE', (1,4), 0.5, False, [], 'thin'] ]
        self.schem_model_surface = [ ['LINE',(2,0),(2,8), []],
                                     # Symbol
                                     ['LINE',(1.5,0.5),(1.5,1.5), [], 'thin'],
                                     ['LINE',(1,0),(1.5,0.5), [], 'thin'],
                                     ['LINE',(1,0.5),(1.5,1), [], 'thin'],
                                     ['LINE',(1,1),(1.5,1.5), [], 'thin'],
                                     ['LINE',(1.5,6.5),(1.5,7.5), [], 'thin'],
                                     ['LINE',(1,6),(1.5,6.5), [], 'thin'],
                                     ['LINE',(1,6.5),(1.5,7), [], 'thin'],
                                     ['LINE',(1,7),(1.5,7.5), [], 'thin'], ]
        self.schem_models_dict = {self.laying_types[0]: self.schem_model_conduit,
                                 self.laying_types[1]: self.schem_model_conduit,
                                 self.laying_types[2]: self.schem_model_conduit,
                                 self.laying_types[3]: self.schem_model_conduit,
                                 self.laying_types[4]: self.schem_model_surface,
                                 self.laying_types[5]: self.schem_model_ug,
                                 self.laying_types[6]: self.schem_model_ug,
                                 self.laying_types[7]: self.schem_model_surface}
                                                                                       
        # Modify existing fields
        self.fields['r_ohm_per_km']['status_inactivate'] = True
        self.fields['g_us_per_km']['status_enable'] = False
        self.fields['r0g_ohm_per_km']['status_inactivate'] = True
        self.fields['x0g_ohm_per_km']['status_inactivate'] = True
        self.fields['r0n_ohm_per_km']['status_inactivate'] = True
        self.fields['x0n_ohm_per_km']['status_inactivate'] = True
        self.fields['c0g_nf_per_km']['status_enable'] = False
        self.fields['c0n_nf_per_km']['status_enable'] = False
        self.fields['endtemp_degree']['status_inactivate'] = True
        self.fields['max_i_ka']['status_inactivate'] = True
        self.fields['type']['status_enable'] = False
        self.fields['type']['value'] = 'Under Ground'
        self.fields['phase_sc_current_rating']['status_inactivate'] = True
        self.fields['cpe_sc_current_rating']['status_inactivate'] = True
        self.fields['df']['status_inactivate'] = True
        self.fields['length_km']['alter_structure'] = True
        
        # Add new fields
        self.fields['conductor_material'] = self.get_field_dict('str', 'Conductor material', '', self.conductor_materials[0], 
                                                                selection_list=self.conductor_materials,
                                                                alter_structure=True)
        self.fields['insulation_material'] = self.get_field_dict('str', 'Insulation', '', self.insulation_materials[0], 
                                                                 selection_list=self.insulation_materials,
                                                                 alter_structure=True)
        self.fields['conductor_cross_section'] = self.get_field_dict('float', 'Phase nominal\ncross-sectional area', 'sq.mm.', 
                                                                     25, selection_list=cross_sections_cu,
                                                                     alter_structure=True)
        self.fields['neutral_xsec'] = self.get_field_dict('float', 'Neutral cross-sectional area', 'xSph', 1,
                                                          alter_structure=True)
        self.fields['type_of_cable'] = self.get_field_dict('str', 'Type', '', '3ph', selection_list=['1ph','3ph'],
                                                           alter_structure=True)
        self.fields['cpe'] = self.get_field_dict('str', 'CPE Conductor', '', self.cpe_list[1], 
                                                 selection_list=self.cpe_list,
                                                 alter_structure=True,)
        self.fields['armour_material'] = self.get_field_dict('str', 'Armour material', '', self.cpe_materials[0], 
                                                                selection_list=self.cpe_materials,
                                                                alter_structure=True,
                                                                status_enable=False)
        self.fields['armour_cross_section'] = self.get_field_dict('float', 'Armour nominal\ncross-sectional area', 'sq.mm.', 
                                                                  0, alter_structure=True,
                                                                  status_enable=False)
        self.fields['cpe_material'] = self.get_field_dict('str', 'CPE material', '', self.cpe_materials[0], 
                                                                selection_list=self.cpe_materials,
                                                                alter_structure=True,
                                                                status_enable=False)
        self.fields['cpe_insulation'] = self.get_field_dict('str', 'CPE insulation', '', self.cpe_insulation[0], 
                                                                selection_list=self.cpe_insulation,
                                                                alter_structure=True,
                                                                status_enable=False)
        self.fields['cpe_cross_section'] = self.get_field_dict('float', 'CPE nominal\ncross-sectional area', 'sq.mm.', 
                                                               0, alter_structure=True,
                                                               status_enable=False)
        self.fields['laying_type'] = self.get_field_dict('str', 'Laying type', '', self.laying_types[0], 
                                                         selection_list=self.laying_types,
                                                         selection_image_list=self.laying_types_images,
                                                         alter_structure=True)
        self.fields['laying_type_sub'] = self.get_field_dict('str', 'Laying arrangement', '', 'Bunched', 
                                                             selection_list=['Bunched'],
                                                             alter_structure=True)
        self.fields['no_in_group'] = self.get_field_dict('str', '# of cables in group', '', '1', selection_list=no_groups_abc_1,
                                                         alter_structure=True)
        self.fields['no_of_layers'] = self.get_field_dict('str', '# of layers', '', '1', selection_list=['1'],
                                                          alter_structure=True)
        self.fields['ambient_temp'] = self.get_field_dict('int', 'Ambient temperature', 'degC', 30, selection_list=ambient_temps_pvc,
                                                          alter_structure=True)
        self.fields['ground_temp'] = self.get_field_dict('int', 'Ground temperature', 'degC', 20, selection_list=ambient_temps_pvc,
                                                         status_enable=False,
                                                         alter_structure=True)
        self.fields['soil_thermal_resistivity'] = self.get_field_dict('float', 'Soil thermal resistivity', 'K·m/W', 2.5, 
                                                                      selection_list=self.soil_thermal_resistivities, 
                                                                      status_enable=False,
                                                                      alter_structure=True)
        self.fields['user_df'] = self.get_field_dict('float', 'Additional DF', '', 1, alter_structure=True)
        self.fields['armour_sc_current_rating'] = self.get_field_dict('float', 'Isc armour (1s)', 'kA', 0, inactivate=True, status_enable=False)
        self.fields['ext_cpe_sc_current_rating'] = self.get_field_dict('float', 'Isc cpe ext (1s)', 'kA', 0, inactivate=True, status_enable=False)
        self.calculate_parameters()
        
    def render_element(self, context):
        """Render element to context"""
        # Preprocessing
        self.schem_model = self.schem_models_dict[self.fields['laying_type']['value']]
        # Render
        if self.fields['in_service']['value']:
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
            if code == 'conductor_material':
                self.fields['conductor_cross_section']['selection_list'] = self.cross_section_dict[value]
            elif code == 'insulation_material':
                self.fields['ambient_temp']['selection_list'] = self.ambient_temp_dict[value]
            elif code == 'laying_type':
                self.fields['laying_type_sub']['selection_list'] = self.laying_arrangements_dict[value]
                self.fields['laying_type_sub']['value'] = self.laying_arrangements_dict[value][0]
                if value in self.laying_types[5:7]:
                    self.fields['ground_temp']['status_enable'] = True
                    self.fields['ambient_temp']['status_enable'] = False
                    self.fields['soil_thermal_resistivity']['status_enable'] = True
                else:
                    self.fields['ground_temp']['status_enable'] = False
                    self.fields['ambient_temp']['status_enable'] = True
                    self.fields['soil_thermal_resistivity']['status_enable'] = False
                code1 = self.fields['laying_type']['selection_list'].index(value)
                code2 = 0            
                self.fields['no_in_group']['selection_list'] = self.no_groups_dict[code1, code2]
                self.fields['no_of_layers']['selection_list'] = self.no_layers_dict[code1, code2]
            elif code == 'laying_type_sub':
                code1 = self.fields['laying_type']['selection_list'].index(self.fields['laying_type']['value'])
                code2 = self.fields['laying_type_sub']['selection_list'].index(value)            
                self.fields['no_in_group']['selection_list'] = self.no_groups_dict[code1, code2]
                self.fields['no_of_layers']['selection_list'] = self.no_layers_dict[code1, code2]
            elif code == 'cpe':
                code_cpe = self.fields['cpe']['selection_list'].index(value)
                if code_cpe in (0,1):
                    self.fields['armour_material']['status_enable'] = False
                    self.fields['armour_cross_section']['status_enable'] = False
                    self.fields['cpe_material']['status_enable'] = False
                    self.fields['cpe_insulation']['status_enable'] = False
                    self.fields['cpe_cross_section']['status_enable'] = False
                    self.fields['armour_sc_current_rating']['status_enable'] = False
                    self.fields['ext_cpe_sc_current_rating']['status_enable'] = False
                elif code_cpe in (2, 4):
                    self.fields['armour_material']['status_enable'] = False
                    self.fields['armour_cross_section']['status_enable'] = False
                    self.fields['cpe_material']['status_enable'] = True
                    self.fields['cpe_insulation']['status_enable'] = True
                    self.fields['cpe_cross_section']['status_enable'] = True
                    self.fields['armour_sc_current_rating']['status_enable'] = False
                    self.fields['ext_cpe_sc_current_rating']['status_enable'] = False
                elif code_cpe == 3:
                    self.fields['armour_material']['status_enable'] = True
                    self.fields['armour_cross_section']['status_enable'] = True
                    self.fields['cpe_material']['status_enable'] = False
                    self.fields['cpe_insulation']['status_enable'] = False
                    self.fields['cpe_cross_section']['status_enable'] = False
                    self.fields['armour_sc_current_rating']['status_enable'] = False
                    self.fields['ext_cpe_sc_current_rating']['status_enable'] = False
                elif code_cpe == 5:
                    self.fields['armour_material']['status_enable'] = True
                    self.fields['armour_cross_section']['status_enable'] = True
                    self.fields['cpe_material']['status_enable'] = True
                    self.fields['cpe_insulation']['status_enable'] = True
                    self.fields['cpe_cross_section']['status_enable'] = True
                    self.fields['armour_sc_current_rating']['status_enable'] = True
                    self.fields['ext_cpe_sc_current_rating']['status_enable'] = True
            self.calculate_parameters()
            
    def conductor_k_value(self, conductor, t0, tf):
        B = self.conductor_B_dict[conductor]
        Qc = self.conductor_Qc_dict[conductor]
        delta20 = self.conductor_delta20_dict[conductor]
        k = math.sqrt(Qc*(B+20)/delta20*math.log((B+tf)/(B+t0)))
        return k
            
    def calculate_parameters(self):
        Sph = self.fields['conductor_cross_section']['value']
        L = self.fields['length_km']['value']
        x_1 = self.fields['x_ohm_per_km']['value']
        open_imp_value = 10000
        
        phase_material = self.fields['conductor_material']['value']
        phase_insulation = self.fields['insulation_material']['value']
        armour_material = self.fields['armour_material']['value']
        armour_cross_section = self.fields['armour_cross_section']['value']
        cpe_material = self.fields['cpe_material']['value']
        cpe_insulation = self.fields['cpe_insulation']['value']
        cpe_cross_section = self.fields['cpe_cross_section']['value']
        phase_working_temp = self.insulation_max_working_temp_dict[phase_insulation]
        ambient_temp = self.fields['ambient_temp']['value']
        neutral_xsec_times = self.fields['neutral_xsec']['value']
        
        code_laying_type = self.fields['laying_type']['selection_list'].index(self.fields['laying_type']['value'])
        code_laying_sub_type = self.fields['laying_type_sub']['selection_list'].index(self.fields['laying_type_sub']['value'])
        code_no_in_group = self.fields['no_in_group']['selection_list'].index(self.fields['no_in_group']['value'])
        code_no_of_layers = self.fields['no_of_layers']['selection_list'].index(self.fields['no_of_layers']['value'])
        code_insulation_material = self.fields['insulation_material']['selection_list'].index(self.fields['insulation_material']['value'])
        code_soil_thermal_resistivity = self.fields['soil_thermal_resistivity']['selection_list'].index(self.fields['soil_thermal_resistivity']['value'])
        code_ambient_temp = self.fields['ambient_temp']['selection_list'].index(self.fields['ambient_temp']['value'])
        code_ground_temp = self.fields['ground_temp']['selection_list'].index(self.fields['ground_temp']['value'])
        code_cpe = self.fields['cpe']['selection_list'].index(self.fields['cpe']['value'])
        
        B_ph = self.conductor_B_dict[phase_material]
        resistivity_20_ph = self.conductor_delta20_dict[phase_material]
        resistivity_working_ph = resistivity_20_ph*(1+1/B_ph*(phase_working_temp-20))
        
        # Impedence
        
        # Positive sequence
        r_ph = open_imp_value if Sph == 0 else resistivity_working_ph*10**6/Sph
        r_1 = r_ph

        # Zero sequence for neutral return
        r_0n = r_ph + 3*r_ph*neutral_xsec_times
        x_0n = x_1 + 3*x_1  # Nuetral reactance contribution to loop assumed same as phase
        
        # Zero sequence for ground return
        if code_cpe == 0:
            r_0 = open_imp_value
            x_0 = open_imp_value
            self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        elif code_cpe == 1:
            r_0 = r_ph + 3*r_ph*neutral_xsec_times
            x_0 = x_1 + 3*x_1  # Nuetral reactance contribution to loop assumed same as phase
            self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "PEN", True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        elif code_cpe == 2:
            B_cpe = self.conductor_B_dict[cpe_material]
            resistivity_20_cpe = self.conductor_delta20_dict[cpe_material]
            resistivity_working_cpe = resistivity_20_cpe*(1+1/B_cpe*(phase_working_temp-20))
            r_0 = open_imp_value if cpe_cross_section == 0 else r_ph + 3*resistivity_working_cpe*10**6/cpe_cross_section
            x_0 = x_1 + 3*x_1  # Nuetral reactance contribution to loop assumed same as phase
            mat_code = self.material_code[cpe_material]
            ins_code = self.insulation_code[cpe_insulation]
            self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "PE:${int(cpe_cross_section)} " + mat_code + "/" + ins_code, True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        elif code_cpe == 3:
            B_ar = self.conductor_B_dict[armour_material]
            resistivity_20_ar = self.conductor_delta20_dict[armour_material]
            resistivity_working_ar = resistivity_20_ar*(1+1/B_ar*(phase_working_temp-20))
            magnetic_effect = 1.1 if armour_material == 'Steel' else 1
            r_0 = open_imp_value if armour_cross_section == 0 else r_ph + 3*magnetic_effect*resistivity_working_ar*10**6/armour_cross_section  # IEE Guidance notes 6, 6.3.1, 6.3.3
            x_0 = x_1 + 3*(0.3 - x_1) if armour_material == 'Steel' else x_1  # IEE Guidance notes 6, 6.3.1, 6.3.3
            mat_code = self.material_code[armour_material]
            self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "PE:Ar/" + mat_code, True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        elif code_cpe == 4:
            B_cpe = self.conductor_B_dict[cpe_material]
            resistivity_20_cpe = self.conductor_delta20_dict[cpe_material]
            resistivity_working_cpe = resistivity_20_cpe*(1+1/B_cpe*(ambient_temp-20))
            r_0 = open_imp_value if cpe_cross_section == 0 else r_ph + 3*resistivity_working_cpe*10**6/cpe_cross_section
            x_0 = x_1 + 3*0.08  # IS 732 Annex Y
            mat_code = self.material_code[cpe_material]
            ins_code = self.insulation_code[cpe_insulation]
            self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "PE:${int(cpe_cross_section)} " + mat_code + "/" + ins_code, True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        elif code_cpe == 5:
            B_cpe = self.conductor_B_dict[cpe_material]
            resistivity_20_cpe = self.conductor_delta20_dict[cpe_material]
            resistivity_working_cpe = resistivity_20_cpe*(1+1/B_cpe*(ambient_temp-20))
            B_ar = self.conductor_B_dict[cpe_material]
            resistivity_20_ar = self.conductor_delta20_dict[phase_material]
            resistivity_working_ar = resistivity_20_ar*(1+1/B_ph*(phase_working_temp-20))
            magnetic_effect = 1.1 if armour_material == 'Steel' else 1
            r_ar = open_imp_value if armour_cross_section == 0 else magnetic_effect*resistivity_working_ar*10**6/armour_cross_section
            r_cpe = open_imp_value if cpe_cross_section == 0 else resistivity_working_cpe*10**6/cpe_cross_section
            r_0 = r_ph + 3*(1/(1/r_ar + 1/r_cpe))  # Appendix 16 – Electrical Research Association Report (ERA) report on armoured cables with external CPCs
            x_0 = x_1 + 3*(0.4 - x_1) if armour_material == 'Steel' else x_1 # Appendix 16 – Electrical Research Association Report (ERA) report on armoured cables with external CPCs
            ar_mat_code = self.material_code[armour_material]
            mat_code = self.material_code[cpe_material]
            ins_code = self.insulation_code[cpe_insulation]
            self.text_model = [[(3,1), "${ref}", True],
                           [(3,None), "${parallel}#${designation}", True],
                           [(3,None), "PE:${int(cpe_cross_section)} " + mat_code + "/" + ins_code + ", Ar/" + ar_mat_code, True],
                           [(3,None), "${int(length_km*1000)}m", True],
                           [(3,None), "${name}", True]]
        
        # Current carrying capacity
        
        # Copper cable
        if self.fields['conductor_material']['value'] == self.conductor_materials[0]:
            if self.fields['type_of_cable']['value'] == '1ph':
                current_model = self.current_rating_table_cu_1ph[code_laying_type][code_insulation_material]
            else:
                current_model = self.current_rating_table_cu_3ph[code_laying_type][code_insulation_material]
        # Aluminium cable
        else:
            if self.fields['type_of_cable']['value'] == '1ph':
                current_model = self.current_rating_table_al_1ph[code_laying_type][code_insulation_material]
            else:
                current_model = self.current_rating_table_al_3ph[code_laying_type][code_insulation_material]
        # Parse current model
        Imax = 0
        for (i0, i1, A, m) in current_model:
            if Sph > i0 and Sph <= i1:
                Imax += A*Sph**m
        Imax = round(Imax) if Imax >= 20 else round(Imax*2)/2
        
        # Reduction factors
        
        Cg = self.df_dict[code_laying_type, code_laying_sub_type][code_no_of_layers][code_no_in_group]
        
        if code_laying_type == 5:
            Ci = self.soil_resistivity_duct_df[code_soil_thermal_resistivity]
        elif code_laying_type == 6:
            Ci = self.soil_resistivity_direct_df[code_soil_thermal_resistivity]
        else:
            Ci = 1
        
        # In ground
        if code_laying_type in (5,6):
            # PVC
            if self.fields['insulation_material']['value'] == self.insulation_materials[0]:
                Ca = self.ground_temp_pvc_df[code_ground_temp]
            # XLPE
            elif self.fields['insulation_material']['value'] == self.insulation_materials[1]:
                Ca = self.ground_temp_xlpe_df[code_ground_temp]
            else:
                Ca = 1
        # Other laying methods
        else:
            # PVC
            if self.fields['insulation_material']['value'] == self.insulation_materials[0]:
                Ca = self.ambient_temp_pvc_df[code_ambient_temp]
            # XLPE
            elif self.fields['insulation_material']['value'] == self.insulation_materials[1]:
                Ca = self.ambient_temp_xlpe_df[code_ambient_temp]
            else:
                Ca = 1
                
        # Short circuit ratings
        
        # Phase
        phase_ultimate_temp = self.insulation_ultimate_working_temp_dict[phase_insulation]
        k_ph = self.conductor_k_value(phase_material, phase_working_temp, phase_ultimate_temp)
        phase_sc_current_rating = k_ph*Sph
        
        # CPE
        if code_cpe == 0:
            armour_sc_current_rating = 0
            ext_cpe_sc_current_rating = 0
            cpe_sc_current_rating = 0
        elif code_cpe == 1:
            armour_sc_current_rating = 0
            ext_cpe_sc_current_rating = 0
            cpe_sc_current_rating = phase_sc_current_rating*neutral_xsec_times
        elif code_cpe == 2:
            cpe_ultimate_temp = self.insulation_ultimate_working_temp_dict[cpe_insulation]
            k_cpe = self.conductor_k_value(cpe_material, phase_working_temp, cpe_ultimate_temp)
            armour_sc_current_rating = 0
            ext_cpe_sc_current_rating = 0
            cpe_sc_current_rating = k_cpe*cpe_cross_section
        elif code_cpe == 3:
            ar_ultimate_temp = self.insulation_ultimate_working_temp_dict[phase_insulation]
            k_ar = self.conductor_k_value(armour_material, phase_working_temp, ar_ultimate_temp)
            armour_sc_current_rating = k_ar*armour_cross_section
            ext_cpe_sc_current_rating = 0
            cpe_sc_current_rating = armour_sc_current_rating
        elif code_cpe == 4:
            cpe_ultimate_temp = self.insulation_ultimate_working_temp_dict[cpe_insulation]
            k_cpe = self.conductor_k_value(cpe_material, ambient_temp, cpe_ultimate_temp)
            armour_sc_current_rating = 0
            ext_cpe_sc_current_rating = 0
            cpe_sc_current_rating = k_cpe*cpe_cross_section
        elif code_cpe == 5:
            ar_ultimate_temp = self.insulation_ultimate_working_temp_dict[phase_insulation]
            k_ar = self.conductor_k_value(armour_material, phase_working_temp, ar_ultimate_temp)
            cpe_ultimate_temp = self.insulation_ultimate_working_temp_dict[cpe_insulation]
            k_cpe = self.conductor_k_value(cpe_material, ambient_temp, cpe_ultimate_temp)
            armour_sc_current_rating = k_ar*armour_cross_section
            ext_cpe_sc_current_rating = k_cpe*cpe_cross_section
            cpe_sc_current_rating = min(armour_sc_current_rating, ext_cpe_sc_current_rating)
                
        # Update fields
        
        self.fields['r_ohm_per_km']['value'] = round(r_1, 3)
        self.fields['r0n_ohm_per_km']['value'] = round(r_0n, 3)
        self.fields['x0n_ohm_per_km']['value'] = round(x_0n, 3)
        self.fields['r0g_ohm_per_km']['value'] = round(r_0, 3)
        self.fields['x0g_ohm_per_km']['value'] = round(x_0, 3)

        self.fields['endtemp_degree']['value'] = phase_ultimate_temp
        self.fields['max_i_ka']['value'] = Imax/1000
        self.fields['df']['value'] = round(self.fields['user_df']['value']*Ci*Cg*Ca, 3)
        
        self.fields['phase_sc_current_rating']['value'] = round(phase_sc_current_rating/1000, 3)
        self.fields['armour_sc_current_rating']['value'] = round(armour_sc_current_rating/1000, 3)
        self.fields['ext_cpe_sc_current_rating']['value'] = round(ext_cpe_sc_current_rating/1000, 3)
        self.fields['cpe_sc_current_rating']['value'] = round(cpe_sc_current_rating/1000,3)

    def set_model(self, model, gid=None):
        """Set storage model"""
        if model['code'] == self.code:
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            for code in self.fields:
                if code in model['fields']:
                    self.set_text_field_value(code, model['fields'][code]['value'])
            self.gid = gid


class LTCableCustom(Line):
    """Cable element"""

    code = 'element_line_custom'
    name = 'Line (Custom Geometry)'
    group = 'Components'
    icon = misc.abs_path('icons', 'line.svg')

    def __init__(self, cordinates=(0,0), **kwargs):
        # Global
        Line.__init__(self, cordinates, **kwargs)
        self.database_path = misc.abs_path('database', 'line_custom.csv')
        
        # Data dropdowns
        self.laying_types = ['OH Line - \n3 phase with earth return\nGeneral geometry', 
                             'OH Line - \n3 phase with earth return\nTriangular arrangement',
                             'OH Line - \n3 phase with earth return\nFlat arrangement']
        self.laying_types_images = ['line_custom_oh1.svg',
                                    'line_custom_oh2.svg',
                                    'line_custom_oh3.svg']
        self.conductor_materials = ['Copper','Aluminium','Steel']
        self.material_code = {'Copper':'Cu','Aluminium':'Al','Steel':'Fe'}
        self.conductor_B_dict = {'Copper':234.5,'Aluminium':228,'Steel':202}
        self.conductor_Qc_dict = {'Copper':3.45e-3,'Aluminium':2.5e-3,'Steel':3.8e-3}
        self.conductor_delta20_dict = {'Copper':17.241e-6,'Aluminium':28.264e-6,'Steel':138e-6}
                                                                                       
        # Modify existing fields
        self.fields['r_ohm_per_km']['status_inactivate'] = True
        self.fields['x_ohm_per_km']['status_inactivate'] = True
        self.fields['c_nf_per_km']['status_inactivate'] = True
        self.fields['g_us_per_km']['status_enable'] = False
        self.fields['r0g_ohm_per_km']['status_inactivate'] = True
        self.fields['x0g_ohm_per_km']['status_inactivate'] = True
        self.fields['r0n_ohm_per_km']['status_inactivate'] = True
        self.fields['x0n_ohm_per_km']['status_inactivate'] = True
        self.fields['c0g_nf_per_km']['status_enable'] = False
        self.fields['c0n_nf_per_km']['status_enable'] = False
        self.fields['type']['status_enable'] = False
        self.fields['type']['value'] = 'Over Head'
        self.fields['phase_sc_current_rating']['status_inactivate'] = True
        self.fields['cpe_sc_current_rating']['status_inactivate'] = True
        self.fields['df']['status_inactivate'] = True
        self.fields['length_km']['alter_structure'] = True
        
        # Add new fields
        self.fields['laying_type'] = self.get_field_dict('str', 'Line type', '', self.laying_types[0],
                                                         selection_list=self.laying_types,
                                                         selection_image_list=self.laying_types_images,
                                                         alter_structure=True)
        self.fields['conductor_material'] = self.get_field_dict('str', 'Conductor material', '', 
                                                                self.conductor_materials[1],
                                                                selection_list=self.conductor_materials,
                                                                alter_structure=True)
        self.fields['conductor_cross_section'] = self.get_field_dict('float', 'Phase nominal\ncross-sectional area', 
                                                                    'sq.mm.', 50, alter_structure=True)
        self.fields['dims_d'] = self.get_field_dict('float', 'D', 'm', 1, status_enable=False, alter_structure=True)
        self.fields['dims_dia'] = self.get_field_dict('float', 'Conductor Diameter', 'mm', 1, alter_structure=True)
        self.fields['dims_d1'] = self.get_field_dict('float', 'D1', 'm', 1, alter_structure=True)
        self.fields['dims_d2'] = self.get_field_dict('float', 'D2', 'm', 1, alter_structure=True)
        self.fields['dims_d3'] = self.get_field_dict('float', 'D3', 'm', 1, alter_structure=True)
        self.fields['soil_resistivity'] = self.get_field_dict('float', 'Soil resistivity', 'Ohm.m', 100,
                                                              alter_structure=True)
        self.fields['working_temp_degree'] = self.get_field_dict(
            'float', 'Line Working Temperature', 'degC', 70, alter_structure=True)
        self.fields['user_df'] = self.get_field_dict(
            'float', 'Additional DF', '', 1, alter_structure=True)
        self.calculate_parameters()
        
    def set_text_field_value(self, code, value):
        if self.fields and code in self.fields:
            self.fields[code]['value'] = value
            # Modify variables based on selection
            if code == 'laying_type':
                if value == self.laying_types[0]:
                    self.fields['dims_d']['status_enable'] = False
                    self.fields['dims_d1']['status_enable'] = True
                    self.fields['dims_d2']['status_enable'] = True
                    self.fields['dims_d3']['status_enable'] = True
                elif value in self.laying_types[1:2]:
                    self.fields['dims_d']['status_enable'] = True
                    self.fields['dims_d1']['status_enable'] = False
                    self.fields['dims_d2']['status_enable'] = False
                    self.fields['dims_d3']['status_enable'] = False
            self.calculate_parameters()

    def conductor_k_value(self, conductor, t0, tf):
        B = self.conductor_B_dict[conductor]
        Qc = self.conductor_Qc_dict[conductor]
        delta20 = self.conductor_delta20_dict[conductor]
        k = math.sqrt(Qc*(B+20)/delta20*math.log((B+tf)/(B+t0)))
        return k
            
    def calculate_parameters(self):
        open_imp_value = 10000
        f_hz = self.kwargs['project_settings']['Simulation']['grid_frequency']['value']
        Sph = self.fields['conductor_cross_section']['value']
        L = self.fields['length_km']['value']
        phase_material = self.fields['conductor_material']['value']
        code_laying_type = self.fields['laying_type']['selection_list'].index(self.fields['laying_type']['value'])
        phase_working_temp = self.fields['working_temp_degree']['value']
        B_ph = self.conductor_B_dict[phase_material]
        resistivity_20_ph = self.conductor_delta20_dict[phase_material]
        resistivity_working_ph = resistivity_20_ph*(1+1/B_ph*(phase_working_temp-20))
        r_ph = open_imp_value if Sph == 0 else resistivity_working_ph*10**6/Sph
        mu_0 = 4*math.pi*10**-7
        omega = 2*math.pi*f_hz
        rho = self.fields['soil_resistivity']['value']
        delta = 1.85/math.sqrt(omega*mu_0/rho)  # As per IEC 60909-3 eq.(35)

        if code_laying_type in (0,):
            r = self.fields['dims_dia']['value']/1000/2
            d1 = self.fields['dims_d1']['value']
            d2 = self.fields['dims_d2']['value']
            d3 = self.fields['dims_d3']['value']
            d = (d1*d2*d3)**(1/3)
            # Positive sequence
            r_1 = r_ph
            x_1 = omega*mu_0/(2*math.pi)*(1/4+math.log(d/r))*1000  # As per IEC 60909-2 eq.(1)
            # Zero sequence
            r_0 = r_0n = r_ph + 3*omega*mu_0/8*1000  # As per IEC 60909-2 eq.(3)
            x_0 = x_0n = omega*mu_0/(2*math.pi)*(1/4+3*math.log(delta/(r*d**2)**(1/3)))*1000  # As per IEC 60909-2 eq.(3)
        elif code_laying_type == 1:
            r = self.fields['dims_dia']['value']/1000/2
            d = self.fields['dims_d']['value']
            # Positive sequence
            r_1 = r_ph
            x_1 = omega*mu_0/(2*math.pi)*(1/4+math.log(d/r))*1000  # As per IEC 60909-2 eq.(1)
            # Zero sequence
            r_0 = r_0n = r_ph + 3*omega*mu_0/8*1000  # As per IEC 60909-2 eq.(3)
            x_0 = x_0n = omega*mu_0/(2*math.pi)*(1/4+3*math.log(delta/(r*d**2)**(1/3)))*1000  # As per IEC 60909-2 eq.(3)
        elif code_laying_type == 2:
            r = self.fields['dims_dia']['value']/1000/2
            d = (self.fields['dims_d']['value']**3*2)**(1/3)
            # Positive sequence
            r_1 = r_ph
            x_1 = omega*mu_0/(2*math.pi)*(1/4+math.log(d/r))*1000  # As per IEC 60909-2 eq.(1)
            # Zero sequence
            r_0 = r_0n = r_ph + 3*omega*mu_0/8*1000  # As per IEC 60909-2 eq.(3)
            x_0 = x_0n = omega*mu_0/(2*math.pi)*(1/4+3*math.log(delta/(r*d**2)**(1/3)))*1000  # As per IEC 60909-2 eq.(3)

        # Short circuit ratings
        phase_ultimate_temp = self.fields['endtemp_degree']['value']
        k_ph = self.conductor_k_value(phase_material, phase_working_temp, phase_ultimate_temp)
        phase_sc_current_rating = k_ph*Sph

        # Update fields
        self.fields['r_ohm_per_km']['value'] = round(r_1, 3)
        self.fields['x_ohm_per_km']['value'] = round(x_1, 3)
        self.fields['r0n_ohm_per_km']['value'] = round(r_0n, 3)
        self.fields['x0n_ohm_per_km']['value'] = round(x_0n, 3)
        self.fields['r0g_ohm_per_km']['value'] = round(r_0, 3)
        self.fields['x0g_ohm_per_km']['value'] = round(x_0, 3)
        self.fields['df']['value'] = round(self.fields['user_df']['value'], 3)
        self.fields['phase_sc_current_rating']['value'] = round(phase_sc_current_rating/1000, 3)

    def set_model(self, model, gid=None):
        """Set storage model"""
        if model['code'] == self.code:
            self.x = model['x']
            self.y = model['y']
            self.orientation = model['orientation']
            self.ports = copy.deepcopy(model['ports'])
            for code in self.fields:
                if code in model['fields']:
                    self.set_text_field_value(code, model['fields'][code]['value'])
            self.gid = gid
