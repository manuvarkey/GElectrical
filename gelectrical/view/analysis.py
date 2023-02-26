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
    
    def __init__(self, parent, ana_settings, library_dir=None):

        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "analysissettings.glade"))
        self.dialog = self.builder.get_object("settings_dialog")
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.builder.connect_signals(self)
        
        # Get objects
        self.switch_diagnostics = self.builder.get_object('switch_diagnostics')
        self.switch_3ph = self.builder.get_object('switch_3ph')
        self.switch_powerflow = self.builder.get_object('switch_powerflow')
        self.switch_sc_sym = self.builder.get_object('switch_sc_sym')
        self.switch_sc_gf = self.builder.get_object('switch_sc_gf')
        self.switch_export = self.builder.get_object('switch_export')
        self.filechooser_export = self.builder.get_object('filechooser_export')
        
        # Set values
        self.switch_diagnostics.set_state(ana_settings['run_diagnostics']['value'])
        self.switch_3ph.set_state(ana_settings['power_flow_3ph']['value'])
        self.switch_powerflow.set_state(ana_settings['run_powerflow']['value'])
        self.switch_sc_sym.set_state(ana_settings['run_sc_sym']['value'])
        self.switch_sc_gf.set_state(ana_settings['run_sc_gf']['value'])
        self.switch_export.set_state(ana_settings['export_results']['value'])
        
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
            settings['3ph'] = self.switch_3ph.get_state()
            settings['powerflow'] = self.switch_powerflow.get_state()
            settings['sc_sym'] = self.switch_sc_sym.get_state()
            settings['sc_gf'] = self.switch_sc_gf.get_state()
            settings['export'] = self.switch_export.get_state()
            folder = self.filechooser_export.get_uri()
            if folder:
                settings['folder'] = misc.uri_to_file(folder)
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
            
