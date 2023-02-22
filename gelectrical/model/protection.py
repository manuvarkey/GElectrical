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
# from scipy.interpolate import interp1d

# def interpolate(x,y):
#     fit_func = interp1d(np.log10(x), np.log10(y))
#     fit_func_mod = lambda x: list(10**(fit_func(np.log10(np.array(x)))))
#     return fit_func_mod

# local files import
from .. import misc
from ..misc import FieldDict


class ProtectionModel():
    """Generic protection base element"""

    def __init__(self, title, parameters, curve_u, curve_l, element_type='protection'):
        """
            data_struct: Protection datastructure of following format
            
            { 
                'type': 'protection' | 'damage'
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
                                ('thermal', tms, i_n, i1, i2, n),
                                    ... ],
                        'curve_l': ...}
                'graph_model'      : (title, models)}
            }
        """
        self.title = title
        self.data_struct = {'type'          : element_type,
                            'parameters'    : parameters,
                            'data'          : {'curve_u': curve_u,'curve_l': curve_l},
                            'graph_model'   : []}
        # Generated variables
        self.polygon = None
        self.linestring_upper = None
        self.linestring_lower = None
        self.polygon_log = None
        self.linestring_upper_log = None
        self.linestring_lower_log = None

    @classmethod
    def new_from_data(cls, data_struct):
        if data_struct and data_struct['type'] in ('protection', 'damage'):
            if data_struct['graph_model']:
                title = data_struct['graph_model'][0]
            else:
                title = ''
            parameters = copy.deepcopy(data_struct['parameters'])
            curve_u = copy.deepcopy(data_struct['data']['curve_u'])
            curve_l = copy.deepcopy(data_struct['data']['curve_l'])
            element_type = data_struct['type']
            return cls(title, parameters, curve_u, curve_l, element_type)
        else:
            raise ValueError('Wrong data structure passed')

    def copy(self):
        new_obj = self.new_from_data(self.data_struct)
        # Copy generated data
        new_obj.title = self.title
        new_obj.polygon = Polygon(self.polygon)
        new_obj.linestring_upper = LineString(self.linestring_upper)
        new_obj.linestring_lower = LineString(self.linestring_lower)
        new_obj.polygon_log = Polygon(self.polygon_log)
        new_obj.linestring_upper_log = LineString(self.linestring_upper_log)
        new_obj.linestring_lower_log = LineString(self.linestring_lower_log)
        return new_obj

    def get_data_fields(self, modify_code=''):
        fields = dict()
        for key, (caption, unit, value, selection_list) in self.data_struct['parameters'].items():
            fields[modify_code+key] = misc.get_field_dict('float', caption, unit, value, 
                                                            selection_list=selection_list, 
                                                            status_inactivate=False)
        return fields

    def update_graph(self):
        if self.data_struct['type'] == 'protection':
            polygon_pnts = np.array((self.polygon.exterior.coords))
            xval = list(polygon_pnts[:,0])
            yval = list(polygon_pnts[:,1])
            graph_model = [self.title, [{'mode':misc.GRAPH_DATATYPE_POLYGON, 
                                            'title':self.title, 
                                            'xval':xval, 
                                            'yval': yval},]]
            self.data_struct['graph_model'] = graph_model
        elif self.data_struct['type'] == 'damage':
            xval1 = list(self.linestring_upper.xy[0])
            yval1 = list(self.linestring_upper.xy[1])
            xval2 = list(self.linestring_lower.xy[0])
            yval2 = list(self.linestring_lower.xy[1])
            graphs = []
            damage_flag = False
            starting_flag = False

            if xval1 and yval1:
                graphs.append({'mode':misc.GRAPH_DATATYPE_PROFILE, 
                                            'title': self.title + ' - Damage', 
                                            'xval':xval1, 
                                            'yval': yval1})
                damage_flag = True
            else:
                graphs.append({'mode':misc.GRAPH_DATATYPE_PROFILE, 
                                            'title': '', 
                                            'xval':[], 
                                            'yval': []})
            if xval2 and yval2:
                graphs.append({'mode':misc.GRAPH_DATATYPE_PROFILE, 
                                            'title':self.title + ' - Starting', 
                                            'xval':xval2, 
                                            'yval': yval2})
                starting_flag = True
            else:
                graphs.append({'mode':misc.GRAPH_DATATYPE_PROFILE, 
                                            'title': '', 
                                            'xval':[], 
                                            'yval': []})

            if damage_flag and not starting_flag:
                title = self.title + ' - Damage curve'
            elif starting_flag and not damage_flag:
                title = self.title + ' - Starting curve'
            else:
                title = self.title

            graph_model = [title, graphs]
            self.data_struct['graph_model'] = graph_model
            

    def update_parameters(self, parameters):
        for key, field in parameters.items():
            if key in self.data_struct['parameters']:
                self.data_struct['parameters'][key][2] = field[2]

    def evaluate_curves(self, fields, data_fields=None, scale=1):
        
        # Variables for evaluation
        f = FieldDict(fields)
        if data_fields:
            d = FieldDict(data_fields)
        else:
            d = FieldDict(self.get_data_fields())
        
        # Functions for curve evaluation
        def point(i1, t1):
            return (i1,), (t1,)

        def iec(tms, i_n, k, c, alpha, i1, i2, t_min, n):
            if i2 > i1:
                i_array = np.geomspace(i1,i2,num=n)
                t_array_1 = tms*(k/((i_array/i_n)**alpha - 1) + c)
                t_array_2 = np.ones(i_array.shape)*t_min
                t_array = np.maximum(t_array_1, t_array_2)
                return list(i_array), list(t_array)
            else:
                return [], []

        def thermal(tms, i_n, i1, i2, n):
            # As per IEC 60255-8
            i_array = np.geomspace(i1,i2,num=n)
            t_array = tms*np.log(i_array**2/(i_array**2 - i_n**2))
            return list(i_array), list(t_array)

        def i2t(tms, i_n, k, alpha, i1, i2, t_min, n):
            if i2 > i1:
                i_array = np.geomspace(i1,i2,num=n)
                t_array_1 = tms*(k/((i_array/i_n)**alpha))
                t_array_2 = np.ones(i_array.shape)*t_min
                t_array = np.maximum(t_array_1, t_array_2)
                return list(i_array), list(t_array)
            else:
                return [], []

        iec_inverse = lambda tms, i_n, i1, i2, t_min, n: iec(tms, i_n, 0.14, 0, 0.02, i1, i2, t_min, n) # As per IEC 60255-3
        iec_v_inverse = lambda tms, i_n, i1, i2, t_min, n: iec(tms, i_n, 13.5, 0, 1, i1, i2, t_min, n) # As per IEC 60255-3
        iec_e_inverse = lambda tms, i_n, i1, i2, t_min, n: iec(tms, i_n, 80, 0, 2, i1, i2, t_min, n) # As per IEC 60255-3
        ieee_m_inverse = lambda tms, i_n, i1, i2, t_min, n: iec(tms, i_n, 0.0515, 0.1140, 0.02, i1, i2, t_min, n)
        ieee_v_inverse = lambda tms, i_n, i1, i2, t_min, n: iec(tms, i_n, 19.61, 0.491, 2, i1, i2, t_min, n)
        ieee_e_inverse = lambda tms, i_n, i1, i2, t_min, n: iec(tms, i_n, 28.2, 0.1217, 2, i1, i2, t_min, n)
        
        def eval_curve(curve):
            var_dict = {'f': f, 'd': d}
            func_dict = {   'point'         : point,
                            'iec'           : iec,
                            'iec_inverse'   : iec_inverse,
                            'iec_v_inverse' : iec_v_inverse,
                            'iec_e_inverse' : iec_e_inverse,
                            'ieee_m_inverse': ieee_m_inverse,
                            'ieee_v_inverse': ieee_v_inverse,
                            'ieee_e_inverse': ieee_e_inverse,
                            'thermal'       : thermal,
                            'i2t'           : i2t
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
            curve = (np.array([curve_i, curve_t]).T)*[scale, 1]
            return curve

        # Evaluate curves
        curve_upper = eval_curve(self.data_struct['data']['curve_u'])
        curve_lower = eval_curve(self.data_struct['data']['curve_l'])

        # Geometry elements
        if curve_upper is not None:
            # self.linestring_upper = LineString(misc.log_interpolate_piecewise(self.curve_upper))
            self.linestring_upper = LineString(curve_upper)
            self.linestring_upper_log = LineString(np.log10(curve_upper))
        else:
            self.linestring_upper = None
            self.linestring_upper_log = None

        if curve_lower is not None:
            # self.linestring_lower = LineString(misc.log_interpolate_piecewise(self.curve_lower))
            self.linestring_lower = LineString(curve_lower)
            self.linestring_lower_log = LineString(np.log10(curve_lower))
        else:
            self.linestring_lower = None
            self.linestring_lower_log = None
            
        if self.linestring_upper and self.linestring_lower:
            self.polygon = Polygon(list(reversed(self.linestring_upper.coords)) + list(self.linestring_lower.coords))
            self.polygon_log = Polygon(list(reversed(self.linestring_upper_log.coords)) + list(self.linestring_lower_log.coords))
        else:
            self.polygon = None
            self.polygon_log = None

    def get_graph_model(self):
        return copy.deepcopy(self.data_struct['graph_model'])

    def get_evaluated(self, fields, data_fields=None, scale=1):
        obj = self.copy()
        obj.evaluate_curves(fields, data_fields, scale)  # Evaluate curves
        obj.update_graph()  # Update graph
        return obj

    def get_evaluated_model(self, fields, data_fields=None):
        self.evaluate_curves(fields, data_fields)  # Evaluate curves
        self.update_graph()  # Update graph
        return copy.deepcopy(self.data_struct)

    def get_current(self, t, mode='protection'):
        values = tuple()
        if mode == 'protection' and self.polygon:
            if t > self.polygon.bounds[3]:
                values = (min(self.linestring_lower.xy[0]), min(self.linestring_upper.xy[0]))
            elif t < self.polygon.bounds[1]:
                values = (max(self.linestring_lower.xy[0]), max(self.linestring_upper.xy[0]))
            else:
                hor_line = LineString(np.log10([[self.polygon.bounds[0]-0.0001, t],
                                                [self.polygon.bounds[2]+0.0001, t]]))
                bounds = self.polygon_log.intersection(hor_line).bounds
                values = (10**bounds[0], 10**bounds[2])
        elif mode == 'damage' and self.linestring_upper:
            if t > self.linestring_upper.bounds[3] or t < self.linestring_upper.bounds[1]:
                values = tuple()
            else:
                hor_line = LineString(np.log10([[self.linestring_upper.bounds[0]-0.0001, t],
                                                [self.linestring_upper.bounds[2]+0.0001, t]]))
                bounds = (self.linestring_upper_log.intersection(hor_line)).bounds
                values = (10**bounds[0], 10**bounds[2])
        elif mode == 'starting' and self.linestring_lower:
            if t > self.linestring_lower.bounds[3] or t < self.linestring_lower.bounds[1]:
                values = tuple()
            else:
                hor_line = LineString(np.log10([[self.linestring_lower.bounds[0]-0.0001, t],
                                                [self.linestring_lower.bounds[2]+0.0001, t]]))
                bounds = (self.linestring_lower_log.intersection(hor_line)).bounds
                values = (10**bounds[0], 10**bounds[2])
        else:
            values = tuple()
        return tuple(sorted(set(values)))

    def get_time(self, I, mode='protection'):
        values = tuple()
        if mode == 'protection' and self.polygon:
            if I > self.polygon.bounds[2] or I < self.polygon.bounds[0]:
                values = tuple()
            else:
                vert_line = LineString(np.log10([[I, self.polygon.bounds[1]-0.0001],
                                                 [I, self.polygon.bounds[3]+0.0001]]))
                bounds = self.polygon_log.intersection(vert_line).bounds
                values = (10**bounds[1], 10**bounds[3])
        elif mode == 'damage' and self.linestring_upper:
            if I > self.linestring_upper.bounds[2] or I < self.linestring_upper.bounds[0]:
                values = tuple()
            else:
                vert_line = LineString(np.log10([[I, self.linestring_upper.bounds[1]-0.0001],
                                                 [I, self.linestring_upper.bounds[3]+0.0001]]))
                bounds = (self.linestring_upper_log.intersection(vert_line)).bounds
                values = (10**bounds[1], 10**bounds[3])
        elif mode == 'starting' and self.linestring_lower:
            if I > self.linestring_lower.bounds[2] or I < self.linestring_lower.bounds[0]:
                values = tuple()
            else:
                vert_line = LineString(np.log10([[I, self.linestring_lower.bounds[1]-0.0001],
                                                 [I, self.linestring_lower.bounds[3]+0.0001]]))
                bounds = (self.linestring_lower_log.intersection(vert_line)).bounds
                values = (10**bounds[1], 10**bounds[3])
        else:
            values = tuple()
        return tuple(sorted(set(values)))
    
    def contains(self, geometry, curve='upper', direction='right', i_max=None, scale=1):
        """
        Check if geometry lies completely to the given direction of selected curve
        """
        lim_min = -6
        lim_max = 6
        
        if curve == 'upper':
            linestring = self.linestring_upper_log
        elif curve == 'lower':
            linestring = self.linestring_lower_log

        # Scale data
        ls_x = np.array(linestring.xy[0])
        ls_y = np.array(linestring.xy[1])
        linestring = LineString((np.vstack((ls_x + np.log10(scale), ls_y))).T)

        if linestring and geometry:
            i0 = linestring.xy[0][0]
            t0 = linestring.xy[1][0]
            i1 = linestring.xy[0][-1]
            t1 = linestring.xy[1][-1]
            if direction == 'right':
                check_geom = Polygon(list(linestring.coords) + 
                                        [(i1, lim_max), (i0, lim_max)])
                if i_max:
                    lim_i_max = min(np.log10(i_max), i1)
                else:
                    lim_i_max = i1
                geom_mask = Polygon([   (lim_min, lim_max), 
                                        (lim_i_max, lim_max), 
                                        (lim_i_max, lim_min), 
                                        (lim_min, lim_min),
                                        (lim_min, lim_max)  ])
                geometry_masked = geometry.intersection(geom_mask)
            elif direction == 'left':
                check_geom = Polygon(list(linestring.coords) + 
                                        [(i1, lim_min), 
                                         (lim_min, lim_min), 
                                         (lim_min, lim_max), 
                                         (i0, lim_max)])
                geometry_masked = geometry
            return check_geom.contains(geometry_masked)
        
    



        
        

