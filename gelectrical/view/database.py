#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# drawing
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

import logging, csv, json
from gi.repository import Gtk, Gdk, GLib
import numpy as np

# local files import
from .. import misc
from ..misc import undoable, group

# Get logger object
log = logging.getLogger(__name__)


class DatabaseView:
    """Class for loading database from file into FieldView"""
    
    def __init__(self, window, button, stack=None, field_view=None, fields=None, fields_updated_callback=None):
        self.window = window
        self.button = button
        self.stack = stack
        self.data_path = None
        self.field_view = field_view
        self.fields = fields
        self.fields_updated_callback = fields_updated_callback
        self.data = dict()

        # Setup Widgets
        self.dialog_window = Gtk.Dialog("Select database item...", self.window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.dialog_window.set_resizable(True)
        self.dialog_window.set_default_size(int(misc.WINDOW_WIDTH*0.5),int(misc.WINDOW_HEIGHT*0.7))
        self.dialog_window.set_default_response(Gtk.ResponseType.OK)

        # Pack Dialog
        content_area = self.dialog_window.get_content_area()
        action_area = self.dialog_window.get_action_area()
        scrolled_window = Gtk.ScrolledWindow()
        action_area.props.margin_top = 12
        action_area.props.margin_bottom = 6
        action_area.props.margin_left = 6
        action_area.props.margin_right = 6
        
        # Setup Treeview
        self.store = Gtk.TreeStore(str, str)
        self.filter = self.store.filter_new()
        self.filter.set_visible_func(self.filter_func, data=[0,1])

        self.search_field = Gtk.SearchEntry()
        self.search_field.set_width_chars(30)
        self.search_bar = Gtk.SearchBar()
        self.search_bar.set_show_close_button(True)
        scrolled = Gtk.ScrolledWindow()
        self.tree = Gtk.TreeView(self.filter)

        self.tree.set_grid_lines(Gtk.TreeViewGridLines.BOTH)
        self.tree.set_enable_tree_lines(True)
        self.tree.set_search_equal_func(self.equal_func, [0,1])
        self.tree.set_show_expanders(True)
        self.tree.set_level_indentation(30)
        self.tree.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self.tree.props.activate_on_single_click = False
        
        self.tree.connect("button-press-event", self.on_click_event)
        self.tree.connect("key-press-event", self.on_key_press_treeview, self.tree)
        self.search_field.connect("search-changed", self.on_search)
        self.button.connect("clicked", self.run_dialog)
        
        # Pack Widgets
        self.search_bar.add(self.search_field)
        content_area.pack_start(self.search_bar, False, False, 0)
        content_area.pack_start(scrolled, True, True, 0)
        scrolled.add(self.tree)
        column = Gtk.TreeViewColumn('')            
        cell = Gtk.CellRendererText()   
        self.tree.append_column(column)
        column.pack_start(cell, True)
        column.set_expand(True)
        column.add_attribute(cell, "text", 0)
                
    def update_from_database(self, data_path):
        """Display dialog box and get selected item
        
            Returns:
                Selected row on Ok
                None on Cancel
        """
        if data_path:
            self.data_path = data_path
            self.data = dict()
            self.button.props.sensitive = True
            
            # Load Data
            with open(data_path) as csv_file:
                csv_reader = csv.DictReader(csv_file, delimiter=';')
                for row in csv_reader:
                    item_name = row['item_name']
                    item_category = row['item_category']
                    if item_category in self.data:
                        category_dict = self.data[item_category]
                    else:
                        category_dict = dict()
                        self.data[item_category] = category_dict
                    row.pop('item_category')
                    row.pop('item_name')
                    category_dict[item_name] = row
                    
            self.store.clear()
            # Populate data
            for category, element_dict in self.data.items():
                category_iter = self.store.append(None, [category, category])
                for element in element_dict:
                    item_iter = self.store.append(category_iter, [element, category])
            if len(self.data) == 1:
                self.tree.expand_all()
        else:
            self.data_path = None
            self.data = dict()
            self.button.props.sensitive = False  
    
    def run_dialog(self, button):
        if self.data_path:
            # Run dialog
            self.dialog_window.show_all()
            self.search_bar.set_search_mode(True)
            response = self.dialog_window.run()
            
            if response == Gtk.ResponseType.OK:
                # Get selection
                selection = self.tree.get_selection()
                if selection.count_selected_rows() != 0: # if selection exists
                    [model, paths] = selection.get_selected_rows()
                    item_iter = paths[-1]
                    item_name = self.filter[item_iter][0]
                    item_category = self.filter[item_iter][1]
                    if item_name != item_category:
                        item = self.data[item_category][item_name]
                        validated_dict = dict()
                        for code, value in item.items():
                            if self.field_view:
                                data_type = self.field_view.fields[code]['type']
                            else:
                                data_type = self.fields[code]['type']

                            if data_type == 'int':
                                try:
                                    validated = int(value)
                                except:
                                    validated = 0
                            elif data_type == 'float':
                                try:
                                    validated = float(value)
                                except:
                                    validated = 0
                            elif data_type == 'bool':
                                try:
                                    validated = bool(value)
                                except:
                                    validated = False
                            elif data_type == 'graph':
                                try:
                                    dirname = misc.dir_from_path(self.data_path)
                                    valuepath = misc.posix_path(dirname, value)
                                    with open(valuepath, 'r') as fileobj:
                                        data = json.load(fileobj)
                                        validated = data
                                except:
                                    validated = None
                                    log.exception('run_dialog - validation failure while reading graph field')
                            elif data_type == 'data':
                                try:
                                    if value:
                                        (subdir, data_filename, params_filename) = eval(value)
                                        dirname = misc.dir_from_path(self.data_path)
                                        valuepath_params = misc.posix_path(dirname, subdir, params_filename)
                                        with open(valuepath_params, 'r') as fp:
                                            data_struct = json.load(fp)
                                        validated = data_struct
                                        if data_filename:
                                            valuepath = misc.posix_path(dirname, subdir, data_filename)
                                            data = np.loadtxt(valuepath, delimiter=',')
                                            curve_u = []
                                            curve_l = []
                                            for row in data:
                                                curve_u.append(('point', str(row[0])+'*f.In', str(row[1])))
                                                curve_l.append(('point', str(row[2])+'*f.In', str(row[3])))
                                            validated['data']['curve_u'] = curve_u
                                            validated['data']['curve_l'] = curve_l
                                    else:
                                        validated = None
                                except:
                                    validated = None
                                    log.exception('run_dialog - validation failure while reading data field')
                            else:
                                validated = value
                            validated_dict[code] = validated

                        if self.stack:
                            with group(self, 'Update data from database'):  # For grouping undo
                                for code, validated in validated_dict.items():
                                    if self.field_view:
                                        self.field_view.set_field(code, validated)
                                    else:
                                        self.fields[code]['value'] = validated
                        else:
                            for code, validated in validated_dict.items():
                                if self.field_view:
                                    self.field_view.set_field(code, validated)
                                else:
                                    self.fields[code]['value'] = validated

                        if self.field_view:
                            self.field_view.update_widgets()
                        else:
                            self.fields_updated_callback()

                self.dialog_window.hide()
            else:
                self.dialog_window.hide()
        
    # Callbacks
    
    def equal_func(self, model, column, key, iterator, cols):
        """Equal function for interactive search"""
        search_string = ''
        for col in cols:
            search_string += ' ' + model[iterator][col].lower()
        for word in key.split():
            if word.lower() not in search_string:
                return True
        return False

    def filter_func(self, model, model_iter, cols):
        """Searches in treestore"""
        
        def check_key(key, model_iter):
            if key is None or key == "":
                return True
            else:
                search_string = ''
                for col in cols:
                    if model[model_iter][col] is not None:
                        search_string += ' ' + model[model_iter][col].lower()
                for word in key.split():
                    if word.lower() not in search_string:
                        return False
                return True

        def search_children(key, model_iter):
            cur_iter = model.iter_children(model_iter)
            while cur_iter:
                if check_key(key, cur_iter) == True:
                    return True
                else:
                    code = search_children(key, cur_iter)
                    if code == True:
                        return True
                cur_iter = model.iter_next(cur_iter)
            return False

        key = self.search_field.get_text()
        # Check item
        if check_key(key, model_iter) == True:
            return True
        # Check children
        else:
            return search_children(key, model_iter)
    
    def on_search(self, entry):
        # Refilter model
        self.filter.refilter()
        # Expand all expanders
        self.tree.expand_all()
        
    def on_click_event(self, button, event):
        """Select item on double click"""
        # Grab focus
        self.tree.grab_focus()
        # Handle double clicks
        if event.type == Gdk.EventType._2BUTTON_PRESS:
            self.select_action()

    def on_key_press_treeview(self, widget, event, treeview):
        """Handle keypress event"""
        keyname = event.get_keyval()[1]
        state = event.get_state()
        shift_pressed = bool(state & Gdk.ModifierType.SHIFT_MASK)
        control_pressed = bool(state & Gdk.ModifierType.CONTROL_MASK)
                
        # Key Board events
        if keyname in [Gdk.KEY_Escape]:  # Unselect all
            self.tree.get_selection().unselect_all()
            return
        
        if keyname in [Gdk.KEY_Return, Gdk.KEY_KP_Enter]:  # Select element
            if control_pressed:
                self.select_action_alt()
            else:
                self.select_action()
            return
        
        if keyname == Gdk.KEY_f and control_pressed:  # Search keycode
            self.search_bar.set_search_mode(True)
            return
                                
    def select_action(self):
        self.dialog_window.response(Gtk.ResponseType.OK)
        
    def select_action_alt(self):
        pass
