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

import logging, copy, pickle, codecs, bisect
from gi.repository import Gtk, Gdk, GLib
import cairo

# local files import
from .. import misc
from ..model.graph import GraphModel

from matplotlib.backends.backend_gtk3agg import (
    FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.figure import Figure

# Get logger object
log = logging.getLogger(__name__)

class MouseButtons:
    LEFT_BUTTON = 1
    MIDDLE_BUTTON = 2
    RIGHT_BUTTON = 3

       
class GraphView():
    """Class for displaying graph"""
    
    def __init__(self, box, xlim, ylim, title='', xlabel='', ylabel='', inactivate=False):
        
        self.box = box
        self.xlim = xlim
        self.ylim = ylim
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.inactivate = inactivate
        self.models = []
        self.model = None
        self.colors = ('r', 'b', 'g', 'c', 'm', 'y', 'k', 'w')
        self.signal1_id = None
        self.signal2_id = None
        
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.hbox_int = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.scrolled_window = Gtk.ScrolledWindow()
        self.figure = Figure(figsize=(1, 1))
        self.canvas = FigureCanvas(self.figure)  # a Gtk.DrawingArea
        self.box.set_size_request(100,300)
        self.name_widget = Gtk.Label('<i>' + self.title + '</i>', xalign=0.5)
        self.name_widget.set_use_markup(True)
        self.name_widget.props.margin_top = 6
        self.name_widget.props.margin_bottom = 6
        self.xlabel_widget = Gtk.Label('<i>' + self.xlabel + '</i>', xalign=0.5)
        self.xlabel_widget.set_use_markup(True)
        self.ylabel_widget = Gtk.Label('<i>' + self.ylabel + '</i>', xalign=0.5)
        self.ylabel_widget.set_use_markup(True)
        self.ylabel_widget.set_angle(90)
        self.box.pack_start(self.vbox, True, True, 0)
        if title: 
            self.vbox.pack_start(self.name_widget, False, False, 0)
        if ylabel:
            self.hbox_int.pack_start(self.ylabel_widget, False, False, 0)
        self.hbox_int.pack_start(self.scrolled_window, True, True, 0)
        self.vbox.pack_start(self.hbox_int, True, True, 0)
        if xlabel:
            self.vbox.pack_start(self.xlabel_widget, False, False, 0)
        self.scrolled_window.add(self.canvas)
        self.plot = self.figure.add_subplot(111)
        self.plot_curves()
        
    # Functions
    
    def add_plot(self, graph_model):
        self.models.append(GraphModel(graph_model))
        if len(self.models) == 1:
            self.model = self.models[0]
        self.plot_curves()
        
    def add_plots(self, graph_models):
        for model in graph_models:
            self.add_plot(model)
        
    def clear_plots(self):
        self.models.clear()
        self.model = None
        
    def set_active_model(self, index):
        if index < len(self.models):
            self.model = self.models[index]
            
    def cycle_active_graph(self):
        index = self.models.index(self.model)
        if index < len(self.models)-1:
            self.model = self.models[index+1]
        else:
            self.model = self.models[0]
            
    def plot_curves(self):
        if self.inactivate == False:
            self.signal1_id = self.box.connect('button_press_event', self.on_click_box)
            self.signal2_id = self.canvas.mpl_connect('button_press_event', self.on_click)
        else:
            if self.signal1_id:
                self.box.disconnect(self.signal1_id)
                self.signal1_id = None
            if self.signal2_id:
                self.canvas.mpl_disconnect(self.signal2_id)
                self.signal2_id = None
            
        self.plot.clear()
        for tick in self.plot.get_xticklabels():
            tick.set_fontname(misc.GRAPH_FONT_FACE)
            tick.set_fontsize(misc.GRAPH_FONT_SIZE)
        for tick in self.plot.get_yticklabels():
            tick.set_fontname(misc.GRAPH_FONT_FACE)
            tick.set_fontsize(misc.GRAPH_FONT_SIZE)
        self.plot.set_xlim(self.xlim[0], self.xlim[1])
        if len(self.xlim) == 4 and self.xlim[3] == 'log':
            self.plot.set_xscale('log')
        self.plot.set_ylim(self.ylim[0], self.ylim[1])
        self.plot.grid(True, which='major')
        self.plot.minorticks_on()
        self.plot.grid(True, which='minor', alpha=0.2)
        for slno, model in enumerate(self.models):
            color = self.colors[slno % len(self.colors)]
            self.plot.plot(model.xval, model.yval, marker="o", color=color)
        self.canvas.draw()
        
    # Callbacks
    
    def on_click_box(self, widget, event):
        self.canvas.grab_focus()
    
    def on_click(self, event):
        if self.model and event.xdata and event.ydata:
            x = round(event.xdata/self.xlim[2], 0)*self.xlim[2]
            y = round(event.ydata/self.ylim[2], 0)*self.ylim[2]
            if event.button == MouseButtons.LEFT_BUTTON:
                self.model.add_point(x, y)
            elif event.button == MouseButtons.MIDDLE_BUTTON:
                self.cycle_active_graph()
            else:
                self.model.remove_point(x, y)
            self.plot_curves()
      
            
class GraphViewDialog():
    """Creates a dialog box for entry of custom data fields
    
        Arguments:
            parent: Parent Window
            graph_database: Graph database to display
    """
    
    def __init__(self, parent, graph_database, xlim, ylim, xlabel, ylabel):
        
        # Dialog variables
        self.toplevel = parent
        self.graph_database = graph_database
        self.xlim = xlim
        self.ylim = ylim
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.temp_graph = None
        self.mode = 'DEFAULT'
        
        # Setup widgets
        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "loadprofileeditor.glade"))
        self.builder.connect_signals(self)
        self.dialog_window = self.builder.get_object("dialog_window")
        self.dialog_window.set_size_request(int(self.toplevel.get_size_request()[0]*0.6),int(self.toplevel.get_size_request()[1]*0.6))
        self.graph_box = self.builder.get_object("graph_box")
        self.combobox_title = self.builder.get_object("combobox_title")
        self.textbox_title = self.builder.get_object("textbox_title")
        self.stack_switcher = self.builder.get_object("main_stack")
        
        # Setup graphview
        self.graph_view = GraphView(self.graph_box, xlim, ylim, xlabel=xlabel, ylabel=ylabel, inactivate=True)
        
        # Populate database
        for (title, graph_model) in self.graph_database:
            self.combobox_title.append_text(title)
            
        if self.graph_database:
            self.graph_view.add_plots(self.graph_database[0][1])
            self.combobox_title.set_active(0)
        
    # Callbacks
    
    def graph_database_changed(self, combo_box):
        index = combo_box.get_active()
        self.graph_view.clear_plots()
        self.graph_view.add_plots(self.graph_database[index][1])
        
    def add_profile(self, button):
        self.temp_graph =  ['Untitled', [{'mode':misc.GRAPH_DATATYPE_PROFILE, 'title':'Default', 'xval':[], 'yval':[]}]]
        self.graph_view.clear_plots()
        self.graph_view.add_plots(self.temp_graph[1])
        self.graph_view.inactivate = False
        self.graph_view.plot_curves()
        self.textbox_title.set_text(self.temp_graph[0])
        self.stack_switcher.set_visible_child_name('edit')
        self.mode = 'ADD'
    
    def delete_profile(self, button):
        index = self.combobox_title.get_active()
        if index is not None and len(self.graph_database) > 1:
            self.graph_database.pop(index)
            self.combobox_title.remove(index)
            if index != 0:
                self.combobox_title.set_active(index-1)
                self.graph_view.clear_plots()
                self.graph_view.add_plots(self.graph_database[index-1][1])
            else:
                self.combobox_title.set_active(0)
                self.graph_view.clear_plots()
                self.graph_view.add_plots(self.graph_database[0][1])
            
    def edit_profile(self, button):
        index = self.combobox_title.get_active()
        if index is not None:
            self.temp_graph = copy.deepcopy(self.graph_database[index])
            self.graph_view.clear_plots()
            self.graph_view.add_plots(self.temp_graph[1])
            self.graph_view.inactivate = False
            self.graph_view.plot_curves()
            self.textbox_title.set_text(self.temp_graph[0])
            self.stack_switcher.set_visible_child_name('edit')
            self.mode = 'EDIT'
    
    def accept_modification(self, button):
        title = self.textbox_title.get_text()
        if self.mode == 'ADD':
            self.graph_database.append(self.temp_graph)
            index = len(self.graph_database)-1
        else:
            index = self.combobox_title.get_active()
            self.graph_database[index] = self.temp_graph
            
        self.graph_view.clear_plots()
        self.graph_view.add_plots(self.graph_database[index][1])
        self.graph_view.inactivate = True
        self.graph_view.plot_curves()
        self.graph_database[index][0] = title
        self.repopulate_combo()
        self.combobox_title.set_active(index)
        self.stack_switcher.set_visible_child_name('default')
        self.mode = 'DEFAULT'
        
    def cancel_modification(self, button):
        index = self.combobox_title.get_active()
        self.graph_view.clear_plots()
        self.graph_view.add_plots(self.graph_database[index][1])
        self.graph_view.inactivate = True
        self.graph_view.plot_curves()
        self.stack_switcher.set_visible_child_name('default')
        self.mode = 'DEFAULT'
            
    # Functions
    
    def repopulate_combo(self):
        self.combobox_title.remove_all()
        for (title, graph_model) in self.graph_database:
            self.combobox_title.append_text(title)
                
    def run(self):
        """Display dialog box and modify graph in place
          
            Returns:
                Graph model
                None on Cancel
        """
        # Run dialog
        self.dialog_window.show_all()
        response = self.dialog_window.run()
        
        if response == Gtk.ResponseType.CLOSE and self.graph_database:
            # Get formated text and update item_values
            index = self.combobox_title.get_active()
            self.dialog_window.destroy()
            return self.graph_database[index]
        else:
            self.dialog_window.destroy()
            return None
