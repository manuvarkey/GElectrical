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

ASSYM_MESSAGE = """Assymetric power power flow method do not support the following features
    1. Generator, Impedance, Shunt elements.
    2. OLTC controller for transformers.
    3. Bus diversity."""

DIV_PF_MESSAGE = """Power flow with diversity method do not support the following features
    1. Multiple source paths."""

TIMESERIES_PF_MESSAGE = """Time series power flow method do not support the following features
    1. OLTC controller for transformers."""

  
class AnalysisSettingsDialog:
    
    def __init__(self, parent, ana_settings, library_dir=None):

        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "analysissettings.glade"))
        self.dialog = self.builder.get_object("settings_dialog")
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.builder.connect_signals(self)
        self.messages = ['','']
        
        # Get objects
        self.switch_diagnostics = self.builder.get_object('switch_diagnostics')
        self.switch_3ph = self.builder.get_object('switch_3ph')
        self.switch_powerflow = self.builder.get_object('switch_powerflow')
        self.switch_sc_sym = self.builder.get_object('switch_sc_sym')
        self.switch_sc_gf = self.builder.get_object('switch_sc_gf')
        self.pf_method_combo = self.builder.get_object('pf_method_combo')
        self.switch_export = self.builder.get_object('switch_export')
        self.filechooser_export = self.builder.get_object('filechooser_export')
        self.message_label = self.builder.get_object('message_label')
        
        # Set values
        self.switch_diagnostics.set_state(ana_settings['run_diagnostics']['value'])
        self.switch_3ph.set_state(ana_settings['power_flow_3ph']['value'])
        self.switch_powerflow.set_state(ana_settings['run_powerflow']['value'])
        self.pf_method_combo.set_active_id(ana_settings['pf_method']['value'])
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
            settings['pf_method'] = self.pf_method_combo.get_active_id()
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

    def update_message(self):
        if self.messages[0] or self.messages[1]:
            message = 'Notes:\n' + (self.messages[0] + '\n' + self.messages[1]).lstrip('\n').rstrip('\n')
            self.message_label.set_label(message)
        else:
            self.message_label.set_label('')
    
    def export_toggle(self, switch, gparam):
        if switch.get_state() == True:
            self.filechooser_export.set_sensitive(True)
        else:
            self.filechooser_export.set_sensitive(False)

    def pf_toggle(self, switch, gparam):
        if switch.get_state() == True:
            self.pf_method_combo.set_sensitive(True)
        else:
            self.pf_method_combo.set_sensitive(False)
            self.messages[1] = ''
            self.update_message()
    
    def pf_type_toggle(self, switch, gparam):
        if switch.get_state() == True:
            self.messages[0] = ASSYM_MESSAGE
        else:
            self.messages[0] = ''
        self.update_message()

    def pf_method_changed(self, combo):
        pf_method = combo.get_active_id()
        if pf_method == 'Power flow':
            self.messages[1] = ''
        elif pf_method == 'Power flow with diversity':
            self.messages[1] = DIV_PF_MESSAGE
        elif pf_method == 'Time series':
            self.messages[1] = TIMESERIES_PF_MESSAGE
        self.update_message()
        