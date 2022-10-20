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

import logging, copy
from math import sin, cos, acos, asin, exp, log, log10
from mako.template import Template as ExprTemplate
from gi.repository import Gtk, Gdk
import cairo

# local files import
from .. import misc
from .element import ElementModel

# Get logger object
log = logging.getLogger(__name__) 


class Template(ElementModel):
    """Class for rendering cross reference elements"""
    def __init__(self, width=misc.PAGE_WIDTH, height=misc.PAGE_HEIGHT):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_template'
        self.name = 'Template'
        self.group = 'Miscellaneous'
        self.icon = None
        self.ports = []
        self.fields = dict()
        
        self.border_left = 15/misc.POINT_TO_MM/misc.M
        self.border_right = 5/misc.POINT_TO_MM/misc.M
        self.border_top = 5/misc.POINT_TO_MM/misc.M
        self.border_bottom = 5/misc.POINT_TO_MM/misc.M
        self.border_width = 5/misc.POINT_TO_MM/misc.M
        self.set_dimensions(width, height)
        
    def set_dimensions(self, width=misc.PAGE_WIDTH, height=misc.PAGE_HEIGHT):
        # Set page dimensions
        self.model_width = width/misc.POINT_TO_MM/misc.M
        self.model_height = height/misc.POINT_TO_MM/misc.M
        # Set drawing area dimentions
        drawing_width = self.model_width - self.border_left - self.border_right - 2*self.border_width
        drawing_height = self.model_height - self.border_top - self.border_bottom - 2*self.border_width
        # Reference system dimentions
        horizontal_ref_nos = 2*round(drawing_width/2/(50/misc.POINT_TO_MM/misc.M))
        vertical_ref_nos = 2*round(drawing_height/2/(50/misc.POINT_TO_MM/misc.M))
        horizontal_ref_length = drawing_width/horizontal_ref_nos
        vertical_ref_length = drawing_height/vertical_ref_nos
        D = self.border_width/2 - misc.SCHEM_FONT_SIZE/ misc.M/2
        # Helper functions
        def line(x, y, length, orientation):
            if orientation == 'horizontal':
                return ['LINE',(x, y), (x+length, y), []]
            else:
                return ['LINE',(x, y), (x, y+length), []]
        
        self.text_model = []
        self.schem_model = [ 
                             # Outer border
                             ['RECT',(self.border_left, self.border_top), 
                              self.model_width - self.border_left - self.border_right,
                              self.model_height - self.border_top - self.border_bottom,
                              False, []],
                             # Inner border
                             ['RECT',(self.border_left + self.border_width, self.border_top + self.border_width), 
                              drawing_width, drawing_height,
                              False, [], 'thick'],
                             # Cut mark rectangle 1
                             ['RECT',(0,0), self.border_width, 2*self.border_width, True, []],
                             ['RECT',(0,0), 2*self.border_width, self.border_width, True, []],
                             # Cut mark rectangle 2
                             ['RECT',(0,self.model_height-self.border_width), 2*self.border_width, self.border_width, True, []],
                             ['RECT',(0,self.model_height-2*self.border_width), self.border_width, 2*self.border_width, True, []],
                             # Cut mark rectangle 3
                             ['RECT',(self.model_width-self.border_width,0), self.border_width, 2*self.border_width, True, []],
                             ['RECT',(self.model_width-2*self.border_width,0), 2*self.border_width, self.border_width, True, []],
                             # Cut mark rectangle 4
                             ['RECT',(self.model_width-self.border_width,self.model_height-2*self.border_width), self.border_width, 2*self.border_width, True, []],
                             ['RECT',(self.model_width-2*self.border_width,self.model_height-self.border_width), 2*self.border_width, self.border_width, True, []],
                             # Centre lines
                             line(self.border_left+self.border_width+drawing_width/2, self.border_top+self.border_width, self.border_width, 'vertical'),
                             line(self.border_left+self.border_width+drawing_width/2, self.border_top+drawing_height, self.border_width, 'vertical'),
                             line(self.border_left+self.border_width, self.border_top+self.border_width+drawing_height/2, self.border_width, 'horizontal'),
                             line(self.border_left+drawing_width, self.border_top+self.border_width+drawing_height/2, self.border_width, 'horizontal'),
                           ]
        # Draw reference lines and text
        for refno in range(1, horizontal_ref_nos+1):
            x = self.border_left + self.border_width + horizontal_ref_length * refno
            y1 = self.border_top
            y2 = self.border_top + self.border_width + drawing_height
            if refno < horizontal_ref_nos:
                self.schem_model.append(line(x, y1, self.border_width, 'vertical'))
                self.schem_model.append(line(x, y2, self.border_width, 'vertical'))
            self.text_model.append([(x-horizontal_ref_length/2,y1+ D), str(refno), True])
            self.text_model.append([(x-horizontal_ref_length/2,y2+ D), str(refno), True])
        ignored_count = 0
        for refno in range(1, vertical_ref_nos+1):
            y = self.border_top + self.border_width + vertical_ref_length * refno
            x1 = self.border_left
            x2 = self.border_left + self.border_width + drawing_width
            refcode = chr(refno+64+ignored_count)
            if refcode in ('I','O'):
                ignored_count += 1
                refcode = chr(refno+64+ignored_count)
            if refno < vertical_ref_nos:
                self.schem_model.append(line(x1, y, self.border_width, 'horizontal'))
                self.schem_model.append(line(x2, y, self.border_width, 'horizontal'))
            self.text_model.append([(x1+self.border_width/3,y-vertical_ref_length/2), refcode, True])
            self.text_model.append([(x2+self.border_width/3,y-vertical_ref_length/2), refcode, True])
            
    def modify_extends(self):
        pass
            
            
