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
        self.f = FieldDict(element.res_fields)


class RulesCheck:

    def __init__(self, network, program_state):
        """
        .Run project rules check

        INPUT:
        network       : Network model
        program_state : Program state with project settings etc

        OUTPUT:
        diag_results  : Diagnostic results

        Format: {'Head 1': [{'message': 'Title goes here', 'type': 'error'}, ['node', [node_ids]],
                           [{'message': 'Title goes here', 'type': 'warning'}, ['element', [(k1,k2), ...]],
                               ...
                           ],
                 'Head 2':     ...
                   ...
                }
        """
        self.network = network
        self.program_state = program_state
        diag_results = self.rules_check()
        return diag_results

    def rules_check(self):
        """
        Conduct rules check as per defined rules.
        Rules are added to the rules dict with <rule caption> as key
        Rules are defined in the following format
            (<check_expression>, <match_criterion>, <arg1>, <arg2> ...)
        Where:
            <check_expression> : Same as <bool_expression> below with arg1, arg2, ... corresponding to arguments
            <match_criterion>  : ([code1, code2 ...], <bool_expression>)
            <argn>             : ('self', <expression>)
                                 ('upstream', [code1, code2 ...], <expression>)
                                 ('downstream', [code1, code2 ...], <expression>)
                                 ('constant', <constant>)
                                 ('match', [code1, code2 ...], <bool_expression>, <expression>)
            <bool_expression>  : Conditional expression using class notation to access elements
                ex: "e.f.i_ka < e.r.i_ka_max"
            <expression>       : Expression using class notation to access elements
                ex: "e.f.i_ka + e.f.i_ka_max"
        """
        check_results = dict()
        rules = dict()
        rules['Cable overload protection by upstream switch'] = ('arg1 <= arg2', 
                        (misc.LINE_ELEMENT_CODES, 'e.f.max_i_ka >= 0.1'), 
                        ('self', 'e.f.max_i_ka'),
                        ('upstream', misc.SWITCH_ELEMENT_CODES, 'e.f.In'))

        for eid, element in self.network.base_elements.items():
            for caption, rule in rules:
                check_expression, match_criterion, *args = rule
                (codes, main_expression) = match_criterion
                args_eval = []
                for arg in args:
                    if arg[0] == 'self':
                        expr = arg[1]
                        e = Element(arg_elements[0])
                        args_eval.append(eval(expr))
                    elif arg[0] == 'upstream':
                        codes = arg[1]
                        expr = arg[2]
                        arg_elements = self.network.get_upstream_element(eid, codes)
                        if arg_elements:
                            e = Element(arg_elements[0])
                            args_eval.append(eval(expr))

                # check_results[caption] = 

        return check_results

