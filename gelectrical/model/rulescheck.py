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
from collections.abc import MutableMapping

# local files import
from .. import misc

# Get logger object
log = logging.getLogger(__name__)

# Helper functions and classes

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
        self.r = FieldDict(element.res_fields)
        self.f = FieldDict(element.fields)

def get_message_data_struct(network, results_dict):
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
    message_list = []
    for caption, result_eids in results_dict.items():
        ref_eid = ', '.join([network.base_elements[tuple(eid)].fields['ref']['value'] for eid in result_eids])
        message = caption + '\nElements: ' + ref_eid
        element_list = [['element', tuple(result_eids)]]
        message_list.append((message, element_list))
    return {'Electrical Rules Check': message_list}

# Rules check rules and functions

electrical_rules = {
'Cable overload protection by upstream switch': ('arg1 <= arg2', 
                    (misc.LINE_ELEMENT_CODES, 'e.f.max_i_ka >= 0.1', 'all'), 
                    ('self', 'e.f.max_i_ka'),
                    ('upstream', misc.SWITCH_ELEMENT_CODES, 'e.f.In'))
}

def rules_check(network, rules):
    """
    Conduct rules check as per defined rules.

    INPUT:
    network       : Network model
    program_state : Program state with project settings etc

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
    results_dict = dict()

    for eid, element in network.base_elements.items():
        cur_element_var = Element(element)
        # Evaluate each rule for selected element
        for rule_caption, rule in rules.items():
            failure_flag = False  # Tracks rule failure
            run_evaluation = True  # Tracks if <check_expression> evalation can be run
            check_expression, (match_codes, match_expression, match_type), *args = rule
            # Check if match_criterion satisfied
            if element.code in match_codes and eval(match_expression, {'e':cur_element_var}):
                args_eval = []
                # Fill arguments from rule
                for arg in args:
                    if arg[0] == 'self':
                        expr = arg[1]
                        args_eval.append([eval(expr, {'e':cur_element_var})])
                    elif arg[0] == 'upstream':
                        codes = arg[1]
                        expr = arg[2]
                        arg_element_dict = network.get_upstream_element(eid, codes)
                        if arg_element_dict:
                            args_eval_sub = []
                            for arg_element in arg_element_dict.values():
                                e = Element(arg_element)
                                args_eval_sub.append(eval(expr, {'e':e}))
                            args_eval.append(args_eval_sub)
                        else:
                            if match_type in ('all', 'any'):
                                failure_flag = True
                            run_evaluation = False
                            break
                if run_evaluation:
                    # Setup argument pairs for evaluation
                    args_eval_pair = []
                    for arg1 in  args_eval[0]:
                        if len(args) == 2:
                            for arg2 in  args_eval[1]:
                                args_eval_pair.append((arg1, arg2))
                        else:
                            args_eval_pair.append(arg1, 0)
                    # Evaluate argument pairs
                    for (arg1, arg2) in args_eval_pair:
                        if eval(check_expression, {'arg1':arg1, 'arg2':arg2}):
                            if match_type in ('any', 'any_ifexist'):
                                break
                        else:
                            if match_type in ('all', 'all_ifexist'):
                                failure_flag = True
                                break
                if failure_flag:
                    if rule_caption not in results_dict:
                        results_dict[rule_caption] = set()
                    results_dict[rule_caption].add(eid)
    return results_dict

def electrical_rules_check(network):
    """Helper function to call electrical rules check"""
    results_dict = rules_check(network, electrical_rules)
    message_data = get_message_data_struct(network, results_dict)
    return message_data