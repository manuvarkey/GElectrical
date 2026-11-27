#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# fields
#
#  Copyright 2014 Manu Varkey <manuvarkey@gmail.com>
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

"""Field dictionaries: construction, truncation for storage, update from
stored values, parameter tables and default settings. No GUI imports."""

import copy
from collections.abc import MutableMapping
from uuid import uuid4 as uuid

from . import style
from .expressions import ExpressionError, Policy, evaluate_numeric


class ReferenceCounter:
    """Class for implementing reference counting"""
    
    def __init__(self, start):
        self.refs = dict()
        self.start=start
        
    def __setitem__(self, code, value):
        self.refs[code] = value
            
    def __getitem__(self, code):
        if code in self.refs:
            return self.refs[code]
        else:
            return self.start

class FieldDict(MutableMapping):
    """Convinence class to read field dictionary attributes"""

    def __init__(self, dict_var):
        self.store = dict_var

    def __getitem__(self, key):
        return self.store[key]['value']

    def __setitem__(self, key, value):
        self.store[key]['value'] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)
    
    def __len__(self):
        return len(self.store)
    
    __getattr__ = __getitem__

class Element:
    def __init__(self, element):
        # Copy all variables
        self.__dict__.update(vars(element))
        # Add convinence variables
        self.r = FieldDict(element.res_fields)
        self.f = FieldDict(element.fields)

# Safe expression access (ADR 0011): ``f.code`` reads a field value

def field_dict_attribute(obj, name):
    """Attribute resolver of :class:`FieldDict` for safe expressions"""
    if name in obj.store:
        return obj[name]
    raise ExpressionError('Unknown field %r' % name)

def element_attribute(obj, name):
    """Attribute resolver of :class:`Element`: public instance variables"""
    if name in vars(obj):
        return vars(obj)[name]
    raise ExpressionError('Unknown element attribute %r' % name)

FIELD_POLICY = Policy(attributes={FieldDict: field_dict_attribute})
"""Expressions over field dictionaries (``f.In * d.i_r``)"""

def get_uid():
    """Get unique id as identifier"""
    return str(uuid())

# Field handling functions

def get_field_dict(field_type, caption, unit, value, 
                        max_chars=None, 
                        validation_func=None, 
                        selection_list=None, 
                        selection_image_list=None, 
                        decimal=6,
                        status_enable=True,
                        status_inactivate=True,
                        status_floating=False,
                        click_to_edit_message=None,
                        alter_structure=False,
                        alter_values_dict=None,
                        tooltip=''):
    """
    ARGUMENTS:
    field_type:             Any of ('int','float','str','multiline_str','bool', 'font', 'graph')
    validation_func:        Function to validate input, should return validated result
    selection_list:         List of values to select from
    selection_image_list:   Corresponding images to load
    status_enable:          Whether to display field ?
    status_inactivate:      Whether to deactivate editing ?
    status_floating:        Whether to display field while floating (only used for element addition)
    click_to_edit_message:  Show a message before editing field
    alter_structure:        Whether field alters field structure of base element ?
    alter_values_dict:      value -> default values (a new empty dict when not given, D15)
    """
    field_dict = dict()
    field_dict['type'] = field_type
    field_dict['caption'] = caption
    field_dict['unit'] = unit
    field_dict['value'] = value
    field_dict['max_chars'] = max_chars
    field_dict['validation_func'] = validation_func
    field_dict['selection_list'] = selection_list
    field_dict['selection_image_list'] = selection_image_list
    field_dict['decimal'] = decimal
    field_dict['status_enable'] = status_enable
    field_dict['status_inactivate'] = status_inactivate
    field_dict['status_floating'] = status_floating
    field_dict['click_to_edit_message'] = click_to_edit_message
    field_dict['alter_structure'] = alter_structure
    field_dict['alter_values_dict'] = alter_values_dict if alter_values_dict is not None else {}
    field_dict['tooltip'] = tooltip
    return field_dict

