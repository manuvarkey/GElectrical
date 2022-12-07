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

import logging, copy, pickle, codecs, bisect
from gi.repository import Gtk, Gdk, GLib
import cairo

# local files import
from .. import misc

# Get logger object
log = logging.getLogger(__name__)

             
class MessageView:
    """Class for displaying messages"""
    
    def __init__(self, window, listbox):
        self.window = window
        self.listbox = listbox
        self.model = None
        self.caption = None
        
        self.field_rows = dict()
        self.name_row = None
        self.name_widget = None
        self.select_callback = None
        
        # Setup listbox
        self.listbox.set_activate_on_single_click(False)
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        
    def update(self, model, select_callback):
        """
        Format: {'Head 1': [{'message': 'Title goes here', 'type': 'error'}, data_for_callback,
                           [{'message': 'Title goes here', 'type': 'warning'}, data_for_callback],
                               ...
                           ],
                 'Head 2':     ...
                   ...
                }
        """
        self.clean()
        self.model = model
        self.select_callback = select_callback
        
        # Callbacks
        def activate_callback(list_box, row):
            (data_widget, data) = self.field_rows[row]
            self.select_callback(data)
            
        if self.select_callback:
            self.listbox.connect("row_activated", activate_callback)
                        
        # Add fields
        for heading, messages in self.model.items():
            row = Gtk.ListBoxRow()
            # Create widgets
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            data_widget = Gtk.Label('', xalign=0)
            data_widget.set_markup('<b>'+ heading + '</b>')
            data_widget.set_use_markup(True)
            data_widget.set_line_wrap(True)
            data_widget.props.margin_top = 6
            data_widget.props.margin_bottom = 6
            # Pack
            row.add(hbox)
            hbox.pack_start(data_widget, True, True, 0)
            self.listbox.add(row)
            self.field_rows[row] = (data_widget, None)
            for message in messages:
                row = Gtk.ListBoxRow()
                # Create widgets
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                hbox.props.margin_top = 6
                hbox.props.margin_bottom = 6
                data_widget = Gtk.Label('', xalign=0)
                data_widget.set_line_wrap(True)
                message_text = message[0]
                if type(message_text) is dict:
                    if message_text['type'] == 'error':
                        message_processed = "<span fgcolor='#cc0000'>" + message_text['message'] + '</span>'
                        data_widget.set_use_markup(True)
                        data_widget.set_markup(message_processed)
                    elif message_text['type'] == 'warning':
                        message_processed = "<span fgcolor='#f57900'>" + message_text['message'] + '</span>'
                        data_widget.set_use_markup(True)
                        data_widget.set_markup(message_processed)
                else:
                    message_processed = message_text
                    data_widget.set_text(message_processed)
                if self.select_callback:
                    row.set_activatable(True)
                # Pack
                row.add(hbox)
                hbox.pack_start(data_widget, True, True, 0)
                self.listbox.add(row)
                self.field_rows[row] = (data_widget, message[1])
            
        self.listbox.show_all()
        
    def clean(self):
        for row_widget in self.field_rows:
             row_widget.destroy()
