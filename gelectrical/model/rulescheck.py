#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# project
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

import logging, math

# local files import
from .. import misc
from ..misc import FieldDict, Element
# Get logger object
log = logging.getLogger(__name__)


# Helper functions and classes

def get_message_data_struct(network, results_dict_pass, results_dict_fail):
    """
    INPUT:
    results_dict  : Rules check result

    OUTPUT:
    Format: {'Electrical Rules Check': [
                    [{'message': 'Title goes here', 'type': 'warning'}, [['element', [(k1,k2), ...]]],
                    [{'message': 'Title goes here', 'type': 'error'}, [['element', [(k1,k2), ...]]],
                    ['Title goes here', [['element', [(k1,k2), ...]]],
                        ...
                    ]
            }
    """
    def get_message(results_dict, warning=False):
        message_list = []
        for caption, result_eids in results_dict.items():
            ref_eid = ', '.join([network.base_elements[tuple(eid)].fields['ref']['value'] for eid in result_eids])
            message = caption + '\nElements: ' + ref_eid
            element_list = [['element', tuple(result_eids)]]
            if warning:
                message_list.append(({'message': message, 'type': 'warning'}, element_list))
            else:
                message_list.append((message, element_list))
        return message_list
    message_list_pass = get_message(results_dict_pass)
    message_list_fail = get_message(results_dict_fail, warning=True)
    return {'Electrical Rules Check - Failed': message_list_fail,
            'Electrical Rules Check - Passed': message_list_pass}

# Rules check rules and functions

