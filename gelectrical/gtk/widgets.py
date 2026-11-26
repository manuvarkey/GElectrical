#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# widgets
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

"""GTK helpers of the legacy UI: dialogs, progress revealer, splash screen,
font string parsing and icon loading (moved from ``misc.py``, M2)."""

import subprocess, threading, platform, logging, time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Pango', '1.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf

from ..core.paths import abs_path
from ..core.style import COLOR_INACTIVE
from ..reports.spreadsheet import Spreadsheet

# Setup logger object
log = logging.getLogger(__name__)


class SpreadsheetDialog:
    """Dialog for manage input and output of spreadsheets"""
   
    def __init__(self, parent, filename, columntypes, captions, dimensions = None, allow_formula=False):
        """Initialise SpreadsheetDialog class
        
            Arguments:
                parent: Parent widget (Main window)
                filename: 
                columntypes: Data types of columns. 
                             Takes following values:
                                misc.MEAS_NO: Integer
                                misc.MEAS_L: Float
                                misc.MEAS_DESC: String
                                misc.MEAS_CUST: Value omited
                dimensions: List of two lists passing column widths and expand properties
                allow_formula: Reads all values as string
        """
        log.info('SpreadsheetDialog - Initialise')
        # Setup variables
        self.parent = parent
        self.filename = filename
        self.captions = captions
        self.columntypes = columntypes
        self.dimensions = dimensions
        self.allow_formula = allow_formula
        
        self.top = 0
        self.bottom = 0
        self.left = 0
        self.right = 0
        self.values = []
        self.spreadsheet = None
        self.sheet = ''

        # Setup dialog window
        self.builder = Gtk.Builder()
        self.builder.add_from_file(abs_path("gtk", "interface","spreadsheetdialog.glade"))
        self.window = self.builder.get_object("dialog")
        self.window.set_transient_for(self.parent)
        self.window.set_default_size(1100,600)
        self.builder.connect_signals(self)

        # Get required objects
        self.combo = self.builder.get_object("combobox_sheet")
        self.combo_store = self.builder.get_object("liststore_combo")
        self.tree = self.builder.get_object("treeview_schedule")
        self.entry_top = self.builder.get_object("entry_top")
        self.entry_bottom = self.builder.get_object("entry_bottom")
        self.entry_left = self.builder.get_object("entry_left")
        self.entry_right = self.builder.get_object("entry_right")
        
        # Setup treeview
        self.columns = []
        self.cells = []
        # Setup row number column
        cell_row = Gtk.CellRendererText()
        column_row = Gtk.TreeViewColumn('', cell_row)
        column_row.add_attribute(cell_row, "markup", 0)
        column_row.set_min_width(50)
        column_row.set_fixed_width(50)
        cell_row.props.wrap_width = 50
        cell_row.props.background = COLOR_INACTIVE
        self.cells.append(cell_row)
        self.columns.append(column_row)
        self.tree.append_column(column_row)
        # Setup remaining columns
        for c_no, caption  in enumerate(self.captions,1):
            cell = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(caption, cell)
            column.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
            column.connect("notify", self.on_wrap_column_resized, cell)
            column.add_attribute(cell, "text", c_no)
            self.cells.append(cell)
            self.columns.append(column)
            self.tree.append_column(column)
        # Setup dimensions
        if dimensions is not None:
            self.setup_column_props(*dimensions)
        # Setup liststore model
        types = [str] + [str]*len(self.columntypes)
        self.store = Gtk.ListStore(*types)
        self.tree.set_model(self.store)
        # Misc options
        self.tree.set_grid_lines(3)
        self.tree.set_enable_search(True)
        search_cols = [no for no,x in enumerate(self.columntypes,1) if x == str]
        self.tree.set_search_equal_func(self.equal_func, [0,1,2,3])
        
        # Read file into spreadsheet object
        if filename is not None:
            try:
                self.spreadsheet = Spreadsheet(filename)
            except:
                self.spreadsheet = None
                log.warning('SpreadsheetDialog - Spreadsheet could not be read - ' + filename)
                
        # Setup combobox
        if self.spreadsheet:
            sheets = self.spreadsheet.sheets()
            for sheet in sheets:
                self.combo_store.append([sheet])
            if sheets:
                self.combo.set_active_id(sheets[0])
                self.update()
            

    def run(self):
        """Display dialog box and return data model
        
            Returns:
                Data Model on Ok
                [] on Cancel
        """
        self.window.show_all()
        response = self.window.run()
        self.window.destroy()

        if response == 1 and self.spreadsheet:
            log.info('SpreadsheetDialog - run - Response Ok')
            return self.values
        else:
            log.info('SpreadsheetDialog - run - Response Cancel')
            return []
    
    def update(self):
        """Update contents from input values"""
        log.info('SpreadsheetDialog - Update')
        
        # Read if sheet changed
        sheet = self.combo_store[self.combo.get_active_iter()][0]
        if sheet != self.sheet:
            self.sheet = sheet
            self.spreadsheet.set_active_sheet(self.sheet)
            self.entry_top.set_text('1')
            self.entry_bottom.set_text(str(self.spreadsheet.length()+1))
            self.entry_left.set_text('1')
            
        # Read values of entries
        self.top = int(self.entry_top.get_text())
        self.bottom = int(self.entry_bottom.get_text())
        self.left = int(self.entry_left.get_text())
        
        # Set values
        self.entry_right.set_text(str(self.left + len(self.columntypes)))
        
        # Read spreadsheet
        self.values = self.spreadsheet.read_rows(self.columntypes, start=self.top-1, end=self.bottom-1, left=self.left-1, allow_formula=self.allow_formula)
        
        # Update store
        self.store.clear()
        for slno, value in enumerate(self.values, self.top):
            formated_value = [str(x) if x != 0 else '' for x in value]
            self.store.append(['<b>' + str(slno) + '</b>'] + formated_value)
                
    def setup_column_props(self, widths, expandables):
        """Set column properties
            Arguments:
                widths: List of column widths type-> [int, ...]. None values are skiped.
                expandables: List of expand property type-> [bool, ...]. None values are skiped.
        """
        for column, cell, width, expandable in zip(self.columns[1:], self.cells[1:], widths, expandables):
            if width != None:
                column.set_min_width(width)
                column.set_fixed_width(width)
                cell.props.wrap_width = width
            if expandable != None:
                column.set_expand(expandable)
    
    def equal_func(self, model, column, key, iter, cols):
        """Equal function for interactive search"""
        search_string = ''
        for col in cols:
            search_string += ' ' + model[iter][col].lower()
        for word in key.split():
            if word.lower() not in search_string:
                return True
        return False
        
    def on_wrap_column_resized(self, column, pspec, cell):
        """ Automatically adjust wrapwidth to column width"""

        width = column.get_width() - 5
        oldwidth = cell.props.wrap_width
        
        if width > 0 and width != oldwidth:
            cell.props.wrap_width = width
            # Force redraw of treeview
            GLib.idle_add(column.queue_resize)
    
    # Callbacks
    
    def onRefreshClicked(self, button):
        """Refresh screen on button click"""
        
        # Sanitise entries
        if self.entry_top.get_text() == '':
            self.entry_top.set_text('1')
        if self.entry_bottom.get_text() == '':
            self.entry_bottom.set_text('1')
        if self.entry_left.get_text() == '':
            self.entry_left.set_text('1')
        
        if self.spreadsheet:
            self.update()
    
    def onEntryEditedNum(self, entry):
        """Treeview cell renderer for editable number field
        
            User Data:
                column: column in ListStore being edited
        """
        new_text = entry.get_text()
        num = ''
        if new_text != '':
            try:  # check whether item evaluates fine
                num = int(new_text)
                if num <= 0:
                   num = 1
            except:
                log.warning("SpreadsheetDialog - onEntryEditedNum - evaluation of [" 
                + new_text + "] failed")
        entry.set_text(str(num))

            