def get_fields_trunc(fields):
    updated_fields = dict()
    for key, field in fields.items():
        updated_field = {'value': field['value'],
                         'type' : field['type']}
        updated_fields[key] = updated_field
    return updated_fields

def update_fields(reffields, newfields):
    updated = copy.deepcopy(reffields)
    for key in newfields:
        if key in reffields and updated[key]['type'] == newfields[key]['type']:
            updated[key]['value'] = newfields[key]['value']
    return updated
    
def get_fields_dict_trunc(fields_dict):
    updated_fields_dict = dict()
    for key, fields in fields_dict.items():
        updated_fields_dict[key] = get_fields_trunc(fields)
    return updated_fields_dict

def update_fields_dict(reffields_dict, newfields_dict):
    updated = copy.deepcopy(reffields_dict)
    for key in newfields_dict:
        if key in reffields_dict:
            updated[key] = update_fields(reffields_dict[key], newfields_dict[key])
    return updated

def set_field_selection_list(field, code, selection_list, modified=None):
    """Set the selection list of field ``code``. When the current value is not
    in the list it is replaced by the first entry and the old value is stored
    in ``modified`` (if given; D15: no shared default dictionary)."""
    field[code]['selection_list'] = selection_list
    if (selection_list is not None) and (field[code]['value'] not in selection_list):
        if modified is not None:
            modified[code] = field[code]['value'] 
        field[code]['value'] = selection_list[0]

def apply_alter_values(fields, code):
    """Apply ``alter_values_dict`` of field ``code`` (``alter_structure``
    fields): for the current value, hide the listed fields (default ``None``)
    or show them with the given default value. Moved from the GTK field view
    (M4) so that services apply the same side effects."""
    alter_values_dict = fields[code]['alter_values_dict']
    value = fields[code]['value']
    if alter_values_dict and value in alter_values_dict:
        alter_values_dict_cur = alter_values_dict[value]
        for set_key in alter_values_dict_cur:
            if set_key in fields:
                set_value = alter_values_dict_cur[set_key]
                if set_value is None:
                    fields[set_key]['status_enable'] = False
                else:
                    fields[set_key]['status_enable'] = True
                    fields[set_key]['value'] = set_value

def get_fields_from_params(parameters, modify_code=''):
    """Return feilds from paramater dict
        Order of parameters: caption, unit, value, [selection_list, tooltip, data_type, status_enable, default_values_dict]
            where
            default_values_dict: value -> default_values
                where
                default_values: parameter_key -> default value of parameter [if None, parameter is disabled]
    """
    fields = dict()
    default_parameter_dict = dict()  # default_values_dict combined for all active parameters
    
    def get_validation_func(decimal, min, max):
        def validation_func(text):
            try:
                validated = round(float(evaluate_numeric(text)), decimal)
                if min is not None:
                    if validated < min:
                        validated = min
                if max is not None:
                    if validated > max:
                        validated = max
            except:
                if min is not None:
                    validated = min
                else:
                    validated = 0
            return validated
        return validation_func

    for key, values in parameters.items():
        selection_list = None
        tooltip = ''
        data_type = 'float'
        validation_func = None
        status_enable = True
        alter_structure = False
        alter_values_dict = dict()
        caption, unit, value = values[0:3]
        if len(values) >= 4:
            selection_list = values[3]
        if len(values) >= 5:
            tooltip = values[4]
        if len(values) >= 6:
            # If type specified, use that
            if isinstance(values[5], str):
                data_type = values[5]
            # Else get additional parameters for float
            else:
                decimal, min, max = values[5]
                validation_func = get_validation_func(decimal, min, max)
        if len(values) >= 7:
            status_enable = values[6]
        if len(values) >= 8:
            alter_values_dict = values[7]
            alter_structure = True
        fields[modify_code+key] = get_field_dict(data_type, caption, unit, value, 
                                                selection_list=selection_list,
                                                tooltip=tooltip,
                                                status_inactivate=False,
                                                status_enable=status_enable,
                                                alter_structure=alter_structure,
                                                alter_values_dict=alter_values_dict,
                                                validation_func=validation_func)
    return fields

