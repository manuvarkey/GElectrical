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

import copy, logging
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

# Get logger object
log = logging.getLogger(__name__)

# Module constants
PROT_LOWER = -1
PROT_UPPER = 1

class ProtectionModel():
    """Generic protection base element"""

    def __init__(self, title, parameters, curves, element_type='protection'):
        """
            data_struct: Protection datastructure of following format
            
            { 
                'type': 'protection' | 'damage'
                'parameters': { 'var_1': [caption, unit, value, value_list], 
                                'var_2': [caption, unit, value, value_list] ... },
                'data': {{'select_expr_list' : ['selection_criterion_1', 'selection_criterion_1', 'selection_criterion_1'] 
                          'curve_u1': [('point', i1, t1), 
                                        ('POINTS', tms, i_n, i1, i2, t_min, d_i, d_t), 
                                        ('IEC', tms, i_n, i1, i2, t_min, n, k, c, alpha), 
                                        ('IEC_S_INV_3.0', tms, i_n, t_min, i1, i2, n), 
                                        ('IEC_S_INV_1.3', tms, i_n, t_min, i1, i2, n), 
                                        ('IEC_V_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('IEC_E_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('IEC_LT_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('IEEE_M_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('IEEE_V_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('IEEE_E_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('US_CO8_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('US_CO2_INV', tms, i_n, t_min, i1, i2, n), 
                                        ('THERMAL', tms, i_n, t_min, i1, i2, n), 
                                        ('I2T', tms, i_n, t_min, i1, i2, n, k, alpha), 
                                        ('POLYLOG', tms, i_n, t_min, i1, i2, n, [k0, k1, k2, k3, k4], c), 
                                            ... ],
                                        'curve_l1': ...,
                        'selection_criterion_2' :  ...
                        }}
                        OR
                'data': {'curve_u': [('point', i1, t1), 
                                    ('POINTS', tms, i_n, i1, i2, t_min, d_i, d_t), 
                                    ('IEC', tms, i_n, i1, i2, t_min, n, k, c, alpha), 
                                    ('IEC_S_INV_3.0', tms, i_n, t_min, i1, i2, n), 
                                    ('IEC_S_INV_1.3', tms, i_n, t_min, i1, i2, n), 
                                    ('IEC_V_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('IEC_E_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('IEC_LT_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('IEEE_M_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('IEEE_V_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('IEEE_E_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('US_CO8_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('US_CO2_INV', tms, i_n, t_min, i1, i2, n), 
                                    ('THERMAL', tms, i_n, t_min, i1, i2, n), 
                                    ('I2T', tms, i_n, t_min, i1, i2, n, k, c, alpha),
                                    ('POLYLOG', tms, i_n, t_min, i1, i2, n, [k0, k1, k2, k3, k4], c),  
                                                                ... ],
                         'curve_l': ...,
                        }
                'graph_model'      : (title, models)}
            }
        """
        self.title = title
        self.data_struct = {'type'          : element_type,
                            'parameters'    : parameters,
                            'data'          : curves,
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
            curves = copy.deepcopy(data_struct['data'])
            element_type = data_struct['type']
            return cls(title, parameters, curves, element_type)
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
        fields = misc.get_fields_from_params(self.data_struct['parameters'], modify_code)
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
        misc.update_params_from_params(self.data_struct['parameters'], parameters)

    def update_parameters_from_fields(self, fields):
        misc.update_params_from_fields(self.data_struct['parameters'], fields)

    def evaluate_curves(self, fields, data_fields=None, scale=1):
        
        # Variables for evaluation
        f = FieldDict(fields)
        if data_fields:
            d = FieldDict(data_fields)
        else:
            d = FieldDict(self.get_data_fields())
        
        # Functions for curve evaluation
        def point(i1, t1, **vars):
            return (i1,), (t1,)

        def mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type=None, pole_compensation=True):
            """Applies minimum time and tolerance values to curve"""
            if i2 > i1 and not(curve_type == PROT_LOWER and (abs(i_tol) > 100 or abs(t_tol) > 100)):
                k_i = round(1+i_tol/100,4)
                k_t = round(1+t_tol/100,4)
                i_array = np.geomspace(i1,i2,num=n)
                t_array_1 = np.zeros(i_array.shape)
                if curve_type is None or (i_tol == 0 and t_tol == 0 and t_tol_f == 0):
                    t_array_1 = curve_func(tms, i_n, i_array)
                else:
                    i_array_t = np.copy(i_array)
                    i_array_i = np.copy(i_array)
                    if pole_compensation:
                        i_array_t[i_array <= i_n] = i_n*1.001
                        i_array_i[i_array <= i_n*k_i] = i_n*k_i*1.001
                    t_array_1_t_perc = curve_func(k_t*tms, i_n, i_array_t)
                    t_array_1_t_fixed = curve_func(tms, i_n, i_array_t) + t_tol_f
                    t_array_1_i = curve_func(tms, k_i*i_n, i_array_i)
                    if curve_type == PROT_UPPER:
                        t_array_1 = np.max([t_array_1_t_perc, t_array_1_t_fixed, t_array_1_i, np.ones(t_array_1_i.shape)*0.00001], axis=0)
                    elif curve_type == PROT_LOWER:
                        t_array_1 = np.min([t_array_1_t_perc, t_array_1_t_fixed, t_array_1_i], axis=0)
                        t_array_1 = np.maximum(t_array_1, np.ones(t_array_1_i.shape)*0.00001)
                t_array_2 = np.ones(i_array.shape)*t_min
                t_array = np.maximum(t_array_1, t_array_2)
                return list(i_array), list(t_array)
            else:
                return [], []
    
        def iec(tms, i_n, i1, i2, t_min, n, k_iec=0.14, c_iec=0, alpha_iec=0.02, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            k = k_iec
            c = c_iec
            alpha = alpha_iec
            def curve_func(tms, i_n, i_array):
                return tms*(k/((i_array/(i_n))**alpha - 1) + c)
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type)
    
        def thermal(tms, i_n, i1, i2, t_min, n, i_p_thermal=0, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            i_p = i_p_thermal
            # As per IEC 60255-8
            def curve_func(tms, i_n, i_array):
                return tms*np.log((i_array**2-i_p**2)/(i_array**2 - i_n**2))
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type)

        def i2t(tms, i_n, i1, i2, t_min, n, k_i2t=1, alpha_i2t=2, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            k = k_i2t
            alpha = alpha_i2t
            def curve_func(tms, i_n, i_array):
                return tms*(k/((i_array/i_n)**alpha))
            # Note: do not consider i_tol since curve is unaffected by current pickup value
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, 0, t_tol, t_tol_f, curve_type, pole_compensation=False)
            
        def ri_inverse(tms, i_n, i1, i2, t_min, n, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            # As per P114S/EN OP/B11 catalogue
            def curve_func(tms, i_n, i_array):
                return tms*1/(0.339-0.236/(i_array/i_n))
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type)
            
        def hv_fuse(tms, i_n, i1, i2, t_min, n, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            # As per P114S/EN OP/B11 catalogue
            def curve_func(tms, i_n, i_array):
                return (tms/0.1)*10**(np.log10(2*(i_array/i_n))*(-3.832)+3.66)
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type)
        
        def fr_fuse(tms, i_n, i1, i2, t_min, n, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            # As per P114S/EN OP/B11 catalogue
            def curve_func(tms, i_n, i_array):
                t_array_1 = np.where(i_array < 2*i_n, (tms/0.1)*10**(np.log10(i_array/i_n)*(-7.16)+3.0), 0)
                t_array_2 = np.where((i_array >= 2*i_n) & (i_array <= 2.66*i_n), (tms/0.1)*10**(np.log10(i_array/i_n)*(-5.4)+2.47), 0)
                t_array_3 = np.where(i_array > 2.66*i_n, (tms/0.1)*10**(np.log10(i_array/i_n)*(-4.24)+1.98), 0)
                return t_array_1 + t_array_2 + t_array_3
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type)
            
        def polylog(tms, i_n, i1, i2, t_min, n, kn_polylog=[1,1], c_polylog=1, i_tol=0, t_tol=0, t_tol_f=0, curve_type=None, **vars):
            # Equation of the form log10 T = k0 + k1*log10(M-C) + k2*log10(M-C)**2 + ...
            kn = kn_polylog
            C = c_polylog
            def curve_func(tms, i_n, i_array):
                t_array_1 = np.zeros_like(i_array)
                M = i_array/i_n
                for order, k in enumerate(kn):
                    t_array_1 += k*np.log10(M-C)**order
                return tms*10**t_array_1
            return mod_curve(curve_func, tms, i_n, i1, i2, t_min, n, i_tol, t_tol, t_tol_f, curve_type)
            
        def points(tms, i_n, i1, i2, t_min, d_i_points=[], d_t_points=[], **vars):
            d_i = np.array(d_i_points)*i_n
            d_t = np.array(d_t_points)*tms
            if i2 > i1:
                include_arg = (d_i >= i1) & (d_i <= i2)
                i_array = d_i[include_arg]
                t_array_1 = d_t[include_arg]
                t_array_2 = np.ones(i_array.shape)*t_min
                t_array = np.maximum(t_array_1, t_array_2)
                return list(i_array), list(t_array)
            else:
                return [], []
            
        def clean_iec(vars):
            vars.pop('k_iec', None)
            vars.pop('alpha_iec', None)
            vars.pop('c_iec', None)
            return vars

        iec_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms, i_n, i1, i2, t_min, n, 0.14, 0, 0.02, **clean_iec(vars)) # As per IEC 60255-3
        iec_inverse_1_3 = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms, i_n, i1, i2, t_min, n, 0.06, 0, 0.02, **clean_iec(vars))
        iec_v_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms, i_n, i1, i2, t_min, n, 13.5, 0, 1, **clean_iec(vars)) # As per IEC 60255-3
        iec_e_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms, i_n, i1, i2, t_min, n, 80, 0, 2, **clean_iec(vars)) # As per IEC 60255-3
        iec_lt_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms, i_n, i1, i2, t_min, n, 120, 0, 1, **clean_iec(vars)) # As per IEC 60255-3
        ieee_m_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms/7, i_n, i1, i2, t_min, n, 0.0515, 0.1140, 0.02, **clean_iec(vars)) # As per IEEE C37.112-1996
        ieee_v_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms/7, i_n, i1, i2, t_min, n, 19.61, 0.491, 2, **clean_iec(vars)) # As per IEEE C37.112-1996
        ieee_e_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms/7, i_n, i1, i2, t_min, n, 28.2, 0.1217, 2, **clean_iec(vars)) # As per IEEE C37.112-1996
        us_co8_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms/7, i_n, i1, i2, t_min, n, 5.95, 0.18, 2, **clean_iec(vars))
        us_co2_inverse = lambda tms, i_n, i1, i2, t_min, n, **vars: iec(tms/7, i_n, i1, i2, t_min, n, 0.02394, 0.01694, 0.02, **clean_iec(vars))
        
        def eval_curve(curve):
            var_dict = {'f': f, 'd': d}
            func_dict = {   'point'         : point,
                            'POINT'         : point,
                            'POINTS'        : points,
                            'IEC'           : iec,
                            'IEC_S_INV_3.0' : iec_inverse,
                            'IEC_S_INV_1.3' : iec_inverse_1_3,
                            'IEC_V_INV'     : iec_v_inverse,
                            'IEC_E_INV'     : iec_e_inverse,
                            'IEC_LT_INV'    : iec_lt_inverse,
                            'IEEE_M_INV'    : ieee_m_inverse,
                            'IEEE_V_INV'    : ieee_v_inverse,
                            'IEEE_E_INV'    : ieee_e_inverse,
                            'US_CO8_INV'    : us_co8_inverse,
                            'US_CO2_INV'    : us_co2_inverse,
                            'THERMAL'       : thermal,
                            'I2T'           : i2t,
                            'RI_INV'        : ri_inverse,
                            'HV_FUSE'       : hv_fuse,
                            'FR_FUSE'       : fr_fuse,
                            'POLYLOG'       : polylog
                        }
            # Evaluate curve
            curve_i = []
            curve_t = []
            for func_str, *data in curve:
                if func_str in func_dict:
                    func = eval(func_str, func_dict)
                else:
                    func_eval = eval(func_str, var_dict)
                    if func_eval in func_dict:
                        func = func_dict[func_eval]
                    else:
                        func = None
                if func:
                    # Handle case when parameters are passed as var-> value dict
                    if len(data) == 1 and isinstance(data[0], dict):
                        try:
                            data_eval = {key:(x if isinstance(x, (int, float, list, dict)) else eval(x, var_dict)) for key,x in data[0].items()}
                            i_array, t_array = func(**data_eval)
                            curve_i += i_array
                            curve_t += t_array
                        except Exception as e:
                            log.exception('Error evaluating curve - data skipped')
                    # Handle case when parameters are passed as list
                    else:
                        try:
                            data_eval = [x if isinstance(x, (int, float, list, dict)) else eval(x, var_dict) for x in data]
                            i_array, t_array = func(*data_eval)
                            curve_i += i_array
                            curve_t += t_array
                        except Exception as e:
                            log.exception('Error evaluating curve - data skipped')
                    
            curve = (np.array([curve_i, curve_t]).T)*[scale, 1]
            return curve
        
        def eval_criterion(criterion):
            var_dict = {'f': f, 'd': d}
            return eval(criterion, var_dict)

        # Evaluate curves
        curve_upper = []
        curve_lower = []
        if 'select_expr_list' in self.data_struct['data']:
            for slno, criterion in enumerate(self.data_struct['data']['select_expr_list']):
                if eval_criterion(criterion):
                    curve_upper = eval_curve(self.data_struct['data']['curve_u' + str(slno+1)])
                    curve_lower = eval_curve(self.data_struct['data']['curve_l' + str(slno+1)])
                    break
        else:
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
            self.polygon = Polygon()
            self.polygon_log = Polygon()

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
            if I > self.polygon.bounds[2]:
                values = (self.polygon.bounds[1],)
            elif I < self.polygon.bounds[0]:
                values = (1000000,)
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
        

