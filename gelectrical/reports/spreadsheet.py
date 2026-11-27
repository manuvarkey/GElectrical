#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# spreadsheet
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

"""Spreadsheet input and output (openpyxl). No GUI imports."""

import copy, logging
import openpyxl

from ..core.expressions import evaluate_numeric

# Setup logger object
log = logging.getLogger(__name__)


class Spreadsheet:
    """Manage input and output of spreadsheets"""
    
    def __init__(self, filename=None):
        if filename is not None:
            self.spreadsheet = openpyxl.load_workbook(filename)
        else:
            self.spreadsheet = openpyxl.Workbook()
        self.sheet = self.spreadsheet.active
    
    def save(self, filename):
        """Save worksheet to file"""
        self.spreadsheet.save(filename)
        
    # Sheet management
    
    def new_sheet(self):
        """Create a new sheet to spreadsheet and set as active"""
        self.sheet = self.spreadsheet.create_sheet()  
            
    def sheets(self):
        """Returns a list of sheetnames"""
        return self.spreadsheet.sheetnames
        
    def length(self):
        """Get number of rows in sheet"""
        return self.sheet.max_row
        
    def set_title(self, title):
        """Set title of sheet"""
        self.sheet.title = title
        
    def set_page_settings(self, orientation='portrait', papersize='A4', font=None, print_title_rows = None):
        # Orientation
        if orientation == 'portrait':
            self.sheet.page_setup.orientation = openpyxl.worksheet.worksheet.Worksheet.ORIENTATION_PORTRAIT
        elif orientation == 'landscape':
            self.sheet.page_setup.orientation = openpyxl.worksheet.worksheet.Worksheet.ORIENTATION_LANDSCAPE
            
        # Paper size
        if papersize == 'A4':
            self.sheet.page_setup.paperSize = openpyxl.worksheet.worksheet.Worksheet.PAPERSIZE_A4
            
        # Print title rows
        self.sheet.print_title_rows = print_title_rows
            
        # General settings
        self.sheet.page_setup.fitToPage = True
        self.sheet.page_setup.fitToHeight = 99
        self.sheet.page_setup.fitToWidth = 1
        self.sheet.print_options.horizontalCentered = True

        # Set font
        if font:
            for row in range(1, self.length()+1):
                for cell in self.sheet[row]:
                    font_style = copy.copy(cell.font)
                    font_style.name = font
                    cell.font = font_style

    def set_column_widths(self, widths):
        """Set column widths of sheet"""
        for column, width in enumerate(widths, 1):
            col_letter = openpyxl.utils.get_column_letter(column)
            self.sheet.column_dimensions[col_letter].width = width
        
    def set_active_sheet(self, sheetref):
        """Set active sheet of spreadsheet"""
        sheetname = ''
        sheetno = None
        if type(sheetref) is int:
            sheetno = sheetref
        elif type(sheetref) is str:
            sheetname = sheetref
        
        if sheetname in self.sheets():
            self.sheet = self.spreadsheet[sheetname]
        elif sheetno is not None and sheetno < len(self.sheets()):
            self.sheet = self.spreadsheet[self.sheets()[sheetno]]
    
    def set_style(self, row, col, bold=False, wrap_text=True, horizontal='general', vertical='bottom', fill=None):
        """Set style of individual cell"""
        font = openpyxl.styles.Font(bold=bold)
        alignment = openpyxl.styles.Alignment(wrap_text=wrap_text, horizontal=horizontal, vertical=vertical)

        self.sheet.cell(row=row, column=col).font = font
        self.sheet.cell(row=row, column=col).alignment = alignment
        
        if fill == '#FFFFFF':
            patternfill = openpyxl.styles.PatternFill()
            self.sheet.cell(row=row, column=col).fill = patternfill
        elif fill is not None:
            patternfill = openpyxl.styles.PatternFill(start_color=fill[1:], end_color=fill[1:], fill_type='solid')
            self.sheet.cell(row=row, column=col).fill = patternfill
        
    # Data addition functions
            
    def append(self, ss_obj):
        """Append an sheet to current sheet"""
        sheet = ss_obj.spreadsheet.active
        rowcount = self.length()
        for row_no, row in enumerate(sheet.rows, 1):
            for col_no, cell in enumerate(row, 1):
                self.sheet.cell(row=row_no+rowcount, column=col_no).value = cell.value
                if cell.has_style:
                    self.sheet.cell(row=row_no+rowcount, column=col_no).font = copy.copy(cell.font)
                    self.sheet.cell(row=row_no+rowcount, column=col_no).border = copy.copy(cell.border)
                    self.sheet.cell(row=row_no+rowcount, column=col_no).fill = copy.copy(cell.fill)
                    self.sheet.cell(row=row_no+rowcount, column=col_no).number_format = copy.copy(cell.number_format)
                    self.sheet.cell(row=row_no+rowcount, column=col_no).protection = copy.copy(cell.protection)
                    self.sheet.cell(row=row_no+rowcount, column=col_no).alignment = copy.copy(cell.alignment)

    def append_data(self, data, bold=False, italic=False, wrap_text=True, horizontal='general', vertical='bottom', fill = None):
        """Append data to current sheet"""
        rowcount = self.length()
        self.insert_data(data, rowcount+1, 1, bold, italic,wrap_text, horizontal, vertical, fill)
    
    def insert_data(self, data, start_row=1, start_col=1, bold=False, italic=False, wrap_text=True, horizontal='general', vertical='bottom', fill=None):
        """Insert data to current sheet"""
        # Setup styles
        font = openpyxl.styles.Font(bold=bold, italic=italic)
        
        if fill == '#FFFFFF':
            patternfill = openpyxl.styles.PatternFill()
        elif fill is not None:
            patternfill = openpyxl.styles.PatternFill(start_color=fill[1:], end_color=fill[1:], fill_type='solid')
            
        alignment = openpyxl.styles.Alignment(wrap_text=wrap_text, horizontal=horizontal, vertical=vertical)
        # Apply data and styles
        for row_no, row in enumerate(data, start_row):
            for col_no, value in enumerate(row, start_col):
                self.sheet.cell(row=row_no, column=col_no).value = value
                self.sheet.cell(row=row_no, column=col_no).font = font
                
                if fill:
                    self.sheet.cell(row=row_no, column=col_no).fill = patternfill
                    
                self.sheet.cell(row=row_no, column=col_no).alignment = alignment
                
    def add_merged_cell(self, value, row=None, width=2, bold=False, wrap_text=True, horizontal='center', start_column=1):
        """Add a merged cell of prescrbed width"""
        if row is None:
            rowstart = self.length() + 1
        else:
            rowstart = row
        self.sheet.merge_cells(start_row=rowstart,start_column=start_column,end_row=rowstart,end_column=start_column+width-1)
        self.__setitem__([rowstart,start_column], value)
        self.set_style(rowstart, start_column, bold, wrap_text, horizontal)
    
    def __setitem__(self, index, value):
        """Set an individual cell"""
        self.sheet.cell(row=index[0], column=index[1]).value = value
        
    def __getitem__(self, index):
        """Set an individual cell"""
        return self.sheet.cell(row=index[0], column=index[1]).value
            
    # Bulk read functions
    
    def read_rows(self, columntypes = [], start=0, end=-1, left=0, allow_formula=False):
        """Read and validate selected rows from current sheet"""
        # Get count of rows
        rowcount = self.length()
        if end < 0 or end >= rowcount:
            count_actual = rowcount
        else:
            count_actual = end
        
        items = []
        for row in range(start, count_actual):
            cells = []
            skip = 0  # No of columns to be skiped ex. breakup, total etc...
            for columntype, i in zip(columntypes, list(range(left, len(columntypes)+left))):
                cell = self.sheet.cell(row = row + 1, column = i - skip + 1).value
                if columntype == str:
                    if cell is None:
                        cell_formated = ""
                    else:
                        cell_formated = str(cell)
                elif columntype == float:
                    if cell is None:
                        if allow_formula:
                            cell_formated = '0'
                        else:
                            cell_formated = 0
                    else:
                        if allow_formula:
                            try:  # try evaluating float
                                if len(str(cell)) > 1 and str(cell)[0] == '=':
                                    formula = str(cell)[1:]
                                else:
                                    formula = str(cell)
                                evaluated = str(float(evaluate_numeric(formula)))
                                cell_formated = formula
                            except:
                                cell_formated = '0'
                        else:
                            try:  # try evaluating float
                                cell_formated = str(float(cell))
                            except:
                                cell_formated = 0

                elif columntype == int:
                    if cell is None:
                        if allow_formula:
                            cell_formated = '0'
                        else:
                            cell_formated = 0
                    else:
                        if allow_formula:
                            try:  # try evaluating int
                                if len(str(cell)) > 1 and str(cell)[0] == '=':
                                    formula = str(cell)[1:]
                                else:
                                    formula = str(cell)
                                evaluated = str(int(evaluate_numeric(formula)))
                                cell_formated = formula
                            except:
                                cell_formated = '0'
                        else:
                            try:  # try evaluating int
                                cell_formated = str(int(cell))
                            except:
                                cell_formated = 0
                else:
                    cell_formated = ''
                    log.warning("Spreadsheet - Value skipped on import - " + str((row, i)))
                if columntype is None:
                    skip = skip + 1
                cells.append(cell_formated)
            items.append(cells)
        return items

        
