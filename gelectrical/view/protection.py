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

import logging
from gi.repository import Gtk, Gdk, GLib

# local files import
from .. import misc
from ..model.graph import GraphModel
from .database import DatabaseView
from .graph import GraphView
from .field import FieldView

# Get logger object
log = logging.getLogger(__name__)


class ProtectionViewDialog():
    """Creates a dialog box for display of protection data models
    
        Arguments:
            parent: Parent Window
    """
    
    def __init__(self, parent, elements):
        
        # Dialog variables
        self.toplevel = parent
        self.elements = elements
        self.graph_database = {}
        self.graph_uids = []
        self.fieldviews = []
        self.element_mapping = []  # Maps element index -> prot_models/ para_fields index
        self.element_mapping_inverted = []  # Maps prot_models/ para_fields index -> element index
        self.prot_models = []
        self.l_models = []
        self.g_models = []
        self.d_models = []
        self.para_fields = {}
        self.voltages = {}
        self.max_voltage = 0
        self.changed_parameters = {}
        
        # Setup widgets
        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "protectioneditor.glade"))
        self.builder.connect_signals(self)
        self.dialog_window = self.builder.get_object("dialog_window")
        self.dialog_window.set_title('Coordination view')
        self.dialog_window.set_transient_for(self.toplevel)
        self.dialog_window.set_default_size(int(misc.WINDOW_WIDTH*0.8),int(misc.WINDOW_HEIGHT*0.8))
        self.graph_box = self.builder.get_object("graph_box")
        self.combobox_title = self.builder.get_object("combobox_title")
        self.field_notebook = self.builder.get_object("field_notebook")
        self.field_notebook.set_size_request(int(misc.WINDOW_WIDTH*0.3),-1)
        
        # Setup graphview
        xlim = misc.GRAPH_PROT_CURRENT_LIMITS 
        ylim = misc.GRAPH_PROT_TIME_LIMITS
        xlabel = 'CURRENT IN AMPERES'
        ylabel = 'TIME IN SECONDS'
        self.graph_view = GraphView(self.graph_box, xlim, ylim, xlabel=xlabel, ylabel=ylabel, inactivate=True)

        # Populate voltages
        for element in self.elements:
            if element.code in (misc.PROTECTION_ELEMENT_CODES + misc.DAMAGE_ELEMENT_CODES):
                if element.code in misc.TRAFO_ELEMENT_CODES:
                    self.voltages[element.gid] = element.fields['vn_lv_kv']['value']
                else:
                    self.voltages[element.gid] = element.res_fields['vn_kv']['value']
        self.max_voltage = max(self.voltages.values())
        
        # Populate prot_models
        for el_no, element in enumerate(self.elements):
            scale = self.voltages[element.gid]/self.max_voltage if self.max_voltage != 0 and self.voltages[element.gid] != 0 else 1
            element_ids = []
            if element.code in misc.PROTECTION_ELEMENT_CODES:
                pcurve_l = element.line_protection_model
                pcurve_g = element.ground_protection_model
                if pcurve_l:
                    self.prot_models.append(pcurve_l)
                    self.element_mapping_inverted.append(el_no)
                    curve_eval = pcurve_l.get_evaluated(element.fields, scale=scale)
                    if curve_eval:
                        model = curve_eval.get_graph_model()[1][0]
                        self.l_models.append(model)
                        element_ids.append((len(self.prot_models)-1, len(self.l_models)-1, 'pcurve_l', 0))
                    else:
                        element_ids.append((len(self.prot_models)-1, None, 'pcurve_l', 0))
                if pcurve_g:
                    self.prot_models.append(pcurve_g)
                    self.element_mapping_inverted.append(el_no)
                    curve_eval = pcurve_g.get_evaluated(element.fields, scale=scale)
                    if curve_eval:
                        model = curve_eval.get_graph_model()[1][0]
                        self.g_models.append(model)
                        element_ids.append((len(self.prot_models)-1, len(self.g_models)-1, 'pcurve_g', 0))
                    else:
                        element_ids.append((len(self.prot_models)-1, None, 'pcurve_g', 0))
            if element.code in misc.DAMAGE_ELEMENT_CODES:
                dcurve = element.damage_model
                if dcurve:
                    self.prot_models.append(dcurve)
                    self.element_mapping_inverted.append(el_no)
                    curve_eval = dcurve.get_evaluated(element.fields, scale=scale)
                    if curve_eval:
                        model1 = curve_eval.get_graph_model()[1][0]
                        model2 = curve_eval.get_graph_model()[1][1]
                        if model1:
                            self.d_models.append(model1)
                            element_ids.append((len(self.prot_models)-1, len(self.d_models)-1, 'dcurve', 0))
                        if model2:
                            self.d_models.append(model2)
                            element_ids.append((len(self.prot_models)-1, len(self.d_models)-1, 'dcurve', 1))
                    else:
                        element_ids.append((len(self.prot_models)-1, None, 'dcurve', 0))
            self.element_mapping.append(element_ids)

        # Setup fieldview and populate para_fields
        duplicate_index = 1
        for model in self.prot_models:
            title = model.title
            if title in self.para_fields:
                title += ' (' + str(duplicate_index) + ')'
                duplicate_index += 1
            fields = model.get_data_fields()
            if fields:
                def get_field_func(title):
                    def get_field(code):
                        return self.para_fields[title][code]
                    return get_field
                
                def get_set_field(title):
                    def set_field(code, value):
                        self.para_fields[title][code]['value'] = value
                        self.update_parameters(title)
                        self.update_models(title)
                        self.update_graphs()
                    return set_field
            
                listbox = Gtk.ListBox()
                listbox.props.margin_top = 6
                listbox.props.margin_start = 6
                tab_label = Gtk.Label(title)
                self.field_notebook.append_page(listbox, tab_label)
                field_view = FieldView(self.dialog_window, listbox, 
                                    'status_enable', 'status_inactivate',
                                    caption_width=misc.FIELD_DIALOG_CAPTION_WIDTH)
                field_view.update(fields, None, get_field_func(title), get_set_field(title))
                self.fieldviews.append(field_view)
            self.para_fields[title] = fields

        # Update models
        self.update_models()

        # Update combo
        self.combobox_title.remove_all()
        for graph_uid, (title, graph_model) in self.graph_database.items():
            self.combobox_title.append_text(title)
            self.graph_uids.append(graph_uid)
        self.combobox_title.set_active(0)
        
    # Callbacks
    
    def graph_database_changed(self, combo_box):
        self.update_graphs()
                    
    # Functions

    def update_parameters(self, title=None):
        if title:
            fields = self.para_fields[title]
            para_index = list(self.para_fields.keys()).index(title)
            el_index = self.element_mapping_inverted[para_index]
            for model_id, sub_model_id, el_class, g_index in self.element_mapping[el_index]:
                if model_id == para_index:
                    model = self.prot_models[para_index]
                    model.update_parameters_from_fields(fields)
                    self.changed_parameters[el_index, el_class] = fields
                    break
        else:
            for model, fields in zip(self.prot_models, self.para_fields.values()):
                model.update_parameters_from_fields(fields)
    
    def update_models(self, title=None):
        if title:  # Update elements for title
            para_index = list(self.para_fields.keys()).index(title)
            el_index = self.element_mapping_inverted[para_index]
            element = self.elements[el_index]
            model = self.prot_models[para_index]
            scale = self.voltages[element.gid]/self.max_voltage if self.max_voltage != 0 and self.voltages[element.gid] != 0 else 1
            for model_id, sub_model_id, el_class, g_index in self.element_mapping[el_index]:
                if sub_model_id is not None:
                    if el_class == 'pcurve_l':
                        sub_model_list = self.l_models
                    elif el_class == 'pcurve_g':
                        sub_model_list = self.g_models
                    elif el_class == 'dcurve':
                        sub_model_list = self.d_models
                    curve_eval = model.get_evaluated(element.fields, scale=scale)
                    if curve_eval:
                        sub_model_list[sub_model_id] = curve_eval.get_graph_model()[1][g_index]
        # Populate curves
        if self.l_models or self.d_models:
            self.graph_database['Line protection'] = ['Line protection', self.l_models+self.d_models]
        if self.g_models or self.d_models:
            self.graph_database['Ground protection'] = ['Ground protection', self.g_models+self.d_models]

    def update_graphs(self):
        index = self.combobox_title.get_active()
        self.graph_view.clear_plots()
        self.graph_view.add_plots(self.graph_database[self.graph_uids[index]][1])
                
    def run(self):
        """Display dialog box and modify graph in place
          
            Returns:
                Graph model
                None on Cancel
        """
        # Run dialog
        self.dialog_window.show_all()
        response = self.dialog_window.run()
        
        if response == Gtk.ResponseType.OK and self.graph_database:
            # Get formated text and update item_values
            self.dialog_window.destroy()
            return self.changed_parameters
        else:
            self.dialog_window.destroy()
            return None