def update_params_from_params(parameters, new_parameters):
    for key, values in new_parameters.items():
        if key in parameters:
            parameters[key][2] = values[2]
            if len(parameters[key]) >= 7:
                parameters[key][6] = values[6]

def update_params_from_fields(parameters, fields):
    for key, field in fields.items():
        if key in parameters:
            parameters[key][2] = field['value']
            if len(parameters[key]) >= 7:
                parameters[key][6] = field['status_enable']

def validate_protection_data_struct(data_struct, code):
    check_keys_1 = {'type', 'parameters', 'data', 'graph_model'}
    if code in ['pcurve_l', 'pcurve_g']:
        prot_type = 'protection'
    elif code in ['dcurve']:
        prot_type = 'damage'
    else:
        return False
    if isinstance(data_struct, dict):
        keys = set(data_struct.keys())
        if check_keys_1 & keys == check_keys_1:
            if (isinstance(data_struct['type'], str) and data_struct['type'] == prot_type) and \
               (isinstance(data_struct['parameters'], dict)) and \
               (isinstance(data_struct['graph_model'], list)):
                return True
    return False

def get_blank_data_struct(data_type='protection'):
    data_struct = { 'type'          : data_type,
                    'parameters'    : {},
                    'data'          : {'curve_u': [], 'curve_l': []},
                    'graph_model'   : []}
    return data_struct

# Default settings (templates: use new_program_settings()/new_project_settings()
# for an independent copy, D4)

default_program_settings = {'Defaults':{'drawing_field_dept':    get_field_dict('str', 'Responsible department', '', '', status_inactivate=False),
                            'drawing_field_techref': get_field_dict('str', 'Technical reference', '', '', status_inactivate=False),
                            'drawing_field_created': get_field_dict('str', 'Created by', '', '', status_inactivate=False),
                            'drawing_field_approved':get_field_dict('str', 'Approved by', '', '', status_inactivate=False),
                            'drawing_field_lang':    get_field_dict('str', 'Language code', '', 'en', status_inactivate=False),
                            'drawing_field_address': get_field_dict('multiline_str', 'Address', '', 'WING\nORGANISATION\nLOCATION', status_inactivate=False)},
                            'Interface':{'dark_mode' : get_field_dict('bool', 'Enable dark theme', '(Requires program restart to take effect)', False, status_inactivate=False),
                                         'advanced_mode' : get_field_dict('bool', 'Enable advanced mode', '(Requires program restart to take effect)', False, status_inactivate=False),
                                         'show_graphs' : get_field_dict('bool', 'Show graphs in field view', '(Requires program restart to take effect)', True, status_inactivate=False),
                                         'drawing_font':    get_field_dict('font', 'Drawing Font', '', style.SCHEM_FONT_FACE + ' ' + str(style.SCHEM_FONT_SIZE), status_inactivate=False),
                                         'graph_font':    get_field_dict('font', 'Graph Font', '', style.GRAPH_FONT_FACE + ' ' + str(style.GRAPH_FONT_SIZE), status_inactivate=False),
                                         'report_font':    get_field_dict('font', 'Report Font', '', style.REPORT_FONT_FACE + ' ' + str(style.REPORT_FONT_SIZE), status_inactivate=False),
                                         'report_graph_font':    get_field_dict('font', 'Report Graph Font', '', style.REPORT_GRAPH_FONT_FACE + ' ' + str(style.REPORT_GRAPH_FONT_SIZE), status_inactivate=False)},
                            'Paths': {'library_path':    get_field_dict('path', 'User Library', '', '')}}
                                         
