#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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

import logging, copy, bisect
from math import sin, cos, acos, asin, exp, log, log10
from scipy.interpolate import interp1d
from gi.repository import Gtk, Gdk
import cairo

# local files import
from .. import misc

# Get logger object
log = logging.getLogger(__name__)

class GraphModel():
    """Class for displaying graph"""
    
    def __init__(self, model):
        self.model = model
        self.mode = model['mode']
        self.xval = model['xval']
        self.yval = model['yval']
        self.title = model['title']
            
    # Functions
    
    def modify_data(self, xdata, ydata):
        self.model['xval'] = xdata
        self.model['yval'] = ydata
        self.xval = xdata
        self.yval = ydata
        
    def modify_title(self, title):
        self.model['title'] = title
    
    def get_model(self):
        return self.model
    
    def get_value_func(self):
        return interp1d(self.xval, self.yval)
    
    def add_point(self, x, y):
        xval = copy.copy(self.xval)
        yval = copy.copy(self.yval)
        
        if self.mode == misc.GRAPH_DATATYPE_FREE:
            xval.append(x)
            yval.append(y)
        elif self.mode == misc.GRAPH_DATATYPE_PROFILE:
            if x in xval:
                pos = xval.index(x)
                yval[pos] = y
            else:
                bisect.insort(xval, x)
                pos = xval.index(x)
                yval.insert(pos, y)
                
        self.modify_data(xval, yval)
        
    def remove_point(self, x, y):
        xval = copy.copy(self.xval)
        yval = copy.copy(self.yval)
        
        if self.mode in (misc.GRAPH_DATATYPE_FREE, misc.GRAPH_DATATYPE_PROFILE):            
            if x in xval:
                pos = xval.index(x)
                yval.pop(pos)
                xval.pop(pos)
                
        self.modify_data(xval, yval)
        
