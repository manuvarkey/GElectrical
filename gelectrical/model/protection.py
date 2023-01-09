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

import os, math
import numpy as np
from shapely import Polygon, Point, LineString

# local files import
from .. import misc
from ..misc import FieldDict


class ProtectionModel():
    """Generic protection base element"""

    def __init__(self, data_struct):
        """ARGUMENTS:
            data_struct: Protection datastructure of following format
            
            { 
                'type': 'protection'
                'var': {'var_1': [caption, unit, value, value_list], 
                        'var_2': [caption, unit, value, value_list] ... },
                'curve_u': [('point', i1, t1), 
                          ('iec', tms, i_n, k, c, alpha, i1, i2, n), 
                          ('iec_inverse', tms, i_n, i1, i2, n), 
                          ('iec_v_inverse', tms, i_n, i1, i2, n), 
                          ('iec_e_inverse', tms, i_n, i1, i2, n), 
                          ('ieee_m_inverse', tms, i_n, i1, i2, n), 
                          ('ieee_v_inverse', tms, i_n, i1, i2, n), 
                          ('ieee_e_inverse', tms, i_n, i1, i2, n), 
                            ... ],
                'curve_l': ...
            }
        """
        self.data_struct = data_struct
        # Generated variables
        self.curve_upper = None  # Upper t vs I protection curve as list of tuples
        self.curve_lower = None  # Lower t vs I protection curve as list of tuples
        self.polygon = None
        self.linestring_upper = None
        self.linestring_lower = None
        
    def get_data_fields(self, title, modify_code=''):
        fields = dict()
        for key, (caption, unit, value, selection_list) in self.data_struct['var'].items():
            fields[modify_code+key] = misc.get_field_dict('float', caption, unit, value, 
                                                            selection_list=selection_list, 
                                                            status_inactivate=False)
        return fields

    def evaluate_curves(self, fields):
        
        # Variables for evaluation
        f = FieldDict(fields)
        
        # Functions for curve evaluation
        def point(i1, t1):
            return (i1,), (t1,)

        def iec(tms, i_n, k, c, alpha, i1, i2, n):
            i_array = np.geomspace(i1,i2,n)
            t_array = tms*(k/((i_array/i_n)**alpha - 1) + c)
            return list(i_array), list(t_array)

        iec_inverse = lambda tms, i1, i2, n: iec(tms, f.In, 0.14, 0, 0.02, i1, i2, n)
        iec_v_inverse = lambda tms, i1, i2, n: iec(tms, f.In, 13.5, 0, 1, i1, i2, n)
        iec_e_inverse = lambda tms, i1, i2, n: iec(tms, f.In, 80, 0, 2, i1, i2, n)
        ieee_m_inverse = lambda tms, i1, i2, n: iec(tms, f.In, 0.0515, 0.1140, 0.02, i1, i2, n)
        ieee_v_inverse = lambda tms, i1, i2, n: iec(tms, f.In, 19.61, 0.491, 2, i1, i2, n)
        ieee_e_inverse = lambda tms, i1, i2, n: iec(tms, f.In, 28.2, 0.1217, 2, i1, i2, n)
        
        def eval_curve(curve):
            var_dict = {'f': f}
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
        self.curve_upper = eval_curve(self.data_struct['curve_u'])
        self.curve_lower = eval_curve(self.data_struct['curve_l'])

        # Geometry elements
        self.linestring_upper = LineString(reversed(self.curve_upper))
        self.linestring_lower = LineString(self.curve_lower)
        self.polygon = Polygon(list(reversed(self.curve_upper)) + self.curve_lower)

    def get_graph(self, title):
        polygon_pnts = np.array((self.polygon.exterior.coords))
        xval = list(polygon_pnts[:,0])
        yval = list(polygon_pnts[:,1])
        graph_model = ['Protection Curve', [{'mode':misc.GRAPH_DATATYPE_POLYGON, 'title':title, 'xval':xval, 'yval': yval},]]
        return graph_model