class ProgressRevealer:
    """Class for handling display of long running proccess"""
    
    def __init__(self, parent=None, label=None, progress=None):
        
        self.parent = parent
        self.label = label
        self.progress = progress
        # Setup data
        self.step = 0
        self.fraction = 0
        
    # Revealer functions
    
    def show(self):
        GLib.idle_add(self.parent.set_reveal_child, True)
    
    def close(self):
        GLib.idle_add(self.parent.set_reveal_child, False)
    
    # General functions
        
    def set_pulse_step(self, width):
        self.step = width
        self.fraction = 0
        
    def set_fraction(self, fraction):
        def callback():
            self.fraction = fraction
            self.progress.set_fraction(self.fraction)
            self.show()
            return False
        GLib.idle_add(callback)

    def get_fraction(self):
        return self.progress.get_fraction()
        
    def pulse(self, end=False):
        def callback():
            self.fraction += self.step
            if end:
                self.fraction = 1
            else:
                self.fraction = min(self.fraction + self.step, 1)
            self.progress.set_fraction(self.fraction)
            self.show()
            return False
        GLib.idle_add(callback)
        
    def add_message(self, message):
        GLib.idle_add(self.label.set_markup, message)
            
            
class SplashScreen:
    def __init__(self, callback, image_filename, min_splash_time=0 ):
        self.image = Gtk.Image.new_from_file(image_filename )
        self.window = Gtk.Window(Gtk.WindowType.TOPLEVEL)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.set_type_hint(Gdk.WindowTypeHint.SPLASHSCREEN)
        self.window.set_gravity(Gdk.Gravity.CENTER)
        self.window.set_auto_startup_notification(False)
        self.window.set_decorated(False)
        self.window.add(self.image)
        self.min_splash_time   = time.time() + min_splash_time
        self.window.show_all()
        GLib.timeout_add_seconds(1, callback)
   
    def exit(self):
        # Make sure the minimum splash time has elapsed
        timeNow = time.time()
        if timeNow < self.min_splash_time:
            time.sleep( self.min_splash_time - timeNow )
          
        # Destroy the splash window
        self.window.destroy( )
        