## Get commonly used protection models
        
def get_protection_model(protection_type, ground_model=False):

    curve_u = []
    curve_l = []
    curves = {}
    parameters = dict()

    # Thermal trip constants
    long_trip_curves = ['IEC', 'IEC_S_INV_3.0', 'IEC_S_INV_1.3', 'IEC_V_INV', 'IEC_E_INV', 'IEC_LT_INV', 
                                'IEEE_M_INV', 'IEEE_V_INV', 'IEEE_E_INV', 
                                'US_CO8_INV', 'US_CO2_INV', 
                                'THERMAL', 'I2T', 
                                'RI_INV', 'HV_FUSE', 'FR_FUSE']
    curves_default_values_dict = {curve: {'tr_i2t': None, 'ir_i2t': None, 'k_iec': None, 'c_iec': None, 'alpha_iec': None} for curve in long_trip_curves}
    curves_default_values_dict['I2T'] = {'tr_i2t': 16, 'ir_i2t': 6, 'k_iec': None, 'c_iec': None, 'alpha_iec': None}
    curves_default_values_dict['IEC'] = {'tr_i2t': None, 'ir_i2t': None, 'k_iec': 800, 'c_iec': 0, 'alpha_iec':2}
    # Magnetic trip constants
    i2t_default_values_dict = { True   : {'t_i2t': 0.1, 'i_i2t': 10, 'tol_m_i2t_p': 20,'tol_m_i2t_m': 20}, 
                                False   : {'t_i2t': None, 'i_i2t': None, 'tol_m_i2t_p': None,'tol_m_i2t_m': None}}
    # Instantaneous trip constants
    ii_default_values_dict = {  True    : {'i_i': 15, 't_i_p': 0.02, 't_i_m': 0.001, 'tol_ii_p': 20, 'tol_ii_m': 20}, 
                                False   : {'i_i': None, 't_i_p': None, 't_i_m': None, 'tol_ii_p': None, 'tol_ii_m': None}}
    if ground_model is True:
        In = 'f.I0'
        xIn = 'xI0'
    else:
        In = 'f.In'
        xIn = 'xIn'
    Isc = '1000*f.Isc'
        
    if protection_type in ('Thermal',):

        def get_curves(Ir, Tr, i_tol, t_tol, t_tol_f, t_min, I1, curve_type):
            T_conv = 1e5
            kr_I2t = '((d.ir_i2t)**2)*d.tr_i2t'
            k_iec = 'd.k_iec'
            c_iec = 'd.c_iec'
            alpha_iec = 'd.alpha_iec'
            I1_ = I1 + " if d.curve_l == 'I2T' else " + I1 + "*1.01"
            curve_vars = {  'tms'         : Tr, 
                            'i_n'         : Ir, 
                            'i1'          : I1_,
                            'i2'          : Isc,
                            't_min'       : t_min, 
                            'n'           : 100,
                            'i_tol'       : i_tol,
                            't_tol'       : t_tol,
                            't_tol_f'     : t_tol_f,
                            'curve_type'  : curve_type,

                            'k_i2t'       : kr_I2t,
                            'k_iec'       : k_iec,
                            'c_iec'       : c_iec,
                            'alpha_iec'   : alpha_iec,
                            }
            curve = [   ('point', I1, T_conv),
                        ('d.curve_l', curve_vars)]
            return curve
        
        # Upper curve
        Ir = 'd.i_r*' + In
        Tr = 'd.t_r'
        i_tol = 'd.tol_ir_p'
        t_tol = 'd.tol_tr_p'
        t_tol_f = 'd.tol_trf_p'
        t_min = 'd.t_min'
        I1 = '(100+d.tol_ir_p)/100*' + Ir
        curve_type = PROT_UPPER
        curve_u = get_curves(Ir, Tr, i_tol, t_tol, t_tol_f, t_min, I1, curve_type)
        # Lower curve
        Ir = 'd.i_r*' + In
        Tr = 'd.t_r'
        i_tol = '-d.tol_ir_m'
        t_tol = '-d.tol_tr_m'
        t_tol_f = '-d.tol_trf_m'
        t_min = 0
        I1 = '(100-d.tol_ir_m)/100*' + Ir
        curve_type = PROT_LOWER
        curve_l = get_curves(Ir, Tr, i_tol, t_tol, t_tol_f, t_min, I1, curve_type)
        
        parameters = {'head_t'  : ['Thermal protection', '', '', None, '', 'heading'],
                    'curve_l'   : ['Thermal trip curve', '', 'IEC_S_INV_3.0', long_trip_curves, '', 'str', True, curves_default_values_dict],
                    'i_r'       : ['Ir', xIn, 1, None, 'Thermal protection pickup current'],
                    't_r'       : ['Tr', '', 1, None, 'Time multiplier setting'],
                    'k_iec'     : ['k', '', 800, None, '', 'float', False],
                    'c_iec'     : ['c', '', 0, None, '', 'float', False],
                    'alpha_iec' : ['alpha', '', 2, None, '', 'float', False],
                    'ir_i2t'    : ['Ir i2t', 'xIr', 6, None, '', 'float', False],
                    'tr_i2t'    : ['Tr i2t', 's', 16, None, 'Operation time @ Ir i2t', 'float', False],
                    't_min'     : ['Tmin', 's', 0.1, None, 'Minimum trip time'],
                    'tol_ir_p'  : ['Ir tol (+)', '%', 10, None, 'Current pickup tolerance (+)', [1,0,None]],
                    'tol_ir_m'  : ['Ir tol (-)', '%', 10, None, 'Current pickup tolerance (-)', [1,0,99]],
                    'tol_tr_p'  : ['Tr tol (+)', '%', 10, None, 'Time delay tolerance (+)', [1,0,None]],
                    'tol_tr_m'  : ['Tr tol (-)', '%', 10, None, 'Time delay tolerance (-)', [1,0,99]],
                    'tol_trf_p' : ['Tr tol fixed (+)', 's', 0, None, 'Time delay tolerance fixed (+)', [3,0,None]],
                    'tol_trf_m' : ['Tr tol fixed (-)', 's', 0, None, 'Time delay tolerance fixed (-)', [3,0,None]]}
        curves = {'curve_u': curve_u, 'curve_l': curve_l}

    elif protection_type in ('Magnetic'):
        select_expr_list = ['d.i_i_on is False and d.i2t_on is False',
                            'd.i_i_on is True and d.i2t_on is False',
                            'd.i_i_on is False and d.i2t_on is True',
                            'd.i_i_on is True and d.i2t_on is True']
        
        def get_curves(Im, Tm, Ii, Ti, i2t_tol):
            T_conv = 1e5
            k_I2T = '((d.i_i2t)**2)*d.t_i2t'
            # M
            curve1 = [('point', Im, T_conv),
                        ('point', Im, Tm),
                        ('point', Isc, Tm),]
            # M, I
            curve2 = [('point', Im, T_conv),
                        ('point', Im, Tm),
                        ('point', Ii, Tm),
                        ('point', Ii, Ti),
                        ('point', Isc, Ti),]
            # M, I2t
            curve3 = [('point', Im, T_conv),
                        ('I2T', i2t_tol, In, Im, Isc, Tm, 50, k_I2T, 2),
                        ('point', Isc, Tm),]
            # M, I, I2t
            curve4 = [('point', Im, T_conv),
                        ('I2T', i2t_tol, In, Im, Ii, Tm, 50, k_I2T, 2),
                        ('point', Ii, Tm),
                        ('point', Ii, Ti),
                        ('point', Isc, Ti),]
            return curve1, curve2, curve3, curve4

        # Upper curves
        Im = '(d.i_m*(100+d.tol_im_p)/100)*' + In
        Tm = 'max(d.t_m*(100+d.tol_tm_p)/100, d.t_m+d.tol_tmf_p)'
        Ii = '(d.i_i*(100+d.tol_ii_p)/100)*' + In
        Ti = 'd.t_i_p'
        i2t_tol = '(100+d.tol_m_i2t_p)/100'
        curve_u1, curve_u2, curve_u3, curve_u4 = get_curves(Im, Tm, Ii, Ti, i2t_tol)
        # Lower curves
        Im = '(d.i_m*(100-d.tol_im_m)/100)*' + In
        Tm = 'max(0.00001, min(d.t_m*(100-d.tol_tm_m)/100, d.t_m-d.tol_tmf_m))'
        Ii = '(d.i_i*(100-d.tol_ii_m)/100)*' + In
        Ti = 'd.t_i_m'
        i2t_tol = '(100-d.tol_m_i2t_m)/100'
        curve_l1, curve_l2, curve_l3, curve_l4 = get_curves(Im, Tm, Ii, Ti, i2t_tol)

        parameters = {  'head_m'        : ['Magnetic protection', '', '', None, '', 'heading'],
                        'i_m'           : ['Im', xIn, 10, None, 'Magnetic pickup current'],
                        't_m'           : ['Tm', 's', 0.1, None, 'Magnetic trip time delay'],
                        'tol_im_p'      : ['Im tol (+)', '%', 10, None, 'Current pickup tolerance (+)', [1,0,None]],
                        'tol_im_m'      : ['Im tol (-)', '%', 10, None, 'Current pickup tolerance (-)', [1,0,99]],
                        'tol_tm_p'      : ['Tm tol (+)', '%', 20, None, 'Time delay tolerance % (+)', [1,0,None]],
                        'tol_tm_m'      : ['Tm tol (-)', '%', 20, None, 'Time delay tolerance % (-)', [1,0,99]],
                        'tol_tmf_p'     : ['Tm tol fixed (+)', 's', 0, None, 'Time delay tolerance fixed (+)', [3,0,None]],
                        'tol_tmf_m'     : ['Tm tol fixed (-)', 's', 0, None, 'Time delay tolerance fixed (-)', [3,0,None]],
                        
                        'head_i2t'      : ['I2t protection', '', '', None, '', 'heading'],
                        'i2t_on'        : ['Enable I2t protection', '', False, [True, False], '', 'bool', True, i2t_default_values_dict],
                        'i_i2t'         : ['I i2t', xIn, 10, None, '', 'float', False],
                        't_i2t'         : ['T i2t', 's', 0.1, None, 'Operation time @ I i2t', 'float', False],
                        'tol_m_i2t_p'  : ['Tm (I2t) tol (+)', '%', 20, None, 'Time delay tolerance (+)', [1,0,None], False],
                        'tol_m_i2t_m'  : ['Tm (I2t) tol (-)', '%', 20, None, 'Time delay tolerance (-)', [1,0,99], False],
                        
                        'head_i'        : ['Instantaneous protection', '', '', None, '', 'heading'],
                        'i_i_on'        : ['Enable instantaneous protection', '', False, [True, False], '', 'bool', True, ii_default_values_dict],
                        'i_i'           : ['Ii', xIn, 15, None, 'Instantaneous pickup current', 'float', False],
                        't_i_p'         : ['Ti (max)', 's', 0.02, None, 'Instantaneous trip time delay (max)', 'float', False],
                        't_i_m'         : ['Ti (min)', 's', 0.001, None, 'Instantaneous trip time delay (min)', 'float', False],
                        'tol_ii_p'      : ['Ii tol (+)', '%', 20, None, 'Current pickup tolerance (+)', [1,0,None], False],
                        'tol_ii_m'      : ['Ii tol (-)', '%', 20, None, 'Current pickup tolerance (-)', [1,0,99], False]}
        curves = {'select_expr_list': select_expr_list,
                    'curve_u1': curve_u1, 'curve_l1': curve_l1,
                    'curve_u2': curve_u2, 'curve_l2': curve_l2,
                    'curve_u3': curve_u3, 'curve_l3': curve_l3,
                    'curve_u4': curve_u4, 'curve_l4': curve_l4,}

    elif protection_type in ('Thermal Magnetic',):

        def get_curves(Ir, I1, Tr, T_conv, Im, Tm, i_tol, t_tol, t_tol_f, curve_type):
            kr_I2t = '((d.ir_i2t)**2)*d.tr_i2t'
            k_iec = 'd.k_iec'
            c_iec = 'd.c_iec'
            alpha_iec = 'd.alpha_iec'
            I1_ = I1 + " if d.curve_l == 'I2T' else " + I1 + "*1.01"
            curve_vars = {  'tms'         : Tr, 
                            'i_n'         : Ir, 
                            'i1'          : I1_,
                            'i2'          : Im,
                            't_min'       : Tm, 
                            'n'           : 100,
                            'i_tol'       : i_tol,
                            't_tol'       : t_tol,
                            't_tol_f'     : t_tol_f,
                            'curve_type'  : curve_type,

                            'k_i2t'       : kr_I2t,
                            'k_iec'       : k_iec,
                            'c_iec'       : c_iec,
                            'alpha_iec'   : alpha_iec,
                            }
            curve = [   ('point', I1, T_conv),
                        ('d.curve_l', curve_vars),
                        ('point', Im, Tm),
                        ('point', Isc, Tm),]
            return curve
        
        # Upper curve
        Ir = 'd.i_r*' + In
        I1 = 'd.i_f*d.i_r*' + In
        Tr = 'd.t_r'
        T_conv = 1e5
        Im = '(d.i_m*(100+d.tol_im_p)/100)*' + In
        Tm = 'max(d.t_m*(100+d.tol_tm_p)/100, d.t_m+d.tol_tmf_p)'
        i_tol = 'd.i_f*100-100'
        t_tol = 'd.tol_tr_p'
        t_tol_f = 'd.tol_trf_p'
        curve_type = PROT_UPPER
        curve_u = get_curves(Ir, I1, Tr, T_conv, Im, Tm, i_tol, t_tol, t_tol_f, curve_type)
        # Lower curve
        Ir = 'd.i_r*' + In
        I1 = 'd.i_nf*d.i_r*' + In
        Tr = 'd.t_r'
        T_conv = 1e5
        Im = '(d.i_m*(100-d.tol_im_m)/100)*' + In
        Tm = 'max(0.00001, min(d.t_m*(100-d.tol_tm_m)/100, d.t_m-d.tol_tmf_m))'
        i_tol = 'd.i_nf*100-100'
        t_tol = '-d.tol_tr_m'
        t_tol_f = '-d.tol_trf_m'
        curve_type = PROT_LOWER
        curve_l = get_curves(Ir, I1, Tr, T_conv, Im, Tm, i_tol, t_tol, t_tol_f, curve_type)
        
        parameters = {'head_t'  : ['Thermal protection', '', '', None, '', 'heading'],
                    'curve_l'   : ['Thermal trip curve', '', 'IEC', long_trip_curves, '', 'str', True, curves_default_values_dict],
                    'i_r'       : ['Ir', xIn, 1, None, 'Thermal protection pickup current'],
                    'i_nf'      : ['Inf', 'xIr', 1.05, None, 'Conventional non-tripping current'],
                    'i_f'       : ['If', 'xIr', 1.3, None, 'Conventional tripping current'],
                    't_r'       : ['Tr', '', 1, None, 'Time multiplier setting'],
                    'k_iec'     : ['k', '', 800, None, '', 'float', True],
                    'c_iec'     : ['c', '', 0, None, '', 'float', True],
                    'alpha_iec' : ['alpha', '', 2, None, '', 'float', True],
                    'ir_i2t'    : ['Ir i2t', 'xIr', 6, None, '', 'float', False],
                    'tr_i2t'    : ['Tr i2t', 's', 16, None, 'Operation time @ Ir i2t', 'float', False],
                    'tol_tr_p'  : ['Tr tol (+)', '%', 50, None, 'Time delay tolerance (+)', [1,0,None]],
                    'tol_tr_m'  : ['Tr tol (-)', '%', 50, None, 'Time delay tolerance (-)', [1,0,99]],
                    'tol_trf_p' : ['Tr tol fixed (+)', 's', 0, None, 'Time delay tolerance fixed (+)', [3,0,None]],
                    'tol_trf_m' : ['Tr tol fixed (-)', 's', 0, None, 'Time delay tolerance fixed (-)', [3,0,None]],
                    
                    'head_m'        : ['Magnetic protection', '', '', None, '', 'heading'],
                    'i_m'           : ['Im', xIn, 10, None, 'Magnetic pickup current'],
                    't_m'           : ['Tm', 's', 0.02, None, 'Magnetic trip time delay'],
                    'tol_im_p'      : ['Im tol (+)', '%', 20, None, 'Current pickup tolerance (+)', [1,0,None]],
                    'tol_im_m'      : ['Im tol (-)', '%', 20, None, 'Current pickup tolerance (-)', [1,0,99]],
                    'tol_tm_p'      : ['Tm tol (+)', '%', 0, None, 'Time delay tolerance % (+)', [1,0,None]],
                    'tol_tm_m'      : ['Tm tol (-)', '%', 0, None, 'Time delay tolerance % (-)', [1,0,99]],
                    'tol_tmf_p'     : ['Tm tol fixed (+)', 's', 0, None, 'Time delay tolerance fixed (+)', [3,0,None]],
                    'tol_tmf_m'     : ['Tm tol fixed (-)', 's', 0.019, None, 'Time delay tolerance fixed (-)', [3,0,None]],}
        curves = {'curve_u': curve_u, 'curve_l': curve_l}

    elif protection_type in ('Microprocessor',):
        select_expr_list = ['d.i_i_on is False and d.i2t_on is False',
                            'd.i_i_on is True and d.i2t_on is False',
                            'd.i_i_on is False and d.i2t_on is True',
                            'd.i_i_on is True and d.i2t_on is True']
        
        def get_curves(Ir, I1, Tr, T_conv, Im, Tm, Ii, Ti, i_tol, t_tol, t_tol_f, curve_type, i2t_tol):
            k_I2T = '((d.i_i2t)**2)*d.t_i2t'
            kr_I2t = '((d.ir_i2t)**2)*d.tr_i2t'
            k_iec = 'd.k_iec'
            c_iec = 'd.c_iec'
            alpha_iec = 'd.alpha_iec'
            I1_ = I1 + " if d.curve_l == 'I2T' else " + I1 + "*1.01"
            curve_vars = {'tms'         : Tr, 
                            'i_n'         : Ir, 
                            'i1'          : I1_,
                            'i2'          : Im,
                            't_min'       : Tm, 
                            'n'           : 100,
                            'i_tol'       : i_tol,
                            't_tol'       : t_tol,
                            't_tol_f'     : t_tol_f,
                            'curve_type'  : curve_type,

                            'k_i2t'       : kr_I2t,
                            'k_iec'       : k_iec,
                            'c_iec'       : c_iec,
                            'alpha_iec'   : alpha_iec,
                            }
            # M
            curve1 = [  ('point', I1, T_conv),
                        ('d.curve_l', curve_vars),
                        ('point', Im, Tm),
                        ('point', Isc, Tm),]
            # M, I
            curve2 = [('point', I1, T_conv),
                        ('d.curve_l', curve_vars),
                        ('point', Im, Tm),
                        ('point', Ii, Tm),
                        ('point', Ii, Ti),
                        ('point', Isc, Ti),]
            # M, I2t
            curve3 = [('point', I1, T_conv),
                        ('d.curve_l', curve_vars),
                        ('I2T', i2t_tol, Ir, Im, Isc, Tm, 100, k_I2T, 2),
                        ('point', Isc, Tm),]
            # M, I, I2t
            curve4 = [('point', I1, T_conv),
                        ('d.curve_l', curve_vars),
                        ('I2T', i2t_tol, Ir, Im, Ii, Tm, 100, k_I2T, 2),
                        ('point', Ii, Tm),
                        ('point', Ii, Ti),
                        ('point', Isc, Ti),]
            return curve1, curve2, curve3, curve4
        
        # Upper curves
        Ir = 'd.i_r*' + In
        I1 = 'd.i_f*d.i_r*' + In
        Tr = 'd.t_r'
        T_conv = 1e5
        Im = '(d.i_m*(100+d.tol_im_p)/100)*' + Ir
        Tm = 'max(d.t_m*(100+d.tol_tm_p)/100, d.t_m+d.tol_tmf_p)'
        Ii = '(d.i_i*(100+d.tol_ii_p)/100)*' + In
        Ti = 'd.t_i_p'
        i_tol = 'd.i_f*100-100'
        t_tol = 'd.tol_tr_p'
        t_tol_f = 'd.tol_trf_p'
        curve_type = PROT_UPPER
        i2t_tol = '(100+d.tol_m_i2t_p)/100'
        curve_u1, curve_u2, curve_u3, curve_u4 = get_curves(Ir, I1, Tr, T_conv, Im, Tm, Ii, Ti, i_tol, t_tol, t_tol_f, curve_type, i2t_tol)
        # Lower curves
        Ir = 'd.i_r*' + In
        I1 = 'd.i_nf*d.i_r*' + In
        Tr = 'd.t_r'
        T_conv = 1e5
        Im = '(d.i_m*(100-d.tol_im_m)/100)*' + Ir
        Tm = 'max(0.00001, min(d.t_m*(100-d.tol_tm_m)/100, d.t_m-d.tol_tmf_m))'
        Ii = '(d.i_i*(100-d.tol_ii_m)/100)*' + In
        Ti = 'd.t_i_m'
        i_tol = 'd.i_nf*100-100'
        t_tol = '-d.tol_tr_m'
        t_tol_f = '-d.tol_trf_m'
        curve_type = PROT_LOWER
        i2t_tol = '(100-d.tol_m_i2t_m)/100'
        curve_l1, curve_l2, curve_l3, curve_l4 = get_curves(Ir, I1, Tr, T_conv, Im, Tm, Ii, Ti, i_tol, t_tol, t_tol_f, curve_type, i2t_tol)

        parameters = {  'head_l'    : ['Long time protection', '', '', None, '', 'heading'],
                        'curve_l'   : ['Long time trip curve', '', 'I2T', long_trip_curves, '', 'str', True, curves_default_values_dict],
                        'i_r'       : ['Ir', xIn, 1, None, 'Thermal protection pickup current'],
                        'i_nf'      : ['Inf', 'xIr', 1.05, None, 'Conventional non-tripping current'],
                        'i_f'       : ['If', 'xIr', 1.3, None, 'Conventional tripping current'],
                        't_r'       : ['Tr', '', 1, None, 'Time multiplier setting'],
                        'k_iec'     : ['k', '', 800, None, '', 'float', False],
                        'c_iec'     : ['c', '', 0, None, '', 'float', False],
                        'alpha_iec' : ['alpha', '', 2, None, '', 'float', False],
                        'ir_i2t'    : ['Ir i2t', 'xIr', 6, None, '', 'float', True],
                        'tr_i2t'    : ['Tr i2t', 's', 16, None, 'Operation time @ Ir i2t', 'float', True],
                        'tol_tr_p'  : ['Tr tol (+)', '%', 20, None, 'Time delay tolerance (+)', [1,0,None]],
                        'tol_tr_m'  : ['Tr tol (-)', '%', 20, None, 'Time delay tolerance (-)', [1,0,99]],
                        'tol_trf_p' : ['Tr tol fixed (+)', 's', 0, None, 'Time delay tolerance fixed (+)', [3,0,None]],
                        'tol_trf_m' : ['Tr tol fixed (-)', 's', 0, None, 'Time delay tolerance fixed (-)', [3,0,None]],

                        'head_s'        : ['Short time protection', '', '', None, '', 'heading'],
                        'i_m'           : ['Isd', 'xIr', 8, None, 'Short time pickup current'],
                        't_m'           : ['Tsd', 's', 0.1, None, 'Short time time delay'],
                        'tol_im_p'      : ['Isd tol (+)', '%', 10, None, 'Current pickup tolerance (+)', [1,0,None]],
                        'tol_im_m'      : ['Isd tol (-)', '%', 10, None, 'Current pickup tolerance (-)', [1,0,99]],
                        'tol_tm_p'      : ['Tsd tol (+)', '%', 20, None, 'Time delay tolerance % (+)', [1,0,None]],
                        'tol_tm_m'      : ['Tsd tol (-)', '%', 20, None, 'Time delay tolerance % (-)', [1,0,99]],
                        'tol_tmf_p'     : ['Tsd tol fixed (+)', 's', 0, None, 'Time delay tolerance fixed (+)', [3,0,None]],
                        'tol_tmf_m'     : ['Tsd tol fixed (-)', 's', 0, None, 'Time delay tolerance fixed (-)', [3,0,None]],
                        
                        'i2t_on'        : ['Enable I2t protection', '', False, [True, False], '', 'bool', True, i2t_default_values_dict],
                        'i_i2t'         : ['I i2t', 'xIr', 10, None, '', 'float', False],
                        't_i2t'         : ['T i2t', 's', 0.1, None, 'Operation time @ I i2t', 'float', False],
                        'tol_m_i2t_p'  : ['Tm (I2t) tol (+)', '%', 20, None, 'Time delay tolerance (+)', [1,0,None], False],
                        'tol_m_i2t_m'  : ['Tm (I2t) tol (-)', '%', 20, None, 'Time delay tolerance (-)', [1,0,99], False],
                        
                        'head_i'        : ['Instantaneous protection', '', '', None, '', 'heading'],
                        'i_i_on'        : ['Enable instantaneous protection', '', False, [True, False], '', 'bool', True, ii_default_values_dict],
                        'i_i'           : ['Ii', xIn, 15, None, 'Instantaneous pickup current', 'float', False],
                        't_i_p'         : ['Ti (max)', 's', 0.02, None, 'Instantaneous trip time delay (max)', 'float', False],
                        't_i_m'         : ['Ti (min)', 's', 0.001, None, 'Instantaneous trip time delay (min)', 'float', False],
                        'tol_ii_p'      : ['Ii tol (+)', '%', 20, None, 'Current pickup tolerance (+)', [1,0,None], False],
                        'tol_ii_m'      : ['Ii tol (-)', '%', 20, None, 'Current pickup tolerance (-)', [1,0,99], False]
                        }

        curves = {'select_expr_list': select_expr_list,
                    'curve_u1': curve_u1, 'curve_l1': curve_l1,
                    'curve_u2': curve_u2, 'curve_l2': curve_l2,
                    'curve_u3': curve_u3, 'curve_l3': curve_l3,
                    'curve_u4': curve_u4, 'curve_l4': curve_l4,}
    
    return parameters, curves

