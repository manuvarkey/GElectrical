#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
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
#

import pickle, codecs, os.path, copy, logging

from gi.repository import Gtk, Gdk, GLib, Pango

# local files import
from .. import misc

# Setup logger object
log = logging.getLogger(__name__)

  
class AnalysisSettingsDialog:
    
    def __init__(self, parent, library_dir):

        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "analysissettings.glade"))
        self.dialog = self.builder.get_object("settings_dialog")
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.builder.connect_signals(self)
        
        # Get objects
        self.switch_diagnostics = self.builder.get_object('switch_diagnostics')
        self.switch_powerflow = self.builder.get_object('switch_powerflow')
        self.switch_sc_sym = self.builder.get_object('switch_sc_sym')
        self.switch_sc_gf = self.builder.get_object('switch_sc_gf')
        self.switch_export = self.builder.get_object('switch_export')
        self.filechooser_export = self.builder.get_object('filechooser_export')
        
        # Set existing values
        if library_dir:
            self.filechooser_export.set_current_folder(library_dir)
        
    def run(self):
        # Show settings dialog
        response = self.dialog.run()
        
        if response == 1:
            # Set settings
            settings = dict()
            settings['diagnostics'] = self.switch_diagnostics.get_state()
            settings['powerflow'] = self.switch_powerflow.get_state()
            settings['sc_sym'] = self.switch_sc_sym.get_state()
            settings['sc_gf'] = self.switch_sc_gf.get_state()
            settings['export'] = self.switch_export.get_state()
            folder = self.filechooser_export.get_file()
            if folder:
                settings['folder'] = folder.get_path()
            else:
                settings['folder'] = None
            self.dialog.destroy()
            return settings
            
        self.dialog.destroy()
    
    def export_toggle(self, switch, gparam):
        if switch.get_state() == True:
            self.filechooser_export.set_sensitive(True)
        else:
            self.filechooser_export.set_sensitive(False)
            
