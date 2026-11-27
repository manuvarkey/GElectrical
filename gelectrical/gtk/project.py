#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# project
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

"""GTK side of the project: drawing notebook, sheet views and dialogs.

``GtkProjectModel`` is the headless :class:`gelectrical.model.project.ProjectModel`
plus the legacy views. It subscribes to the model events (pages, tabs,
diagnostics, refresh) and opens the dialogs that the model used to open
(load profile editor, protection coordination). It keeps the attributes the
GTK code uses (``drawing_view``, ``diagnostics_view``, ``program_state``).
"""

import copy, logging

from gi.repository import Gtk, GLib

# local files import
from .. import misc
from ..core import constants
from ..core.paths import open_library
from ..model.project import ProjectModel
from .view.drawing import DrawingView
from .view.graph import GraphViewDialog
from .view.protection import ProtectionViewDialog

# Get logger object
log = logging.getLogger(__name__)


class GtkProjectModel(ProjectModel):
    """Project model with the legacy GTK views"""
    
    def __init__(self, window, program_state):
        # State variables (set before the engine adds the first page)
        self.window = window
        self.program_state = program_state
        self.drawing_notebook = program_state['drawing_notebook']
        self.properties_view = program_state['properties_view']
        self.results_view = program_state['results_view']
        self.diagnostics_view = program_state['diagnostics_view']
        self.database_view = program_state['database_view']
        self.drawing_views = []
        self.drawing_view = None
        ProjectModel.__init__(self, stack=program_state['stack'],
                              program_settings=program_state['program_settings_main'],
                              element_models=program_state['element_models'],
                              listeners=[self.on_model_event])
        self.program_settings = program_state['program_settings_main']
        self.update_program_state()
        self.tab_handler_id = self.drawing_notebook.connect("switch-page", self.on_switch_tab)
        self.drawing_notebook.connect("page_reordered", self.on_page_reordered)
        
    def update_program_state(self):
        self.program_state['project_settings_main'] = self.fields['Information']
        self.program_state['project_settings'] = self.fields
    
    ## Model events
    
    def on_model_event(self, event, **data):
        handler = getattr(self, '_on_' + event, None)
        if handler:
            handler(**data)
            
    def _on_page_added(self, slno, model):
        self.update_program_state()
        page = Gtk.Box()
        program_settings = self.program_state['program_settings_main']
        view = DrawingView(self.window, page, model, self.program_state, program_settings,
                           self.properties_view, self.results_view, self.database_view)
        if slno < len(self.drawing_views):
            self.drawing_notebook.insert_page(page, None, slno) 
            self.drawing_views.insert(slno, view)
        else:
            self.drawing_notebook.append_page(page, None)
            self.drawing_views.append(view)
        self.drawing_view = view
        self.drawing_notebook.show_all()
        self.drawing_notebook.set_tab_reorderable(page, True)
        
    def _on_page_removed(self, slno):
        self.drawing_views.pop(slno)
        page = self.drawing_notebook.get_nth_page(slno)
        self.drawing_notebook.detach_tab(page)
        
    def _on_page_moved(self, from_slno, to_slno):
        view = self.drawing_views.pop(from_slno)
        self.drawing_views.insert(to_slno, view)
        
    def _on_page_selected(self, slno, switch_tab):
        self.drawing_view = self.drawing_views[slno]
        if switch_tab:
            self.drawing_notebook.set_current_page(slno)
        self.drawing_view.select_page()
        
    def _on_page_marked(self, slno):
        page = self.drawing_notebook.get_nth_page(slno)
        sheet_name = self.drawing_models[slno].fields['name']['value']
        label = self.drawing_notebook.get_tab_label(page).get_children()[0]
        label.set_markup('<span foreground="red"><b>{}</b></span>'.format(sheet_name))
        label.set_use_markup(True)
        
    def _on_tabs_changed(self, slno):
    
        def set_label(page, sheet_name):                
            label_hbox = Gtk.Box()
            page_label = Gtk.Label(sheet_name)
            label_hbox.pack_start(page_label, True, True, 0)
            self.drawing_notebook.set_tab_label(page, label_hbox)
            label_hbox.show_all()
            
        slnos = [slno] if slno is not None else range(0, self.get_page_nos())
        for index in slnos:
            page = self.drawing_notebook.get_nth_page(index)
            if page is not None:
                set_label(page, self.drawing_models[index].fields['name']['value'])
                
    def _on_fields_changed(self, fields):
        self.update_program_state()
        
    def _on_diagnostics(self, results, select_callback):
        self.diagnostics_view.update(results, select_callback)
        
    def _on_refresh(self, redraw=False):
        if self.drawing_view:
            if redraw:
                self.drawing_view.refresh(redraw=True)
            else:
                self.drawing_view.refresh()
        
    ## Overrides adding GTK behaviour
    
    def clear_all(self):
        # Sheet switches while clearing do not go through on_switch_tab
        self.drawing_notebook.handler_block(self.tab_handler_id)
        try:
            ProjectModel.clear_all(self)
        finally:
            self.drawing_notebook.handler_unblock(self.tab_handler_id)
        
    def set_model(self, document, pages):
        self.drawing_notebook.handler_block(self.tab_handler_id)
        try:
            return ProjectModel.set_model(self, document, pages)
        finally:
            self.drawing_notebook.handler_unblock(self.tab_handler_id)
        
    ## Dialogs
    
    def edit_loadprofiles(self):
        xlim = constants.GRAPH_LOAD_TIME_LIMITS
        ylim = constants.GRAPH_LOAD_CURRENT_LIMITS
        xlabel = 'Time (Hr)'
        ylabel = 'Diversity Factor'
        database_path = open_library('load_profiles.csv')
        loadprofiles_copy = copy.deepcopy(self.loadprofiles)
        dialog = GraphViewDialog(self.window, 
                                'Edit Load Profiles',
                                loadprofiles_copy, 
                                xlim, ylim, xlabel, ylabel, 
                                 database_path=database_path)
        selected_graph, database_modified_flag = dialog.run()
        if database_modified_flag:
            self.modify_loadprofiles(loadprofiles_copy)

    def view_protection_coordination(self):
        selected_elements = self.prepare_protection_coordination()
        if selected_elements:
            dialog = ProtectionViewDialog(self.window, self.program_state, selected_elements)
            dialog.run()
        else:
            return (constants.WARNING, 'No protection elements selected.')
        
    ## Callbacks
    
    def on_switch_tab(self, notebook, page, pagenum):
        """Refresh display on switching between views"""
        log.info('ProjectModel - on_switch_tab called - ' + str(pagenum))
        self.drawing_view.save_scroll_position()
        self.set_page(pagenum, switch_tab=False)
        GLib.idle_add(self.drawing_view.restore_scroll_position)
        self.program_state['zoom_display_label'].set_label(str(int(self.drawing_view.scale*100)) + '%')

    def on_page_reordered(self, notebook, page, pagenum):
        prev_pagenum = self.page_no
        self.reorder_tab(prev_pagenum, pagenum)
        log.info('ProjectModel - on_page_reordered called - from {} to {}'.format(prev_pagenum, pagenum))