def get_thermal_protection_models(prot_class, magnetic=False):
    curves = {}
    parameters = dict()

    # Thermal trip curves
    # trip_curves = ['Class 10A', 'Class 10', 'Class 20', 'Class 30']
    tms_dict = {'Class 10A': [93,355],
                'Class 10': [186,355],
                'Class 20': [279,710],
                'Class 30': [418.5,1065]}

    # Instantaneous trip constants
    ii_default_values_dict = {  True    : {'i_i': 13, 't_i_p': 0.02, 't_i_m': 0.001, 'tol_ii_p': 20, 'tol_ii_m': 20}, 
                                False   : {'i_i': None, 't_i_p': None, 'tol_ii_p': None, 'tol_ii_m': None, 'tol_ii_m': None}}
        
    In = 'f.In'
    xIn = 'xIn'
    Isc = '1000*f.Isc'

    if magnetic is False:

        def get_curves(Ir, Tr, t_min):
            T_conv = '1e5'
            curve = [   ('point', Ir, T_conv),
                        ('THERMAL', Tr, Ir, Ir + '*1.05', Isc, t_min, 100)]
            return curve
        
        # Upper curve
        Ir = '1.2*d.i_r*' + In
        Tr = tms_dict[prot_class][1]
        t_min = 'd.t_min'
        curve_u = get_curves(Ir, Tr, t_min)
        # Lower curve
        Ir = '1.05*d.i_r*' + In
        Tr = tms_dict[prot_class][0]
        t_min = 0
        curve_l = get_curves(Ir, Tr, t_min)
        
        parameters = {'head_t'  : ['Thermal protection', '', '', None, '', 'heading'],
                    'i_r'       : ['Ir', xIn, 1, None, 'Thermal protection pickup current'],
                    't_min'     : ['Tmin', 's', 0.1, None, 'Minimum trip time']}
        curves = {'curve_u': curve_u, 'curve_l': curve_l}
    
    elif magnetic is True:
        select_expr_list = ['d.i_i_on is False',
                            'd.i_i_on is True']

        def get_curves(Ir, Tr, t_min, Ii, Ti):
            T_conv = '1e5'
            curve1 = [   ('point', Ir, T_conv),
                        ('THERMAL', Tr, Ir, Ir + '*1.01', Isc, t_min, 100)]
            curve2 = [   ('point', Ir, T_conv),
                        ('THERMAL', Tr, Ir, Ir + '*1.01', Ii, Ti, 100),
                        ('point', Ii, Ti),
                        ('point', Isc, Ti)]
            return curve1, curve2
        
        # Upper curve
        Ir = '1.2*d.i_r*' + In
        Tr = tms_dict[prot_class][1]
        t_min = 'd.t_min'
        Ii = '(d.i_i*(100+d.tol_ii_p)/100)*' + In
        Ti = 'd.t_i_p'
        curve_u1, curve_u2 = get_curves(Ir, Tr, t_min, Ii, Ti)
        # Lower curve
        Ir = '1.05*d.i_r*' + In
        Tr = tms_dict[prot_class][0]
        t_min = 0
        Ii = '(d.i_i*(100-d.tol_ii_m)/100)*' + In
        Ti = 'd.t_i_m'
        curve_l1, curve_l2 = get_curves(Ir, Tr, t_min, Ii, Ti)
        
        parameters = {'head_t'  : ['Thermal protection', '', '', None, '', 'heading'],
                    'i_r'       : ['Ir', xIn, 1, None, 'Thermal protection pickup current'],
                    't_min'     : ['Tmin', 's', 0.1, None, 'Minimum trip time'],
                    'head_i'        : ['Instantaneous protection', '', '', None, '', 'heading'],
                    'i_i_on'        : ['Enable instantaneous protection', '', False, [True, False], '', 'bool', True, ii_default_values_dict],
                    'i_i'           : ['Ii', xIn, 13, None, 'Instantaneous pickup current', 'float', False],
                    't_i_p'         : ['Ti (max)', 's', 0.02, None, 'Instantaneous trip time delay (max)', 'float', False],
                    't_i_m'         : ['Ti (min)', 's', 0.001, None, 'Instantaneous trip time delay (min)', 'float', False],
                    'tol_ii_p'      : ['Ii tol (+)', '%', 20, None, 'Current pickup tolerance (+)', [1,0,None], False],
                    'tol_ii_m'      : ['Ii tol (-)', '%', 20, None, 'Current pickup tolerance (-)', [1,0,99], False]}
        
        curves = {'select_expr_list': select_expr_list,
                    'curve_u1': curve_u1, 'curve_l1': curve_l1,
                    'curve_u2': curve_u2, 'curve_l2': curve_l2}
        
    return parameters, curves
