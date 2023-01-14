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

import copy
import numpy as np
from shapely import Polygon, Point, LineString

# local files import
from .. import misc
from ..misc import FieldDict


class ProtectionModel():
    """Generic protection base element"""

    def __init__(self, title, parameters, curve_u, curve_l):
        """
            data_struct: Protection datastructure of following format
            
            { 
                'type': 'protection'
                'parameters': { 'var_1': [caption, unit, value, value_list], 
                                'var_2': [caption, unit, value, value_list] ... },
                'data': {'curve_u': [('point', i1, t1), 
                                ('iec', tms, i_n, k, c, alpha, i1, i2, n), 
                                ('iec_inverse', tms, i_n, i1, i2, n), 
                                ('iec_v_inverse', tms, i_n, i1, i2, n), 
                                ('iec_e_inverse', tms, i_n, i1, i2, n), 
                                ('ieee_m_inverse', tms, i_n, i1, i2, n), 
                                ('ieee_v_inverse', tms, i_n, i1, i2, n), 
                                ('ieee_e_inverse', tms, i_n, i1, i2, n), 
                                    ... ],
                        'curve_l': ...}
                'graph_model'      : (title, models),
                'graph_options'    : (xlim, ylim, xlabel, ylabel)}
            }
        """
        self.title = title
        self.data_struct = {'type'          : 'protection',
                            'parameters'    : parameters,
                            'data'          : {'curve_u': curve_u,'curve_l': curve_l},
                            'graph_model'   : [],
                            'graph_options' : ( misc.GRAPH_PROT_CURRENT_LIMITS, 
                                                misc.GRAPH_PROT_TIME_LIMITS, 
                                                'I (A)', 
                                                'Time (s)')}
        # Generated variables
        self.curve_upper = None  # Upper t vs I protection curve as list of tuples
        self.curve_lower = None  # Lower t vs I protection curve as list of tuples
        self.polygon = None
        self.linestring_upper = None
        self.linestring_lower = None

    @classmethod
    def new_from_data(cls, data_struct):
        if data_struct['type'] == 'protection':
            title = data_struct['graph_model'][0]
            parameters = data_struct['parameters']
            curve_u = data_struct['data']['curve_u']
            curve_l = data_struct['data']['curve_l']
            return cls(title, parameters, curve_u, curve_l)
        else:
            raise ValueError('Wrong data structure passed')

    def get_data_fields(self, modify_code=''):
        fields = dict()
        for key, (caption, unit, value, selection_list) in self.data_struct['parameters'].items():
            fields[modify_code+key] = misc.get_field_dict('float', caption, unit, value, 
                                                            selection_list=selection_list, 
                                                            status_inactivate=False)
        return fields

    def update_graph(self):
        polygon_pnts = np.array((self.polygon.exterior.coords))
        xval = list(polygon_pnts[:,0])
        yval = list(polygon_pnts[:,1])
        graph_model = [self.title, [{'mode':misc.GRAPH_DATATYPE_POLYGON, 
                                        'title':self.title, 
                                        'xval':xval, 
                                        'yval': yval},]]
        self.data_struct['graph_model'] = graph_model

    def update_parameters(self, parameters):
        for key, field in parameters.items():
            if key in self.data_struct['parameters']:
                self.data_struct['parameters'][key][2] = field[2]

    def evaluate_curves(self, fields, data_fields=None):
        
        # Variables for evaluation
        f = FieldDict(fields)
        if data_fields:
            d = FieldDict(data_fields)
        else:
            d = FieldDict(self.get_data_fields())
        
        # Functions for curve evaluation
        def point(i1, t1):
            return (i1,), (t1,)

        def iec(tms, i_n, k, c, alpha, i1, i2, n):
            i_array = np.geomspace(i1,i2,num=n)
            t_array = tms*(k/((i_array/i_n)**alpha - 1) + c)
            return list(i_array), list(t_array)

        iec_inverse = lambda tms, i_n, i1, i2, n: iec(tms, i_n, 0.14, 0, 0.02, i1, i2, n)
        iec_v_inverse = lambda tms, i_n, i1, i2, n: iec(tms, i_n, 13.5, 0, 1, i1, i2, n)
        iec_e_inverse = lambda tms, i_n, i1, i2, n: iec(tms, i_n, 80, 0, 2, i1, i2, n)
        ieee_m_inverse = lambda tms, i_n, i1, i2, n: iec(tms, i_n, 0.0515, 0.1140, 0.02, i1, i2, n)
        ieee_v_inverse = lambda tms, i_n, i1, i2, n: iec(tms, i_n, 19.61, 0.491, 2, i1, i2, n)
        ieee_e_inverse = lambda tms, i_n, i1, i2, n: iec(tms, i_n, 28.2, 0.1217, 2, i1, i2, n)
        
        def eval_curve(curve):
            var_dict = {'f': f, 'd': d}
            func_dict = {   'point'         : point,
                            'iec'           : iec,
                            'iec_inverse'   : iec_inverse,
                            'iec_v_inverse' : iec_v_inverse,
                            'iec_e_inverse' : iec_e_inverse,
                            'ieee_m_inverse': ieee_m_inverse,
                            'ieee_v_inverse': ieee_v_inverse,
                            'ieee_e_inverse': ieee_e_inverse
                        }
            # Evaluate curve
            curve_i = []
            curve_t = []
            for func_str, *data in curve:
                func = eval(func_str, func_dict)
                data_eval = [x if isinstance(x, (int, float)) else eval(x, var_dict) for x in data]
                i_array, t_array = func(*data_eval)
                curve_i += i_array
                curve_t += t_array
            curve = [(i,t) for i,t in zip(curve_i, curve_t)]
            return curve

        # Evaluate curves
        self.curve_upper = eval_curve(self.data_struct['data']['curve_u'])
        self.curve_lower = eval_curve(self.data_struct['data']['curve_l'])

        # Geometry elements
        self.linestring_upper = LineString(reversed(self.curve_upper))
        self.linestring_lower = LineString(self.curve_lower)
        self.polygon = Polygon(list(reversed(self.curve_upper)) + self.curve_lower)

    def get_evaluated_model(self, fields, data_fields=None):
        self.evaluate_curves(fields, data_fields)  # Evaluate curves
        self.update_graph()  # Update graph
        return copy.deepcopy(self.data_struct)

