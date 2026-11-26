#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# interpolation
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

"""Curve interpolation helpers (protection and damage curves)."""

import numpy as np
from scipy.interpolate import interp1d

def log_interpolate(points, num=10, prefix='point'):
    x = [x for x,y in points]
    y = [y for x,y in points]
    fit_func = interp1d(np.log10(x), np.log10(y), kind='quadratic')
    fit_func_mod = lambda x: list(10**(fit_func(np.log10(np.array(x)))))
    X = np.geomspace(min(x), max(x), num=num)
    Y = fit_func_mod(X)
    if prefix:
        points_int = [(prefix,x,y) for x,y in zip(X,Y)]
    else:
        points_int = [(x,y) for x,y in zip(X,Y)]
    return points_int

def log_interpolate_piecewise(points):
    
    def log_interpolate(x, y, num):
        fit_func = interp1d(np.log10(x), np.log10(y))
        fit_func_mod = lambda x: list(10**(fit_func(np.log10(np.array(x)))))
        X = np.geomspace(min(x), max(x), num=num)
        Y = fit_func_mod(X)
        return tuple(X), tuple(Y)

    I0, t0 = points[0]
    curve_i = [I0]
    curve_t = [t0]
    for I,t in points[1:]:
        if I0 != 0 and t0 != 0 and I !=0 and t != 0:
            deli = I/I0
            delt = t/t0
            dist_norm = max(deli, delt)
            if dist_norm > 1.5:
                num = int(20*np.log10(dist_norm))
                i_vals = [I0, I]
                t_vals = [t0, t]
                i_array_int, t_array_int = log_interpolate(i_vals, t_vals, num)
                curve_i += i_array_int[1:]
                curve_t += t_array_int[1:]
            else:
                curve_i += [I]
                curve_t += [t]
        else:
            curve_i += [I]
            curve_t += [t]
        I0, t0 = I, t
    points_int = tuple([(x,y) for x, y in zip(curve_i, curve_t)])
    return points_int