electrical_rules = {
# LINES
'Line loading % < 100%': ('arg1 <= arg2', 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.r.loading_percent_max'),
                    ('constant', 100)),
'Line loss % < X %': ('arg1 <= sr.line_max_loss', 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.r.pl_perc_max')),
'Line protection by upstream breaker': ("arg2[0].contains(arg1[0], curve='upper', direction='right', i_max=arg3[0], scale=arg2[2]/arg3[1]) and arg1[1] >= arg2[1]", 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.damage_model.linestring_upper_log, e.f.max_i_ka * e.f.df * e.f.parallel * 1000'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.f.In, e.r.vn_kv'),
                    ('downstream_node', 'max(e.r.ikss_ka_3ph_max, e.r.ikss_ka_1ph_max)*1000, e.r.vn_kv')),
'Automatic disconnection time of line < X s': ("max(arg1[1].get_current(sr.max_disc_time))*(arg2[1]/arg1[2]) < arg2[0] if arg1[1] else max(arg1[0].get_current(sr.max_disc_time))*(arg2[1]/arg1[2]) < arg2[0]", 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.ground_protection_model, e.r.vn_kv'),
                    ('downstream_node', 'min(e.r.ikss_ka_3ph_min, e.r.ikss_ka_1ph_min)*1000, e.r.vn_kv')),
'CPE conductor sized for fault current': ("arg3 / (max(arg1[1].get_time(arg2[0]*(arg2[1]/arg1[2]))) if arg1[1] else max(arg1[0].get_time(arg2[0]*(arg2[1]/arg1[2]))))**0.5 > arg2[0]", 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.ground_protection_model, e.r.vn_kv'),
                    ('downstream_node', 'e.r.ikss_ka_1ph_max*1000, e.r.vn_kv'),
                    ('self', 'e.f.cpe_sc_current_rating * e.f.parallel * 1000')),
# TRANSFORMER
'Transformer loading % < 100%': ('arg1 <= 100', 
                    (['element_transformer'], 'True', 'all'), 
                    ('self', 'e.r.loading_percent_max')),
'Transformer protection by upstream breaker': ("arg2[0].contains(arg1[0], curve='upper', direction='right', i_max=arg3, scale=arg2[1]/arg1[1])", 
                    (['element_transformer'], 'True', 'all'), 
                    ('self', 'e.damage_model.linestring_upper_log, e.f.vn_lv_kv'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.r.vn_kv'),
                    ('downstream_node', 'max(e.r.ikss_ka_3ph_max, e.r.ikss_ka_1ph_max)*1000')),
'Transformer inrush current coordination with upstream breaker': ("arg2[0].contains(arg1[0], curve='lower', direction='left', scale=arg2[1]/arg1[1])", 
                    (['element_transformer'], 'True', 'all'), 
                    ('self', 'e.damage_model.linestring_lower_log, e.f.vn_lv_kv'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.r.vn_kv')),
# MOTORS
'Motor protection by upstream breaker': ("arg2[0].contains(arg1, curve='upper', direction='right', i_max=arg3[0], scale=arg2[1]/arg3[1])", 
                    (misc.MOTOR_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.damage_model.linestring_upper_log'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.r.vn_kv'),
                    ('upstream_node', 'max(e.r.ikss_ka_3ph_max, e.r.ikss_ka_1ph_max)*1000, e.r.vn_kv')),
'Motor inrush current coordination with upstream breaker': ("arg2[0].contains(arg1, curve='lower', direction='left', scale=arg2[1]/arg3)", 
                    (misc.MOTOR_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.damage_model.linestring_lower_log'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.r.vn_kv'),
                    ('upstream_node', 'e.r.vn_kv')),
# BREAKERS
'Breaker short circuit current < Fault level': ("arg1 > arg2", 
                    (misc.PROTECTION_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.f.Isc*1000'),
                    ('downstream_node', 'max(e.r.ikss_ka_3ph_max, e.r.ikss_ka_1ph_max)*1000')),
'Breaker coordination with upstream': ("arg2[0].contains(arg1[0], curve='lower', direction='left', i_max=arg3, scale=arg2[1]/arg1[1])", 
                    (misc.PROTECTION_ELEMENT_CODES, 'True', 'all_ifexist'), 
                    ('self', 'e.line_protection_model.linestring_upper_log, e.r.vn_kv'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.r.vn_kv'),
                    ('downstream_node', 'max(e.r.ikss_ka_3ph_max, e.r.ikss_ka_1ph_max)*1000')),
# LOADS
'Automatic disconnection time of load < X s': ("max(arg1[1].get_current(sr.max_disc_time))*(arg2[1]/arg1[2]) < arg2[0] if arg1[1] else max(arg1[0].get_current(sr.max_disc_time))*(arg2[1]/arg1[2]) < arg2[0]", 
                    (misc.LOAD_ELEMENT_CODES, 'True', 'all'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.line_protection_model, e.ground_protection_model, e.r.vn_kv'),
                    ('upstream_node', 'min(e.r.ikss_ka_3ph_min, e.r.ikss_ka_1ph_min)*1000, e.r.vn_kv')),
'Voltage drop  < X %': ("arg1 <= sr.max_voltage_drop", 
                    (misc.LOAD_ELEMENT_CODES, 'True', 'all'),
                    ('upstream_node', 'e.r.delv_perc_max')),
# CONNECTIVITY
'Three phase load connected to three phase line': ("arg1 not in ('SP', 'SPN', 'DP')", 
                    (('element_load', 'element_async_motor_3ph'), 'True', 'all_ifexist'),
                    ('upstream', misc.PROTECTION_ELEMENT_CODES, 'e.f.poles')),

}

def rules_check(network, sim_settings, rules_settings, rules):
    """
    Conduct rules check as per defined rules.

    INPUT:
    network        : Network model
    sim_settings   : Simulation settings
    rules_settings : Rules check settings

    OUTPUT:
    results_dict  : Rules check result
        Format: {caption1: set(eid1, eid2 ...), caption2:}

    Rules are added to the rules dict with <rule caption> as key
    Rules are defined in the following format
        (<check_expression>, <match_criterion>, <arg1>, <arg2>)
    Where:
        <check_expression> : Same as <bool_expression> below with arg1, arg2, ... corresponding to arguments
        <match_criterion>  : ([code1, code2 ...], <bool_expression>, <'all'|'all_ifexist'|'any'|'any_ifexist'>)
        <argn>             : ('self', <expression>)
                                ('upstream', [code1, code2 ...], <expression>)
                                ('downstream', [code1, code2 ...], <expression>)
                                ('upstream_node', <expression>)
                                ('downstream_node', <expression>)
                                ('constant', <constant>)
                                ('match', [code1, code2 ...], <bool_expression>, <expression>)
        <bool_expression>  : Conditional expression using class notation to access elements
            ex: "e.f.i_ka < e.r.i_ka_max"
        <expression>       : Expression using class notation to access elements
            ex: "e.f.i_ka + e.f.i_ka_max"
    """

    def eval_(expression_, dict_file):
        """Fail safe eval function"""
        try:
            return eval(expression_, dict_file)
        except:
            return None

    results_dict_pass = dict()
    results_dict_fail = dict()
    ss = FieldDict(sim_settings)
    sr = FieldDict(rules_settings)

    for eid, element in network.base_elements.items():
        cur_element_var = Element(element)

        # Evaluate each rule for selected element
        for rule_caption, rule in rules.items():
            failure_flag = False  # Tracks rule failure
            run_evaluation = True  # Tracks if <check_expression> evalation can be run
            check_expression, (match_codes, match_expression, match_type), *args = rule
            
            # Check if match_criterion satisfied
            if element.code in match_codes and eval_(match_expression, {'e':cur_element_var,'sr':sr,'ss':ss}):
                args_eval = []

                # Fill arguments from rule
                for arg in args:
                    if arg[0] == 'self':
                        expr = arg[1]
                        args_eval.append([eval_(expr, {'e':cur_element_var,'sr':sr,'ss':ss})])

                    elif arg[0] in ('upstream', 'downstream', 'upstream_node', 'downstream_node'):
                        if arg[0] == 'upstream':
                            codes = arg[1]
                            expr = arg[2]
                            arg_element_dict = network.get_upstream_element(eid, codes)
                        elif arg[0] == 'downstream':
                            codes = arg[1]
                            expr = arg[2]
                            arg_element_dict = network.get_downstream_element(eid, codes)
                        elif arg[0] == 'upstream_node':
                            expr = arg[1]
                            arg_element_dict = network.get_upstream_node_of_element(eid)
                        elif arg[0] == 'downstream_node':
                            expr = arg[1]
                            arg_element_dict = network.get_downstream_node_of_element(eid)
                        if arg_element_dict:
                            args_eval_sub = []
                            for arg_element in arg_element_dict.values():
                                e = Element(arg_element)
                                args_eval_sub.append(eval_(expr, {'e':e,'sr':sr,'ss':ss}))
                            args_eval.append(args_eval_sub)
                        else:
                            if match_type in ('all', 'any'):
                                failure_flag = True
                            run_evaluation = False
                            break

                    elif arg[0] == 'constant':
                        const = arg[1]
                        args_eval.append([const])

                    elif arg[0] in ('match'):
                        codes = arg[1]
                        cond_expr = arg[2]
                        expr = arg[3]
                        arg_element_dict = dict()
                        for eid_sub, element_sub in network.base_elements.items():
                            sub_element_var = Element(element_sub)
                            if element_sub.code in codes and eval_(cond_expr, {'e':sub_element_var,'sr':sr,'ss':ss}):
                                arg_element_dict[eid_sub] = sub_element_var
                        if arg_element_dict:
                            args_eval_sub = []
                            for arg_element in arg_element_dict.values():
                                args_eval_sub.append(eval_(expr, {'e':arg_element,'sr':sr,'ss':ss}))
                            args_eval.append(args_eval_sub)
                        else:
                            if match_type in ('all', 'any'):
                                failure_flag = True
                            run_evaluation = False
                            break

                # Run evaluation of check expression
                if run_evaluation:
                    # Setup argument pairs for evaluation
                    args_eval_pair = []
                    for arg1 in  args_eval[0]:
                        if len(args) == 3:
                            for arg2 in  args_eval[1]:
                                for arg3 in  args_eval[2]:
                                    args_eval_pair.append((arg1, arg2, arg3))
                        elif len(args) == 2:
                            for arg2 in  args_eval[1]:
                                args_eval_pair.append((arg1, arg2, 0))
                        else:
                            args_eval_pair.append((arg1, 0, 0))
                    # Evaluate argument pairs
                    for (arg1, arg2, arg3) in args_eval_pair:
                        if eval_(check_expression, {'arg1':arg1, 'arg2':arg2, 'arg3':arg3, 'sr':sr, 'ss':ss}):
                            if match_type in ('any', 'any_ifexist'):
                                break
                        else:
                            if match_type in ('all', 'all_ifexist'):
                                failure_flag = True
                                break

                # If failure add to result
                if failure_flag:
                    if rule_caption not in results_dict_fail:
                        results_dict_fail[rule_caption] = set()
                    results_dict_fail[rule_caption].add(eid)
                else:
                    if rule_caption not in results_dict_pass:
                        results_dict_pass[rule_caption] = set()
                    results_dict_pass[rule_caption].add(eid)


    return results_dict_pass, results_dict_fail

def electrical_rules_check(network, sim_settings, rules_settings):
    """Helper function to call electrical rules check"""
    results_dict_pass, results_dict_fail = rules_check(network, sim_settings, rules_settings, electrical_rules)
    message_data = get_message_data_struct(network, results_dict_pass, results_dict_fail)
    return message_data