class Command(object):
    """Runs a command in a seperate thread"""
    
    def __init__(self, cmd):
        """Initialises class with command to be executed"""
        self.cmd = cmd
        self.process = None

    def run(self, timeout):
        """Run set command with selected timeout"""
        def target():
            if platform.system() == 'Linux':
                self.process = subprocess.Popen(self.cmd)
            elif platform.system() == 'Windows':
                self.process = subprocess.Popen(self.cmd, shell=True)
            log.info('Sub-process spawned - ' + str(self.process.pid))
            self.process.communicate()
        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            log.error('Terminating sub-process exceeding timeout - ' + str(self.process.pid))
            self.process.terminate()
            thread.join()
            return -1
        return 0

## GLOBAL METHODS

def pprint(variable):
    """Pretty print for debug purposes"""
    import json
    print(json.dumps(variable, indent=2))

def display_message(parent, message, title='', message_type='info'):
    '''Gets a single user input by diplaying a dialog box
    
    Arguments:
        parent: Parent window
        message: Message to be displayed to user
        title: Dialog title text
        message_type: question/info/warning/error
    Returns:
        Returns response of dialog.
    '''
    message_type_dict = {'question': Gtk.MessageType.QUESTION,
                         'info': Gtk.MessageType.INFO,
                         'warning': Gtk.MessageType.WARNING,
                         'error': Gtk.MessageType.ERROR}
    buttons_type_dict = {'question': Gtk.ButtonsType.YES_NO,
                         'info': Gtk.ButtonsType.OK,
                         'warning': Gtk.ButtonsType.OK,
                         'error': Gtk.ButtonsType.OK}
    dialogWindow = Gtk.MessageDialog(parent,
                                     Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                     message_type_dict[message_type],
                                     buttons_type_dict[message_type],
                                     message)

    dialogWindow.set_transient_for(parent)
    dialogWindow.set_title(title)
    dialogWindow.set_default_response(Gtk.ResponseType.OK)

    dialogBox = dialogWindow.get_content_area()
    userlabel = Gtk.Label(title)
    dialogBox.pack_end(userlabel, False, False, 0)

    dialogWindow.show_all()
    response = dialogWindow.run()
    dialogWindow.destroy()
    if response == Gtk.ResponseType.OK:
        return True
    else:
        return False

