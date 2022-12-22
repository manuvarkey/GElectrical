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
    def get_message(results_dict):
        message_list = []
        for caption, result_eids in results_dict.items():
            ref_eid = ', '.join([network.base_elements[tuple(eid)].fields['ref']['value'] for eid in result_eids])
            message = caption + '\nElements: ' + ref_eid
            element_list = [['element', tuple(result_eids)]]
            message_list.append((message, element_list))
        return message_list
    message_list_pass = get_message(results_dict_pass)
    message_list_fail = get_message(results_dict_fail)
    return {'Electrical Rules Check - Failed': message_list_fail,
            'Electrical Rules Check - Passed': message_list_pass}

# Rules check rules and functions

electrical_rules = {
'Line loading % < 100%': ('arg1 <= arg2', 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.r.loading_percent_max'),
                    ('constant', 100)),
'Line loss % < x%': ('arg1 <= sr.line_max_loss', 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.r.pl_mw_max')),
'Line overload protection by upstream switch': ('arg1 <= arg2', 
                    (misc.LINE_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.f.max_i_ka'),
                    ('upstream', misc.SWITCH_ELEMENT_CODES, 'e.f.In')),
'Transformer loading % < 100%': ('arg1 <= 100', 
                    (misc.TRAFO_ELEMENT_CODES, 'True', 'all'), 
                    ('self', 'e.r.loading_percent_max'))
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
            if element.code in match_codes and eval(match_expression, {'e':cur_element_var,'sr':sr,'ss':ss}):
                args_eval = []

                # Fill arguments from rule
                for arg in args:
                    if arg[0] == 'self':
                        expr = arg[1]
                        args_eval.append([eval(expr, {'e':cur_element_var,'sr':sr,'ss':ss})])

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
                                args_eval_sub.append(eval(expr, {'e':e,'sr':sr,'ss':ss}))
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
                            if element_sub.code in codes and eval(cond_expr, {'e':sub_element_var,'sr':sr,'ss':ss}):
                                arg_element_dict[eid_sub] = sub_element_var
                        if arg_element_dict:
                            args_eval_sub = []
                            for arg_element in arg_element_dict.values():
                                args_eval_sub.append(eval(expr, {'e':arg_element,'sr':sr,'ss':ss}))
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
                        if len(args) == 2:
                            for arg2 in  args_eval[1]:
                                args_eval_pair.append((arg1, arg2))
                        else:
                            args_eval_pair.append((arg1, 0))
                    # Evaluate argument pairs
                    for (arg1, arg2) in args_eval_pair:
                        if eval(check_expression, {'arg1':arg1, 'arg2':arg2,'sr':sr,'ss':ss}):
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