default_project_settings = {'Information': {'project_name': get_field_dict('str', 'Project Name', '', 'PROJECT', status_inactivate=False),
                            'drawing_field_dept':    get_field_dict('str', 'Responsible department', '', '', status_inactivate=False),
                            'drawing_field_techref': get_field_dict('str', 'Technical reference', '', '', status_inactivate=False),
                            'drawing_field_created': get_field_dict('str', 'Created by', '', '', status_inactivate=False),
                            'drawing_field_approved':get_field_dict('str', 'Approved by', '', '', status_inactivate=False),
                            'drawing_field_lang':    get_field_dict('str', 'Language code', '', 'en', status_inactivate=False),
                            'drawing_field_address': get_field_dict('multiline_str', 'Address', '', 'WING\nORGANISATION\nLOCATION', status_inactivate=False)},
                             
                             'Simulation':{'run_diagnostics' : get_field_dict('bool', 'Run diagnostics', '', True, status_inactivate=False),
                             # Power flow
                             'sub_head_power_flow' : get_field_dict('heading', 'Power Flow', '', '', status_inactivate=False),
                             'run_powerflow' : get_field_dict('bool', 'Run time series power flow', '', False, status_inactivate=False),
                             'pf_method' : get_field_dict('str', 'Power flow method', '', 'Power flow', 
                                                          status_inactivate=False,
                                                          selection_list=['Power flow', 'Power flow with diversity', 'Time series'] ),
                             'power_flow_3ph' : get_field_dict('bool', 'Enable assymetric power flow calculation', '', False, status_inactivate=False),
                             # Short circuit
                             'sub_head_sc' : get_field_dict('heading', 'Short Circuit Calculations', '', '', status_inactivate=False),
                             'run_sc_sym' : get_field_dict('bool', 'Run symmetric short circuit calculation', '', False, status_inactivate=False),
                             'run_sc_gf' : get_field_dict('bool', 'Run line to ground short circuit calculation', '', False, status_inactivate=False),
                             'show_impedances' : get_field_dict('bool', 'Display short circuit impedance values', '', False, status_inactivate=False),
                             # Simulation parameters
                             'export_results' : get_field_dict('bool', 'Export results of simulation', '', False, status_enable=False),
                             'sub_head_sim_param' : get_field_dict('heading', 'Simulation Parameters', '', '', status_inactivate=False),
                             'lv_tol_percent': get_field_dict('float', 'Grid voltage tolerance', '%', 6, selection_list=[6,10], status_inactivate=False),
                             'grid_frequency': get_field_dict('float', 'Grid Frequency', 'Hz', 50, selection_list=[50,60], status_inactivate=False),
                             'r_fault_ohm': get_field_dict('float', 'Fault resistance', 'Ohm', 0, status_inactivate=False),
                             'x_fault_ohm': get_field_dict('float', 'Fault reactance', 'Ohm', 0, status_inactivate=False)},

                             'Reports':{'export_elements' : get_field_dict('bool', 'Export elements', '', True, status_inactivate=False),
                                        'export_boq' : get_field_dict('bool', 'Export BOQ', '', True, status_inactivate=False),
                                        'export_loadprofiles' : get_field_dict('bool', 'Export load profiles', '', True, status_inactivate=False),
                                        'export_analysis' : get_field_dict('bool', 'Export analysis results', '', True, status_inactivate=False),
                                        'export_graphs' : get_field_dict('bool', 'Include graphs in report', '', False, status_inactivate=False),},
                             
                             'Rules Check':{'line_max_loss' : get_field_dict('float', 'Maximum line loss', '%', 3, status_inactivate=False),
                                            'max_disc_time' : get_field_dict('float', 'Maximum disconnection time for faults', 's', 5, status_inactivate=False),
                                            'max_voltage_drop' : get_field_dict('float', 'Maximum voltage drop at loads', '%', 5, status_inactivate=False)}}

loadprofile_blank_fields = {'name': get_field_dict('str', 'Title', '', ''),
                            'name1': get_field_dict('str', 'Sub Title', '', '')}
for slno in range(0,24):
    loadprofile_blank_fields[str(slno)] = get_field_dict('float', str(slno), '', 0)


def new_program_settings():
    """Return an independent copy of the default program settings"""
    return copy.deepcopy(default_program_settings)

def new_project_settings():
    """Return an independent copy of the default project settings (D4)"""
    return copy.deepcopy(default_project_settings)