def get_user_input_text(parent, message, title='', oldval=None, multiline=False):
    '''Gets a single user input by diplaying a dialog box
    
    Arguments:
        parent: Parent window
        message: Message to be displayed to user
        title: Dialog title text
        multiline: Allows multiline input is True
    Returns:
        Returns user input as a string or 'None' if user does not input text.
    '''
    dialogWindow = Gtk.MessageDialog(parent,
                                     Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                     Gtk.MessageType.QUESTION,
                                     Gtk.ButtonsType.OK_CANCEL,
                                     message)

    dialogWindow.set_transient_for(parent)
    dialogWindow.set_title(title)
    dialogWindow.set_default_response(Gtk.ResponseType.OK)

    dialogBox = dialogWindow.get_content_area()
    text = ''
    
    if multiline:
        # Function to mark first line as bold
        def mark_heading(textbuff, tag):
            start = textbuff.get_start_iter()
            end = textbuff.get_end_iter()
            textbuff.remove_all_tags(start, end)
            match = start.forward_search('\n', 0, end)
            if match != None:
                match_start, match_end = match
                textbuff.apply_tag(tag, start, match_start)

        scrolledwindow = Gtk.ScrolledWindow()
        scrolledwindow.set_hexpand(True)
        scrolledwindow.set_vexpand(True)
        scrolledwindow.set_size_request(300, 100)

        textview = Gtk.TextView()
        textbuffer = textview.get_buffer()
        dialogBox.pack_end(scrolledwindow, False, False, 0)
        scrolledwindow.add(textview)
        
        # Set old value
        if oldval != None:
            textbuffer.set_text(oldval)
        
        # Mark heading
        tag_bold = textbuffer.create_tag("bold", weight=Pango.Weight.BOLD)
        mark_heading(textbuffer, tag_bold)
        textbuffer.connect("changed", mark_heading, tag_bold)

        dialogWindow.show_all()
        response = dialogWindow.run()
        text = textbuffer.get_text(textbuffer.get_start_iter(),textbuffer.get_end_iter(), True)
    else:
        userEntry = Gtk.Entry()
        userEntry.set_activates_default(True)
        userEntry.set_size_request(50, 0)
        dialogBox.pack_end(userEntry, False, False, 0)
        
        # Set old value
        if oldval != None:
            userEntry.set_text(oldval)

        dialogWindow.show_all()
        response = dialogWindow.run()
        text = userEntry.get_text()
    dialogWindow.destroy()
    if (response == Gtk.ResponseType.OK) and (text != ''):
        return text
    else:
        return None
    
def set_widget_font(widget, fontname, fontsize=None):
    context = widget.get_pango_context() 
    font = context.get_font_description()
    font.set_family(fontname)
    if fontsize:
        font.set_size(fontsize * Pango.SCALE)
    context.set_font_description(font)
    
def font_str_parse(string):
    pango_font = Pango.FontDescription.from_string(string)
    family = pango_font.get_family().lower()
    size = pango_font.get_size()/Pango.SCALE
    return (family, size)

def font_str_encode(family, size):
    pango_font = Pango.FontDescription()
    pango_font.set_family(family)
    pango_font.set_family(size)
    string = pango_font.to_string()
    return string

def get_image_from_path(path, height=None, inverted=False, mode='image'):
            
    def draw_pixel(pixels, x, y, rgba, width, height):
        # make sure pixel data is reasonable
        x = min(x, width)
        y = min(y, height)
        r = min(rgba[0], 255)
        g = min(rgba[1], 255)
        b = min(rgba[2], 255)
        a = min(rgba[3], 255)
        # insert pixel data at right location in bytes array
        i = y*width + x
        pixels[i*4 + 0] = r
        pixels[i*4 + 1] = g
        pixels[i*4 + 2] = b
        pixels[i*4 + 3] = a
    if height:
        img = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, -1, 400,True)
    else:
        img = GdkPixbuf.Pixbuf.new_from_file(path)
    if inverted:
        pixels = bytearray(img.get_pixels())
        width = img.props.width
        height = img.props.height
        for row_num, row in enumerate(zip(*(iter(img.get_pixels()),) *img.get_rowstride())):
            for col_num, pixel in enumerate(zip(*(iter(row),) * 4)):
                r, g, b, a = pixel
                draw_pixel(pixels, col_num, row_num, [255-r, 255-g, 255-b, a], width, height)
        img_new = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes(pixels), GdkPixbuf.Colorspace.RGB, True, 8,
                                                width, height, img.get_rowstride())
    else:
        img_new = img
    if mode == 'pixbuf':
        return img_new
    elif mode == 'image':
        icon = Gtk.Image()
        icon.set_from_pixbuf(img_new)
        return icon

