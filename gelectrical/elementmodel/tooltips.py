#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2020 Manu Varkey <manuvarkey@gmail.com>
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

def print_model_field_dict(program_state):
    print("tooltips = {")
    for code, model in program_state['element_models'].items():
        print("'{}': {}".format(code, "{"))
        for fcode in model(project_settings=program_state['project_settings']).fields:
            print("'{}': '',".format(fcode))
        print('},')
    print('}')

tooltips = {
'element_switch': {
'ref': '',
'name': '',
'closed': '',
},
'element_fuse': {
'ref': '',
'name': '',
'closed': '',
'custom': '',
'type': '',
'subtype': '',
'prot_curve_type': '',
'prot_0_curve_type': '',
'poles': '',
'Un': 'Rated voltage of fuse unit (L-L)',
'In': 'Rated current of fuse unit',
'In_set': 'Current setting of fuse link as a fraction of rated current',
'Isc': 'Rated short circuit breaking capacity of fuse unit',
'pcurve_l': '',
'I0': '',
'I0_set': '',
'pcurve_g': '',
'sdfu': 'Whether the fuse unit includes a switch disconnector ?',
},
'element_circuitbreaker': {
'ref': '',
'name': '',
'closed': '',
'custom': '',
'type': '',
'subtype': '',
'prot_curve_type': '',
'prot_0_curve_type': '',
'poles': '',
'Un': 'Rated voltage of circuit breaker unit (L-L)',
'In': 'Rated current of circuit breaker unit',
'In_set': 'Current setting as a fraction of rated current',
'Isc': 'Rated short circuit breaking capacity of fuse unit',
'pcurve_g': '',
'pcurve_l': '',
'I0': 'Ground fault rated current of circuit breaker unit',
'I0_set': 'Ground fault current setting as a fraction of ground fault rated current',
'pcurve_g': '',
'drawout': 'Whether the circuit breaker is of draw out type ?',
},
'element_contactor': {
'ref': '',
'name': '',
'type': '',
'poles': '',
'Un': 'Rated voltage (L-L)',
'In': 'Rated current',
'closed': '',
},
'element_co_switch': {
'ref': '',
'name': '',
'type': '',
'poles': '',
'Un': 'Rated voltage (L-L)',
'In': 'Rated current',
'model': '',
'position': '',
},
'element_busbar': {
'ref': '',
'In': 'Rated current of busbar',
'Isc': 'Rated short circuit current of busbar (1s)',
'n_top': 'Number of connection points at top',
'n_btm': 'Number of connection points at bottom',
'width': 'Width of each bay',
'DF': 'Diversity factor at bus to be used in <b>Power flow with diversity</b> analysis. Do not have any effect in other power flow analysis modes.',
'r_grid': """<b>Net resistance of eathing system including resistance of local earth grid and source earth grid.</b>

This parameter is of significance only if return path of fault current is through earth and may be used to model TT &amp; IT earthing systems. If a value of 0 is specified, this parameter is ignored.

The resistance value (x3) specified will be added to the zero sequence impedance for all downstream nodes of same voltage level during single line to ground short circuit calculation.""",
},
'element_grid': {
'ref': '',
'name': '',
'vm_pu': 'Per unit voltage set point of external grid',
'va_degree': 'Voltage angle set point of external grid',
'vn_kv': 'Rated voltage (L-L)',
's_sc_max_mva': 'Maximum short circuit power provision',
's_sc_min_mva': 'Minimum short circuit power provision',
'rx_max': 'Maximum R/X ratio of short-circuit impedance',
'rx_min': 'Minimum R/X ratio of short-circuit impedance',
'r0x0_max': 'Maximum R0/X0 ratio to calculate zero sequence internal impedance',
'r0x0_min': 'Minimum R0/X0 ratio to calculate zero sequence internal impedance',
'x0x_max': 'Maximum X0/X-ratio to calculate zero sequence internal impedance',
'x0x_min': 'Minimum X0/X-ratio to calculate zero sequence internal impedance',
'in_service': '',
},
'element_reference': {
'ref': 'This value is used to link references',
'sheet': 'Sheet to which reference is linking',
'title': '',
'sub_title': '',
},
'element_reference_box': {
'ref': 'This value is used to link references',
'sheet': 'Sheet to which reference is linking',
'title': '',
'sub_title': '',
'width': '',
},
'element_transformer': {
'ref': '',
'name': '',
'sn_mva': 'Rated apparent power of the transformer',
'vn_hv_kv': 'Rated voltage at high voltage bus (L-L)',
'vn_lv_kv': 'Rated voltage at low voltage bus (L-L)',
'vkr_percent': 'Real component of short circuit voltage',
'vk_percent': 'Short circuit voltage',
'vkr0_percent': 'Real part of zero sequence relative short-circuit voltage',
'vk0_percent': 'Zero sequence relative short-circuit voltage',
'mag0_percent': 'z_mag0 / z0 ratio between magnetizing and short circuit impedance (zero sequence)',
'mag0_rx': 'Zero sequence magnetizing r/x ratio',
'si0_hv_partial': 'Zero sequence short circuit impedance distribution in high voltage side',
'shift_degree': 'Transformer phase shift angle',
'vector_group': 'Vector Group of transformer (required for determining zero sequence model of transformer)',
'pfe_kw': 'Iron losses',
'i0_percent': 'Open loop losses',
'sym_hv': '',
'sym_lv': '',
'tap_side': '',
'tap_min': '',
'tap_max': '',
'tap_pos': '',
'tap_step_percent': '',
'oltc': '',
'xn_ohm': '',
'dcurve': '',
},
'element_transformer3w': {
'ref': '',
'name': '',
'sn_hv_mva': 'Rated apparent power on high voltage side',
'sn_mv_mva': 'Rated apparent power on medium voltage side',
'sn_lv_mva': 'Rated apparent power on low voltage side',
'vn_hv_kv': 'Rated voltage at high voltage bus (L-L)',
'vn_mv_kv': 'Rated voltage at medium voltage bus (L-L)',
'vn_lv_kv': 'Rated voltage at low voltage bus (L-L)',
'vk_hv_percent': 'Short circuit voltage from high to medium voltage',
'vk_mv_percent': 'Short circuit voltage from medium to low voltage',
'vk_lv_percent': 'Short circuit voltage from high to low voltage',
'vkr_hv_percent': 'Real part of short circuit voltage from high to medium voltage',
'vkr_mv_percent': 'Real part of short circuit voltage from medium to low voltage',
'vkr_lv_percent': 'Real part of short circuit voltage from high to low voltage',
'pfe_kw': 'Iron losses',
'i0_percent': 'Open loop losses',
'shift_mv_degree': 'Transformer phase shift angle at the MV side',
'shift_lv_degree': 'Transformer phase shift angle at the LV side',
'sym_hv': '',
'sym_mv': '',
'sym_lv': '',
},
'element_load': {
'ref': '',
'name': '',
'sn_kva': '',
'cos_phi': 'Power factor of load',
'scaling': 'Scaling factor for active and reactive power',
'mode': 'Whether load is inductive or capacitive ?',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
},
'element_asymmetric_load': {
'ref': '',
'name': '',
'sn_kva': '',
'p_a_kw': 'The active power for Phase A load',
'p_b_kw': 'The active power for Phase B load',
'p_c_kw': 'The active power for Phase C load',
'q_a_kvar': 'The reactive power for Phase A load',
'q_b_kvar': 'The reactive power for Phase B load',
'q_c_kvar': 'The reactive power for Phase C load',
'scaling': 'Scaling factor for active and reactive power',
'type': 'Type variable to classify three ph load: delta/wye',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
},
'element_single_phase_load': {
'ref': '',
'name': '',
'sn_kva': '',
'cos_phi': 'Power factor of load',
'scaling': 'Scaling factor for active and reactive power',
'phase': '',
'mode': 'Whether load is inductive or capacitive ?',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
},
'element_line': {
'ref': '',
'name': '',
'length_km': '',
'conductor_material': '',
'insulation_material': '',
'r_ohm_per_km': 'Resistance of the line',
'x_ohm_per_km': 'Inductance of the line',
'c_nf_per_km': 'Capacitance of the line',
'g_us_per_km': 'Dielectric conductance of the line',
'r0n_ohm_per_km': 'Zero sequence resistance of the line for neutral',
'x0n_ohm_per_km': 'Zero sequence inductance of the line for neutral',
'c0n_nf_per_km': 'Zero sequence capacitance of the line for neutral',
'r0g_ohm_per_km': 'Zero sequence resistance of the line for protective earth return',
'x0g_ohm_per_km': 'Zero sequence inductance of the line for protective earth return',
'c0g_nf_per_km': 'Zero sequence capacitance of the line for protective earth return',
'endtemp_degree': 'Short-Circuit end temperature of the line',
'max_i_ka': 'Maximum line thermal current',
'phase_sc_current_rating': 'Short-Circuit current rating of phase conductor (1s)',
'cpe_sc_current_rating': 'Short-Circuit current rating of phase ciruit protective earthing conductor (1s)',
'df': 'Derating factor',
'designation': '',
'type': '',
'parallel': '',
'dcurve': '',
'in_service': '',
},
'element_line_cable': {
'ref': '',
'name': '',
'length_km': '',
'conductor_material': '',
'insulation_material': '',
'r_ohm_per_km': 'Resistance of the line',
'x_ohm_per_km': 'Inductance of the line',
'c_nf_per_km': 'Capacitance of the line',
'g_us_per_km': 'Dielectric conductance of the line',
'r0n_ohm_per_km': 'Zero sequence resistance of the line for neutral',
'x0n_ohm_per_km': 'Zero sequence inductance of the line for neutral',
'c0n_nf_per_km': 'Zero sequence capacitance of the line for neutral',
'r0g_ohm_per_km': 'Zero sequence resistance of the line for protective earth return',
'x0g_ohm_per_km': 'Zero sequence inductance of the line for protective earth return',
'c0g_nf_per_km': 'Zero sequence capacitance of the line for protective earth return',
'endtemp_degree': 'Short-Circuit end temperature of the line',
'max_i_ka': 'Maximum line thermal current',
'phase_sc_current_rating': 'Short-Circuit current rating of phase conductor (1s)',
'cpe_sc_current_rating': 'Short-Circuit current rating of phase ciruit protective earthing conductor (1s)',
'df': 'Derating factor',
'designation': '',
'type': '',
'parallel': '',
'dcurve': '',
'in_service': '',
'conductor_cross_section': '',
'neutral_xsec': '',
'type_of_cable': '',
'cpe': """Type of ciruit protective earthing conductor provided.

If <i>None</i> is selected, it is assumed that no dedicated CPE is provided and return current is through earth.""",
'armour_material': '',
'armour_cross_section': '',
'cpe_material': '',
'cpe_insulation': '',
'cpe_cross_section': '',
'laying_type': '',
'laying_type_sub': '',
'no_in_group': '',
'no_of_layers': '',
'ambient_temp': '',
'ground_temp': '',
'soil_thermal_resistivity': '',
'user_df': 'Additional derating factor',
'armour_sc_current_rating': 'Short-Circuit current rating of armour',
'ext_cpe_sc_current_rating': 'Short-Circuit current rating of external ciruit protective earthing conductor',
},
'element_line_custom': {
'ref': '',
'name': '',
'length_km': '',
'conductor_material': '',
'insulation_material': '',
'r_ohm_per_km': 'Resistance of the line',
'x_ohm_per_km': 'Inductance of the line',
'c_nf_per_km': 'Capacitance of the line',
'g_us_per_km': 'Dielectric conductance of the line',
'r0n_ohm_per_km': 'Zero sequence resistance of the line for neutral',
'x0n_ohm_per_km': 'Zero sequence inductance of the line for neutral',
'c0n_nf_per_km': 'Zero sequence capacitance of the line for neutral',
'r0g_ohm_per_km': 'Zero sequence resistance of the line for protective earth return',
'x0g_ohm_per_km': 'Zero sequence inductance of the line for protective earth return',
'c0g_nf_per_km': 'Zero sequence capacitance of the line for protective earth return',
'endtemp_degree': 'Short-Circuit end temperature of the line',
'max_i_ka': 'Maximum line thermal current',
'phase_sc_current_rating': 'Short-Circuit current rating of phase conductor (1s)',
'cpe_sc_current_rating': 'Short-Circuit current rating of phase ciruit protective earthing conductor (1s)',
'df': 'Derating factor',
'designation': '',
'type': '',
'parallel': '',
'dcurve': '',
'in_service': '',
'laying_type': '',
'conductor_cross_section': '',
'dims_d': '',
'dims_dia': '',
'dims_d1': '',
'dims_d2': '',
'dims_d3': '',
'cpe': '',
'armour_material': '',
'armour_cross_section': '',
'soil_resistivity': '',
'working_temp_degree': '',
'user_df': 'Additional derating factor',
},
'element_line_bus': {
'ref': '',
'name': '',
'length_km': '',
'conductor_material': '',
'insulation_material': '',
'r_ohm_per_km': 'Resistance of the line',
'x_ohm_per_km': 'Inductance of the line',
'c_nf_per_km': 'Capacitance of the line',
'g_us_per_km': 'Dielectric conductance of the line',
'r0n_ohm_per_km': 'Zero sequence resistance of the line for neutral',
'x0n_ohm_per_km': 'Zero sequence inductance of the line for neutral',
'c0n_nf_per_km': 'Zero sequence capacitance of the line for neutral',
'r0g_ohm_per_km': 'Zero sequence resistance of the line for protective earth return',
'x0g_ohm_per_km': 'Zero sequence inductance of the line for protective earth return',
'c0g_nf_per_km': 'Zero sequence capacitance of the line for protective earth return',
'endtemp_degree': 'Short-Circuit end temperature of the line',
'max_i_ka': 'Maximum line thermal current',
'phase_sc_current_rating': 'Short-Circuit current rating of phase conductor (1s)',
'cpe_sc_current_rating': 'Short-Circuit current rating of phase ciruit protective earthing conductor (1s)',
'df': 'Derating factor',
'designation': '',
'type': '',
'parallel': '',
'dcurve': '',
'in_service': '',
'r_n_ohm_per_km': 'Resistance of neutral conductor',
'x_n_ohm_per_km': 'Inductance of neutral conductor',
'r_pe_ohm_per_km': 'Resistance of ciruit protective earthing conductor',
'x_p_pe_ohm_per_km': 'Inductance of ciruit protective earthing conductor',
'i_cw': 'Rated short-time withstand current (1s)',
'i_pk': 'Rated peak withstand current',
},
'element_impedance': {
'ref': '',
'name': '',
'rft_pu': 'Resistance of the impedance',
'xft_pu': 'Reactance of the impedance',
'rft0_pu': 'Zero sequence resistance of the impedance',
'xft0_pu': 'Zero sequence reactance of the impedance',
'sn_kva': 'Rated apparent power for the impedance',
'in_service': '',
},
'element_inductance': {
'ref': '',
'name': '',
'rft_pu': 'Resistance of the impedance',
'xft_pu': 'Reactance of the impedance',
'rft0_pu': 'Zero sequence resistance of the impedance',
'xft0_pu': 'Zero sequence reactance of the impedance',
'sn_kva': 'Rated apparent power for the impedance',
'in_service': '',
},
'element_shunt_cap': {
'ref': '',
'name': '',
'p_kw': 'Shunt active power',
'q_kvar': 'Shunt reactive power',
'vn_kv': 'Rated voltage of the shunt element (L-L)',
'in_service': '',
},
'element_generator': {
'ref': '',
'name': '',
'vm_pu': 'Voltage set point of the generator',
'vn_kv': 'Rated voltage of the generator (L-L)',
'p_mw': 'Real power of the generator',
'sn_mva': 'Nominal power of the generator',
'cos_phi': 'Rated generator cosine phi',
'xdss_pu': 'Subtransient generator reactance in per unit',
'rdss_ohm': 'Subtransient generator resistence in ohm',
'in_service': '',
},
'element_async_motor_3ph': {
'ref': '',
'name': '',
'sn_kva': '',
'cos_phi': 'Power factor of load',
'scaling': 'Scaling factor for active and reactive power',
'mode': 'Whether load is inductive or capacitive ?',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
'p_kw': '',
'efficiency': '',
'k': 'Starting current as a multiple of rated current',
'rx': 'R/X ratio of the motor for short-circuit calculation',
'dcurve': '',
},
'element_async_motor_1ph': {
'ref': '',
'name': '',
'sn_kva': '',
'cos_phi': 'Power factor of load',
'scaling': 'Scaling factor for active and reactive power',
'phase': '',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
'p_kw': '',
'efficiency': '',
'k': 'Starting current as a multiple of rated current',
'dcurve': '',
},
'element_staticgenerator': {
'ref': '',
'name': '',
'p_mw': 'Active power of the static generator',
'q_mvar': 'Reactive power of the static generator',
'k': 'Ratio of nominal current to short circuit current',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
},
'element_single_phase_staticgenerator': {
'ref': '',
'name': '',
'p_kw': 'Active power of the static generator',
'q_kvar': 'Reactive power of the static generator',
'k': 'Ratio of nominal current to short circuit current',
'phase': '',
'in_service': '',
'load_profile': 'Daily load profiles are used in <b>Time series</b> power analysis to model variation of load/ power generation over the day.',
},
'element_ward': {
'ref': '',
'name': '',
'ps_mw': 'Active power of the PQ load',
'qs_mvar': 'Reactive power of the PQ load',
'pz_mw': 'Active power of the impedance load in MW at 1 pu voltage',
'qz_mvar': 'Reactive power of the impedance load in MVar at 1 pu voltage',
'in_service': '',
},
'element_xward': {
'ref': '',
'name': '',
'ps_mw': 'Active power of the PQ load',
'qs_mvar': 'Reactive power of the PQ load',
'pz_mw': 'Active power of the impedance load in MW at 1 pu voltage',
'qz_mvar': 'Reactive power of the impedance load in MVar at 1 pu voltage',
'r_ohm': 'Internal resistance of the voltage source',
'x_ohm': 'Internal reactance of the voltage source',
'vm_pu': 'Voltage magnitude at the additional PV-node',
'in_service': '',
},
'element_shunt': {
'ref': '',
'name': '',
'p_kw': 'Shunt active power',
'q_kvar': 'Shunt reactive power',
'vn_kv': 'Rated voltage of the shunt element (L-L)',
'in_service': '',
},
}

