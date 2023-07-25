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

import logging, copy, platform
import pandas as pd
from gi.repository import Gtk, Gdk, GLib

# local files import
from .. import misc
from ..misc import undoable, group
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
    
    def __init__(self, parent, program_state, elements):
        
        # Dialog variables
        self.toplevel = parent
        self.program_state = program_state
        self.stack = program_state['stack']
        self.elements = elements

        self.graph_database = {}
        self.graph_uids = []

        self.fieldviews = []
        self.fieldviews_graph = []
        self.titles = []
        self.fields = []
        self.para_fields = []

        self.element_mapping = []  # Maps element index -> model_id, sub_model_id, el_class, g_index
        self.para_element_mapping = []  # Maps prot_models/ para_fields index -> element index, el_class
        self.field_element_mapping = []  # Maps fields index -> element index
        self.prot_models = []
        self.l_models = []
        self.g_models = []
        self.d_models = [] 
        self.n_models = []
        self.voltages = {}
        self.max_voltage = 0
        
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
        if self.voltages:
            self.max_voltage = max(self.voltages.values())
        else:
            self.max_voltage = 0.415
        
        # Populate prot_models
        for el_no, element in enumerate(self.elements):
            if element.code in (misc.PROTECTION_ELEMENT_CODES + misc.DAMAGE_ELEMENT_CODES):
                scale = self.voltages[element.gid]/self.max_voltage if self.max_voltage != 0 and self.voltages[element.gid] != 0 else 1
            else:
                scale = 1
            element_ids = []
            if element.code in misc.PROTECTION_ELEMENT_CODES:
                pcurve_l = element.line_protection_model
                pcurve_g = element.ground_protection_model
                if pcurve_l:
                    self.prot_models.append(pcurve_l)
                    self.para_element_mapping.append((el_no, 'pcurve_l'))
                    curve_eval = pcurve_l.get_evaluated(element.fields, scale=scale)
                    if curve_eval:
                        model = curve_eval.get_graph_model()[1][0]
                        self.l_models.append(model)
                        element_ids.append((len(self.prot_models)-1, len(self.l_models)-1, 'pcurve_l', 0))
                    else:
                        element_ids.append((len(self.prot_models)-1, None, 'pcurve_l', 0))
                if pcurve_g:
                    self.prot_models.append(pcurve_g)
                    self.para_element_mapping.append((el_no, 'pcurve_g'))
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
                    self.para_element_mapping.append((el_no, 'dcurve'))
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
            if element.code == 'element_display_node':
                if ('ikss_ka_3ph_min' in element.res_fields and 
                    'ikss_ka_1ph_min' in element.res_fields and 
                    'ikss_ka_3ph_max' in element.res_fields and 
                    'ikss_ka_1ph_max' in element.res_fields):
                    ref = element.fields['ref']['value']
                    i_min = min(element.res_fields['ikss_ka_3ph_min']['value'], element.res_fields['ikss_ka_1ph_min']['value'])*1000
                    i_max = max(element.res_fields['ikss_ka_3ph_max']['value'], element.res_fields['ikss_ka_1ph_max']['value'])*1000
                    model1 = {'mode':misc.GRAPH_DATATYPE_MARKER, 
                                    'title': 'If min ({}) = {:0.1f} kA'.format(ref, i_min/1000), 
                                    'xval':[i_min, i_min], 
                                    'yval':[1e-8, 1e8]}
                    model2 = {'mode':misc.GRAPH_DATATYPE_MARKER, 
                                    'title': 'If max ({}) = {:0.1f} kA'.format(ref, i_max/1000),
                                    'xval':[i_max, i_max], 
                                    'yval':[1e-8, 1e8]}
                    self.n_models.append(model1)    
                    self.n_models.append(model2)
            self.element_mapping.append(element_ids)

        # Setup fieldview and populate fields
        for prot_index, model in enumerate(self.prot_models):
            el_index, el_class = self.para_element_mapping[prot_index]
            element = self.elements[el_index]
            self.field_element_mapping.append(el_index)
            
            title = model.title
            self.titles.append(title)

            para_fields = model.get_data_fields()
            self.para_fields.append(para_fields)

            if el_class == 'pcurve_l':
                fields = copy.deepcopy({'In': element.fields['In'],  
                          'In_set': element.fields['In_set'],
                          'Isc': element.fields['Isc']})
            elif el_class == 'pcurve_g':
                fields = copy.deepcopy({'I0': element.fields['I0'],  
                          'I0_set': element.fields['I0_set'],
                          'Isc': element.fields['Isc']})
            else:
                fields = {}
            self.fields.append(fields)
            
            if para_fields:
                box = Gtk.Box(orientation= Gtk.Orientation.VERTICAL)
                tab_label = Gtk.Label(title)
                self.field_notebook.append_page(box, tab_label)

                if fields:
                    def get_field_func(prot_index):
                        def get_field(code):
                            return self.fields[prot_index][code]
                        return get_field

                    def get_set_field(el_no, prot_index):
                        def set_field(code, value):
                            self.fields[prot_index][code]['value'] = value
                            self.update_fields(el_no, prot_index)
                            self.update_models(prot_index)
                            self.update_graphs()
                        return set_field
                
                    listbox = Gtk.ListBox()
                    listbox.props.margin_top = 6
                    listbox.props.margin_start = 6
                    box.pack_start(listbox, False, True, 6)
                    field_view = FieldView(self.dialog_window, listbox, 
                                        'status_enable', 'status_inactivate',
                                        caption_width=misc.FIELD_DIALOG_CAPTION_WIDTH)
                    field_view.update(fields, None, get_field_func(prot_index), get_set_field(el_index, prot_index))
                    self.fieldviews.append(field_view)   
                
                def get_field_func_para(prot_index):
                    def get_field(code):
                        return self.para_fields[prot_index][code]
                    return get_field
                
                def get_set_field_para(prot_index):
                    def set_field(code, value):
                        self.para_fields[prot_index][code]['value'] = value
                        self.update_parameters(prot_index)
                        self.update_models(prot_index)
                        self.update_graphs()
                    return set_field
                
                listbox_parameters = Gtk.ListBox()
                listbox_parameters.props.margin_top = 6
                listbox_parameters.props.margin_start = 6
                box.pack_start(listbox_parameters, True, True, 6)
                field_view_graph = FieldView(self.dialog_window, listbox_parameters, 
                                    'status_enable', 'status_inactivate',
                                    caption_width=misc.FIELD_DIALOG_CAPTION_WIDTH)
                field_view_graph.update(para_fields, None, get_field_func_para(prot_index), get_set_field_para(prot_index))
                self.fieldviews_graph.append(field_view_graph)

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

    def export_settings(self, button):
        """Export coordination settings"""
        
        # Setup file save dialog
        dialog = Gtk.FileChooserNative.new("Save coordination settings as...", self.dialog_window,
                                               Gtk.FileChooserAction.SAVE, "Save", "Cancel")
        file_filter = Gtk.FileFilter()
        file_filter.set_name('Spreadsheet file')
        file_filter.add_pattern("*.xlsx")
        
        # Set directory from project filename (Not supported by sandbox)
        if platform.system() == 'Windows':
            if self.program_state['filename']:
                directory = misc.dir_from_path(self.program_state['filename'])
                if directory:
                    dialog.set_current_folder(directory)
        
        dialog.set_current_name('settings.xlsx')
        dialog.add_filter(file_filter)
        dialog.set_filter(file_filter)
        dialog.set_do_overwrite_confirmation(True)
        
        # Run dialog and evaluate code
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            if not filename.endswith('.xlsx'):
                filename += '.xlsx'
            dialog.destroy()
            self.export_settings_spreadsheet(filename)
            log.info('ProtectionViewDialog - export_settings - File saved as - ' + filename)
        elif response == Gtk.ResponseType.CANCEL:
            dialog.destroy()
            log.info('ProtectionViewDialog - export_settings - Cancelled')
                    
    # Functions

    def update_parameters(self, para_index):
        fields = self.para_fields[para_index]
        el_index, el_class = self.para_element_mapping[para_index]
        element = self.elements[el_index]
        set_text_field = misc.get_undoable_set_field(self.stack, None, element)
        with group(self, 'Update protection parameters - ' + element.name):
            for model_id, sub_model_id, el_class, g_index in self.element_mapping[el_index]:
                if model_id == para_index:
                    data_new = copy.deepcopy(element.fields[el_class]['value'])
                    parameters = data_new['parameters']
                    for key, field in fields.items():
                        parameters[key][2] = field['value']
                    set_text_field(el_class, data_new)
                    self.update_fields(el_index, para_index)
                    break

    def update_fields(self, el_index, prot_index):
        element = self.elements[el_index]
        set_text_field = misc.get_undoable_set_field(self.stack, None, element)
        with group(self, 'Update protection fields - ' + element.name):
            for code, field in self.fields[prot_index].items():
                set_text_field(code, field['value'])
        element.calculate_parameters()
        for model_id, sub_model_id, el_class, g_index in self.element_mapping[el_index]:
            if el_class == 'pcurve_l':
                self.prot_models[model_id] = element.line_protection_model
            elif el_class == 'pcurve_g':
                self.prot_models[model_id] = element.ground_protection_model
            elif el_class == 'dcurve':
                self.prot_models[model_id] = element.damage_model

    def update_models(self, para_index=None):
        if para_index is not None:  # Update elements for title
            el_index, el_class = self.para_element_mapping[para_index]
            element = self.elements[el_index]
            scale = self.voltages[element.gid]/self.max_voltage if self.max_voltage != 0 and self.voltages[element.gid] != 0 else 1
            for model_id, sub_model_id, el_class, g_index in self.element_mapping[el_index]:
                model = self.prot_models[model_id]
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
        # disconnection time vertical line
        disc_time = self.program_state['project_settings']['Rules Check']['max_disc_time']['value']
        disc_time_model = [{'mode':misc.GRAPH_DATATYPE_MARKER, 
                                    'title': 'Max disc. time = {} s'.format(disc_time), 
                                    'xval':[1e-8, 1e8], 
                                    'yval':[disc_time, disc_time]}]
        self.graph_database = {}
        if self.l_models or self.d_models or self.n_models:
            self.graph_database['Line protection'] = ['Line protection', self.l_models + self.d_models + disc_time_model + self.n_models]
        if self.g_models or self.d_models or self.n_models:
            self.graph_database['Ground protection'] = ['Ground protection', self.g_models + self.d_models + disc_time_model + self.n_models]

    def update_graphs(self):
        index = self.combobox_title.get_active()
        self.graph_view.clear_plots()
        self.graph_view.add_plots(self.graph_database[self.graph_uids[index]][1])

    def export_settings_spreadsheet(self, filename):
        table1 = misc.params_to_table(self.fields, self.titles)
        table2 = misc.params_to_table(self.para_fields, self.titles)
        table = pd.concat([table1, table2])
        table.to_excel(filename, index=False)
                
    def run(self):
        """Display dialog box and modify graph in place
          
            Returns:
                Graph model
                None on Cancel
        """
        # Run dialog
        self.dialog_window.show_all()
        self.dialog_window.run()
        self.dialog_window.destroy()