class TitleBlock(ElementModel):
    """Class for rendering cross reference elements"""
    def __init__(self):
        # Global
        ElementModel.__init__(self, (0,0))
        self.code = 'element_template'
        self.name = 'Template'
        self.group = 'Miscellaneous'
        self.icon = None
        self.ports = []
        self.fields = dict()
        
        F = 1/misc.POINT_TO_MM/misc.M
        D = 1*F
        T = misc.SCHEM_FONT_SIZE/misc.M + 2*D
        self.model_width = 180*F
        self.model_height = 36*F
        self.schem_model = [['RECT',(0,0), self.model_width, self.model_height, False, []],
                            # Vertical lines
                            ['LINE',(73*F, 0), (73*F, 36*F), []],
                            ['LINE',(130*F, 9*F), (130*F, 36*F), []],
                            ['LINE',(28*F, 0), (28*F, 9*F), []],
                            ['LINE',(118*F, 0), (118*F, 9*F), []],
                            ['LINE',(163*F, 0), (163*F, 9*F), []],
                            ['LINE',(137*F, 27*F), (137*F, 36*F), []],
                            ['LINE',(160*F, 27*F), (160*F, 36*F), []],
                            ['LINE',(170*F, 27*F), (170*F, 36*F), []],
                            # Horizontal lines
                            ['LINE',(0, 9*F), (180*F, 9*F), []],
                            ['LINE',(73*F, 18*F), (180*F, 18*F), []],
                            ['LINE',(130*F, 27*F), (180*F, 27*F), []], ]
        self.text_model = [[(D, D), 'Responsible dept.', True, misc.TITLE_FONT_SIZE_SMALL], 
                           [(28*F+D, D), 'Technical reference', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(73*F+D, D), 'Created by', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(118*F+D, D), 'Approved by', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(73*F+D, 9*F+D), 'Document Type', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(73*F+D, 18*F+D), 'Title, Supplementary Title', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(130*F+D, 9*F+D), 'Document Status', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(130*F+D, 27*F+D), 'Rev.', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(137*F+D, 27*F+D), 'Date of issue', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(160*F+D, 27*F+D), 'Lang.', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(170*F+D, 27*F+D), 'Sheet', True, misc.TITLE_FONT_SIZE_SMALL],
                           [(D, 9*F-T), '${drawing_field_dept}', True, misc.TITLE_FONT_SIZE], 
                           [(28*F+D, 9*F-T), '${drawing_field_techref}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 9*F-T), '${drawing_field_created}', True, misc.TITLE_FONT_SIZE],
                           [(118*F+D, 9*F-T), '${drawing_field_approved}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 18*F-T), '${type}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 27*F-T), '${project_name}', True, misc.TITLE_FONT_SIZE],
                           [(73*F+D, 27*F+D), '${title}', True, misc.TITLE_FONT_SIZE],
                           [(130*F+D, 18*F-T), '${status}', True, misc.TITLE_FONT_SIZE],
                           [(130*F+D, 36*F-T), '${rev}', True, misc.TITLE_FONT_SIZE],
                           [(137*F+D, 36*F-T), '${date_of_issue}', True, misc.TITLE_FONT_SIZE],
                           [(160*F+D, 36*F-T), '${drawing_field_lang}', True, misc.TITLE_FONT_SIZE],
                           [(170*F+D, 36*F-T), '${sheet_no}', True, misc.TITLE_FONT_SIZE],
                           [(73*F/2, 18*F-T), '${drawing_field_address}', True, misc.TITLE_FONT_SIZE, misc.SCHEM_FONT_WEIGHT, 'center'],
                           [(130*F+50*F/2, 22.5*F-0.5*T), '${drawing_no}', True, misc.TITLE_FONT_SIZE, misc.SCHEM_FONT_WEIGHT_BOLD, 'center'], ]
    
    def set_fields(self, fields):
        self.fields = fields
        # Set page dimensions
        border_right = 5/misc.POINT_TO_MM/misc.M
        border_bottom = 5/misc.POINT_TO_MM/misc.M
        border_width = 5/misc.POINT_TO_MM/misc.M
        
        self.x = (self.fields['page_width']['value']/misc.M - border_right - border_width - self.model_width)*misc.M
        self.y = (self.fields['page_height']['value']/misc.M - border_bottom - border_width - self.model_height)*misc.M
        
    def modify_extends(self):
        pass
