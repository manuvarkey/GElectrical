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

import logging, copy, pickle, codecs, bisect, json
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf
import cairo

# local files import
from .. import misc
from .graph import GraphView, GraphViewDialog

# Get logger object
log = logging.getLogger(__name__)


class FieldView:
    """Class for drawing onto Gtk.DrawingArea using cairo"""
    
    def __init__(self, window, listbox, enable_code, inactivate_code, caption_width=misc.FIELD_CAPTION_WIDTH, show_graphs=True):
        self.window = window
        self.listbox = listbox
        self.fields = None
        self.caption = None
        self.get_field = None
        self.set_field = None
        self.enable_code = enable_code
        self.inactivate_code = inactivate_code
        self.caption_width = caption_width
        self.show_graphs = show_graphs
        
        self.field_rows = []
        self.name_row = None
        self.name_widget = None
        
        # Setup listbox
        self.listbox.set_activate_on_single_click(False)
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
    def update(self, fields, caption, get_field, set_field):
        self.clean()
        self.fields = fields
        self.caption = caption
        self.get_field = get_field
        self.set_field = set_field
        
        # Add item name
        
        self.name_row = Gtk.ListBoxRow()
        if caption:
            self.name_widget = Gtk.Label('<b>' + self.caption + '</b>', xalign=0)
            self.name_widget.set_use_markup(True)
        else:
            self.name_widget = Gtk.Separator()
        self.name_row.props.margin_top = 6
        self.name_row.props.margin_bottom = 6
        self.name_row.props.margin_start = 6
        self.name_row.props.margin_end = 6
        self.name_row.add(self.name_widget)
        self.listbox.add(self.name_row)
        self.field_rows.append((self.name_row, None))
        
        # Callbacks
        def activate_callback(widget, get_field, set_field, code):
            field = get_field(code)
            text = widget.get_text()
            if field['validation_func']:
                validated = field['validation_func'](text)
            else:
                if field['type'] == 'str':
                    validated = text
                elif field['type'] == 'float':
                    try:
                        validated = round(float(eval(text)), field['decimal'])
                    except:
                        validated = 0
                elif field['type'] == 'int':
                    try:
                        validated = int(eval(text))
                    except:
                        validated = 0
            widget.set_text(str(validated))
            set_field(code, validated)  # set value
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
            if field['alter_structure'] == True:
                self.update_alter_dict_status(code)
                self.update_widgets()
            
        def activate_callback_list(widget, get_field, set_field, code):
            field = get_field(code)
            tree_iter = widget.get_active_iter()
            if tree_iter is not None:
                model = widget.get_model()
                text = model[tree_iter][0]
                if field['validation_func']:
                    validated = field['validation_func'](text)
                else:
                    if field['type'] == 'str':
                        validated = text
                    elif field['type'] == 'float':
                        try:
                            validated = round(float(eval(text)), field['decimal'])
                        except:
                            validated = 0
                    elif field['type'] == 'int':
                        try:
                            validated = int(eval(text))
                        except:
                            validated = 0
                set_field(code, validated)  # set value
                if field['alter_structure'] == True:
                    self.update_alter_dict_status(code)
                    self.update_widgets()
        
        def activate_callback_bool(widget, state, get_field, set_field, code):
            field = get_field(code)
            set_field(code, state)  # set value
            if field['alter_structure'] == True:
                self.update_alter_dict_status(code)
                self.update_widgets()
                
        def activate_callback_font(widget, get_field, set_field, code):
            field = get_field(code)
            font = widget.get_font()
            set_field(code, font)  # set value
            if field['alter_structure'] == True:
                self.update_alter_dict_status(code)
                self.update_widgets()

        def activate_callback_path(widget, get_field, set_field, code, text):
            field = get_field(code)
            if field['status_inactivate']:
                filename = field['value']
                # Copy path to clipboard
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                clipboard.set_text(text,-1) # push to clipboard
                # Launch file
                misc.open_file(filename)
                
        def activate_callback_graphtitle(widget, get_field, set_field, code):
            field = get_field(code)
            text = widget.get_text()
            set_field(code, text)  # set value
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
            if field['alter_structure'] == True:
                self.update_alter_dict_status(code)
                self.update_widgets()
                
        def activate_callback_graphlist(widget, set_field, graphview, code):
            index = widget.get_active()
            set_field(code, graphview, index)  # set value
            if field['alter_structure'] == True:
                self.update_alter_dict_status(code)
                self.update_widgets()

        def show_graph_dialog_callback(widget, title, model, xlim, ylim, xlabel, ylabel):
            # Function to show bigger graph as dialog
            parent = self.window
            graph_database = {title: (title, model)}
            dialog = GraphViewDialog(parent, 
                                    'View Graph',
                                    graph_database, 
                                    xlim, ylim, xlabel, ylabel,
                                    read_only=True)
            dialog.run()

        def edit_graph_parameters_callback(widget, set_field, code, fields):
            # Function to edit graph setttings
            parent = self.window
            dialog = FieldViewDialog(parent, 
                                    'Edit Parameters', 
                                    {'Parameters': fields}, 
                                    self.enable_code,
                                    self.inactivate_code)
            modified_fields = dialog.run()
            if modified_fields:
                data_new = copy.deepcopy(self.fields[code]['value'])
                parameters = data_new['parameters']
                misc.update_params_from_fields(parameters, modified_fields['Parameters'])
                set_field(code, data_new)
                self.update_widgets()
        
        def load_data_callback(widget, set_field, code):
            # Function to load data from file
            file_filter = Gtk.FileFilter()
            file_filter.set_name('JSON file')
            file_filter.add_pattern("*.json")
            file_filter.add_pattern("*.JSON")
            file_filter.set_name("JSON")
            # Create a filechooserdialog to open:
            # The arguments are: title of the window, parent_window, action,
            # (buttons, response)
            open_dialog = Gtk.FileChooserNative.new("Open data file", self.window,
                                                    Gtk.FileChooserAction.OPEN,
                                                    "Open", "Cancel")
            # Remote files can be selected in the file selector
            open_dialog.set_local_only(True)
            # Dialog always on top of the parent window
            open_dialog.set_modal(True)
            # Set filters
            open_dialog.set_filter(file_filter)
            
            response_id = open_dialog.run()
            # If response is "ACCEPT" (the button "Open" has been clicked)
            if response_id == Gtk.ResponseType.ACCEPT:
                try:
                    filename = open_dialog.get_filename()
                    with open(filename, 'r') as fp:
                        data_struct = json.load(fp)
                    old_data = copy.deepcopy(self.fields[code])
                    # Rough validation
                    if misc.validate_protection_data_struct(data_struct, code):
                        set_field(code, data_struct)
                        log.info("load_data_callback - Data loaded successfully")
                    else:
                        log.warning("load_data_callback - Wrong data file selected")
                        misc.display_message(self.window, 'Wrong data file selected. Data not loaded.', message_type='warning')
                except:
                    log.exception("load_data_callback - Error opening file")
                    self.fields[code] = old_data
                    misc.display_message(self.window, 'Error opening data file. Data not loaded.', message_type='error')
                self.update_widgets()
            # If response is "CANCEL" (the button "Cancel" has been clicked)
            elif response_id == Gtk.ResponseType.CANCEL:
                log.info("load_data_callback - cancelled: FileChooserAction.OPEN")
            # Destroy dialog
            open_dialog.destroy()
                            
        def changed_callback(widget):
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'dialog-error')
            
        def activate_callback_multiline(button, textbuffer, get_field, set_field, code):
            field = get_field(code)
            start, end =  textbuffer.get_bounds()
            text = textbuffer.get_text(start, end, False)
            set_field(code, text)  # set value
            button.props.image.set_from_icon_name(None, Gtk.IconSize.BUTTON)
            if field['alter_structure'] == True:
                self.update_alter_dict_status(code)
                self.update_widgets()

        def on_key_press_callback_multiline(widget, event, set_button, text_buffer, get_field, set_field, code):
            # Check for Ctrl+Enter key combination
            if event.keyval == Gdk.KEY_Return and event.state & Gdk.ModifierType.CONTROL_MASK:
                activate_callback_multiline(set_button, text_buffer, get_field, set_field, code)
                return True  # To indicate that the event has been handled and should not be propagated further
            return False
            
        def changed_callback_multiline(textbuffer, textview, button):
            button.props.image.set_from_icon_name('dialog-error', Gtk.IconSize.BUTTON)

        def show_image_tooltip_callback(combo, x, y, keyboard_mode, tooltip):
            tree_iter = combo.get_active_iter()
            if tree_iter is not None:
                model = combo.get_model()
                image_file_name = model[tree_iter][2]
                if image_file_name:
                    pixbuf =  GdkPixbuf.Pixbuf.new_from_file_at_scale(image_file_name, -1,400,True)
                    width = pixbuf.get_width()
                    pixbuf =  pixbuf.composite_color_simple(width, 400, GdkPixbuf.InterpType.NEAREST, 255, 64, 0xFFFFFF, 0xFFFFFF)
                    tooltip.set_icon(pixbuf)
                    return True
            return False
                        
        # Add fields
        for code, field in self.fields.items():
            if field[self.enable_code]:
                row = Gtk.ListBoxRow()
                row.set_tooltip_markup(field['tooltip'])
                row.props.margin_start = 6
                row.props.margin_end = 6
                data_widget = None
                # Create widgets
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                caption_widget = Gtk.Label('', xalign=0)
                caption_widget.set_markup(misc.clean_markup(field['caption']))
                caption_widget.set_use_markup(True)
                caption_widget.set_size_request(self.caption_width, -1)
                caption_widget.set_line_wrap(True)
                
                if field['type'] in ('str', 'int', 'float'):
                    
                    if field['selection_list']:
                        name_store = Gtk.ListStore(str, GdkPixbuf.Pixbuf, str)
                        data_widget = Gtk.ComboBox.new_with_model(name_store)
                        if field['selection_image_list']:
                            renderer_image = Gtk.CellRendererPixbuf()
                            data_widget.pack_start(renderer_image, False)
                            data_widget.add_attribute(renderer_image, 'pixbuf', 1)
                        renderer_text = Gtk.CellRendererText()
                        data_widget.pack_start(renderer_text, True)
                        data_widget.add_attribute(renderer_text, 'text', 0)
                        # Populate
                        for slno, text in enumerate(field['selection_list']):
                            if field['selection_image_list']:
                                image_file_name = field['selection_image_list'][slno]
                                if image_file_name:
                                    image_file_name_abs = misc.abs_path('icons', image_file_name)
                                    pixbuf =  GdkPixbuf.Pixbuf.new_from_file(image_file_name_abs)
                                else:
                                    pixbuf = None
                                    image_file_name_abs = None
                                name_store.append([str(text), pixbuf, image_file_name_abs])
                            else:
                                name_store.append([str(text), None, ''])
                        # Set value
                        if field['value'] in field['selection_list']: 
                            index = field['selection_list'].index(field['value'])
                        else:
                            index = 0
                        data_widget.set_active(index)
                        # Set callbacks
                        if field['selection_image_list']:
                            data_widget.set_has_tooltip(True)
                            data_widget.connect('query-tooltip', show_image_tooltip_callback)
                        if field[self.inactivate_code] == False:
                            data_widget.connect("changed", activate_callback_list, get_field, set_field, code)
                        else:
                            data_widget.props.sensitive = False
                    else:
                        data_widget = Gtk.Entry()
                        if field['type'] == 'float':
                            data_widget.set_text(str(round(field['value'], field['decimal'])))
                        else:
                            data_widget.set_text(str(field['value']))
                        if field['max_chars']:
                            data_widget.set_max_length(field['max_chars'])
                        if field[self.inactivate_code] == False:
                            data_widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
                            data_widget.connect("activate", activate_callback, get_field, set_field, code)
                            data_widget.connect("changed", changed_callback)
                        else:
                            data_widget.props.sensitive = False
                    
                    unit_widget = Gtk.Label(field['unit'], xalign=0)
                    unit_widget.set_size_request(misc.FIELD_UNIT_WIDTH, -1)
                    # Pack
                    hbox.pack_start(caption_widget, False, False, 0)
                    hbox.pack_start(data_widget, True, True, 0)
                    hbox.pack_start(unit_widget, False, False, 0)
                    
                elif field['type'] == 'multiline_str':
                    text_buffer = Gtk.TextBuffer()
                    text_buffer.set_text(field['value'])
                    data_widget = Gtk.TextView.new_with_buffer(text_buffer)
                    data_widget.props.editable = True
                    data_widget.props.cursor_visible = True
                    data_widget.set_size_request(-1,50)
                    set_button = Gtk.Button.new_from_icon_name(None, Gtk.IconSize.BUTTON)
                    if field[self.inactivate_code] == False:
                        data_widget.connect("key-press-event", on_key_press_callback_multiline, set_button, text_buffer, get_field, set_field, code)
                        set_button.connect("clicked", activate_callback_multiline, text_buffer, get_field, set_field, code)
                        text_buffer.connect("changed", changed_callback_multiline, data_widget, set_button)
                        # Code to overcome BUG in Gtk see https://gitlab.gnome.org/GNOME/gtk/-/issues/964   
                        data_widget.connect_after('button-press-event', lambda w,e: Gdk.EVENT_STOP)
                        data_widget.connect_after('button-release-event', lambda w,e: Gdk.EVENT_STOP)
                    else:
                        data_widget.props.sensitive = False
                        set_button.props.sensitive = False
                    # Pack
                    hbox.pack_start(caption_widget, False, False, 0)
                    hbox.pack_start(data_widget, True, True, 0)
                    hbox.pack_start(set_button, False, False, 0)
                    
                elif field['type'] == 'bool':
                    data_widget = Gtk.Switch()
                    data_widget.set_state(field['value'])
                    data_widget.set_valign(Gtk.Align.CENTER)
                    data_widget.connect("state-set", activate_callback_bool, get_field, set_field, code)
                    unit_widget = Gtk.Label(field['unit'], xalign=0)
                    unit_widget.set_size_request(misc.FIELD_UNIT_WIDTH, -1)
                    # Pack
                    hbox.pack_start(caption_widget, False, False, 0)
                    hbox.pack_start(data_widget, False, False, 0)
                    hbox.pack_start(unit_widget, False, False, 0)
                    
                elif field['type'] == 'font':
                    data_widget = Gtk.FontButton.new_with_font(field['value'])
                    data_widget.connect("font-set", activate_callback_font, get_field, set_field, code)
                    # Pack
                    hbox.pack_start(caption_widget, False, False, 0)
                    hbox.pack_start(data_widget, True, True, 0)

                elif field['type'] == 'path':
                    label = (field['value'][:20] + ' ... ' + field['value'][-20:] ) if len(field['value']) > 50 else field['value']
                    label_full = field['value']
                    data_widget = Gtk.Button.new_with_label(label)
                    data_widget.set_tooltip_text(label_full)
                    data_widget.get_children()[0].set_xalign(0)
                    data_widget.connect("clicked", activate_callback_path, get_field, set_field, code, label_full)
                    # Pack
                    hbox.pack_start(caption_widget, False, False, 0)
                    hbox.pack_start(data_widget, True, True, 0)
                    
                elif field['type'] in ('graph', 'data') and field['value'] is not None:
                    
                    # Set graph options
                    (xlim, ylim, xlabel, ylabel, graph_params) = field['graph_options']
                    
                    data_widget = Gtk.Box()

                    if self.show_graphs:
                        if field['type'] in ('graph'):
                            graphview = GraphView(data_widget, xlim, ylim, xlabel=xlabel, ylabel=ylabel,
                                            inactivate=field[self.inactivate_code], graph_params=graph_params)
                        else:
                            graphview = GraphView(data_widget, xlim, ylim, xlabel=xlabel, ylabel=ylabel,
                                            inactivate=True, graph_params=graph_params)
                    
                    if field['selection_list']:
                        title_widget = Gtk.ComboBoxText.new()
                        cur_uid = field['value']
                        # Find index and populate graph_uids
                        graph_uids = list(field['selection_list'].keys())
                        index = None
                        for slno, (graph_uid, (text, models)) in enumerate(field['selection_list'].items()):
                            if cur_uid == graph_uid:
                                index = slno
                            title_widget.append_text(str(text))
                        # If index not found reset to 0
                        if index is None:
                            index = 0
                            cur_uid = graph_uids[0]
                        
                        # Update graph
                        title_widget.set_active(index)
                        if field['type'] == 'graph':
                            title, models = self.fields[code]['selection_list'][cur_uid]
                        elif field['type'] == 'data':
                            if self.fields[code]['selection_list'][cur_uid]['graph_model']:
                                title, models = self.fields[code]['selection_list'][cur_uid]['graph_model']
                            else:
                                title = ''
                                models = []

                        def set_field_graph(code, graphview, index):
                            graph_uid = graph_uids[index]
                            (title, models) = self.fields[code]['selection_list'][graph_uid]
                            self.set_field(code, graph_uid)
                            if graphview:
                                graphview.clear_plots()
                                for model in models:
                                    graphview.add_plot(model)
                                graphview.model.title = text
                                GLib.idle_add(graphview.plot_curves)

                        if self.show_graphs:
                            graphview.clear_plots()
                            for model in models:
                                graphview.add_plot(model)
                            GLib.idle_add(graphview.plot_curves)
                            title_widget.connect("changed", activate_callback_graphlist, set_field_graph, graphview, code)
                        else:
                            title_widget.connect("changed", activate_callback_graphlist, set_field_graph, None, code)
                    else:
                        # Load graph models
                        if field['type'] == 'graph':
                            title, models = field['value']
                        elif field['type'] == 'data':
                            if field['value']['graph_model']:
                                title, models = field['value']['graph_model']
                            else:
                                title = ''
                                models = []

                        if self.show_graphs:
                            for model in models:
                                graphview.add_plot(model)
                            GLib.idle_add(graphview.plot_curves)
                        title_widget = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                        text_buffer = Gtk.TextBuffer()
                        text_buffer.set_text(title)
                        label_widget = Gtk.TextView.new_with_buffer(text_buffer)
                        label_widget.props.editable = False
                        show_graph_button = Gtk.Button.new_from_icon_name('view-fullscreen-symbolic',
                                                                            Gtk.IconSize.BUTTON)
                        show_graph_button.set_tooltip_text('Display graph')
                        show_graph_button.connect("clicked", show_graph_dialog_callback, 
                                                    title, models,
                                                    xlim, ylim, xlabel, ylabel)
                        
                        if field['type'] == 'graph':
                            if field[self.inactivate_code] == False:
                                def set_title(code, text):
                                    field = self.fields[code]
                                    field['value'][0][0] = text
                                    if self.show_graphs:
                                        graphview.model.title = text
                                edit_title_widget = Gtk.Entry()
                                edit_title_widget.set_text(title)
                                edit_title_widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, None)
                                edit_title_widget.connect("activate", activate_callback_graphtitle, get_field, set_title, code)
                                edit_title_widget.connect("changed", changed_callback)
                                title_widget.pack_start(edit_title_widget, True, True, 6)
                                title_widget.pack_start(show_graph_button, False, False, 6)
                            else:
                                title_widget.pack_start(label_widget, True, True, 6)
                                title_widget.pack_start(show_graph_button, False, False, 6)
                        elif field['type'] == 'data':
                            load_data_button = Gtk.Button.new_from_icon_name('insert-object-symbolic',
                                                                            Gtk.IconSize.BUTTON)
                            load_data_button.set_tooltip_text('Load data from file')
                            edit_button = Gtk.Button.new_from_icon_name('document-properties-symbolic',
                                                                            Gtk.IconSize.BUTTON)
                            edit_button.set_tooltip_text('Edit parameters')
                            button_box = Gtk.ButtonBox(Gtk.Orientation.HORIZONTAL)
                            title_widget.pack_start(label_widget, True, True, 6)
                            title_widget.pack_start(button_box, False, False, 6)
                            button_box.pack_start(load_data_button, False, False, 0)
                            button_box.pack_start(edit_button, False, False, 0)
                            button_box.pack_start(show_graph_button, False, False, 0)
                            button_box.set_layout(Gtk.ButtonBoxStyle.EXPAND)
                            parameters = field['value']['parameters']
                            if parameters:
                                parameter_fields = misc.get_fields_from_params(parameters)
                                edit_button.set_sensitive(True)
                                edit_button.connect("clicked", edit_graph_parameters_callback, self.set_field, code, parameter_fields)
                            else:
                                edit_button.set_sensitive(False)
                            if field[self.inactivate_code] == False:
                                load_data_button.set_sensitive(True)
                                load_data_button.connect("clicked", load_data_callback, self.set_field, code)
                            else:
                                load_data_button.set_sensitive(False)
                        
                    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    hbox_sub = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    # Pack
                    hbox_sub.pack_start(caption_widget, False, False, 0)
                    hbox_sub.pack_start(title_widget, True, True, 0)
                    vbox.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 5)
                    vbox.pack_start(hbox_sub, True, True, 0)
                    vbox.pack_start(data_widget, True, True, 0)
                    vbox.pack_start(Gtk.Separator.new(Gtk.Orientation.HORIZONTAL), False, False, 5)
                    hbox.pack_start(vbox, True, True, 0)
                
                elif field['type'] == 'heading':
                    data_widget = Gtk.Label('', xalign=0.5)
                    data_widget.set_use_markup(True)
                    data_widget.set_markup('<b>' + misc.clean_markup(field['caption']) + '</b>')
                    seperator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
                    vbox_extra = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                    vbox_extra.props.margin_top = 12
                    # Pack
                    vbox_extra.pack_start(data_widget, False, False, 0)
                    vbox_extra.pack_start(seperator, True, True, 0)
                    hbox.pack_start(vbox_extra, False, False, 0)

                # If click_to_edit_message set, hide edit option under a stack
                if field['click_to_edit_message'] is not None:
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    caption = Gtk.Label('', xalign=0)
                    caption.set_markup(field['caption'])
                    caption.set_use_markup(True)
                    caption.set_size_request(self.caption_width, -1)
                    label = Gtk.Label('', xalign=0.5)
                    label.set_use_markup(True)
                    label.set_markup(field['click_to_edit_message'])
                    reveal_button = Gtk.Button()
                    reveal_button.props.relief = Gtk.ReliefStyle.NONE 
                    reveal_button.add(label)
                    box.pack_start(caption, False, False, 0)
                    box.pack_start(reveal_button, True, True, 0)
                    
                    revealer = Gtk.Stack()
                    revealer.add_named(hbox, 'content')
                    revealer.add_named(box, 'button')
                    row.add(revealer)
                    row.show_all()
                    revealer.set_visible_child_name('button')
                    def reveal_child(button, revealer, field):
                        revealer.set_visible_child_name('content')
                        field['click_to_edit_message'] = None

                    reveal_button.connect("clicked", reveal_child, revealer, field)
                else:
                    row.add(hbox)
                self.listbox.add(row)
                self.field_rows.append((row, data_widget))
            
        self.listbox.show_all()

    def update_alter_dict_status(self, code):
        """Update fields based on alter_values_dict"""
        alter_values_dict = self.fields[code]['alter_values_dict']
        value = self.fields[code]['value']
        if alter_values_dict and value in alter_values_dict:
            alter_values_dict_cur = alter_values_dict[value]
            for set_key in alter_values_dict_cur:
                if set_key in self.fields:
                    set_value = alter_values_dict_cur[set_key]
                    if set_value is None:
                        self.fields[set_key]['status_enable'] = False
                    else:
                        self.fields[set_key]['status_enable'] = True
                        self.fields[set_key]['value'] = set_value
        
    def update_widgets(self):
        self.update(self.fields, self.caption, self.get_field, self.set_field)
        
    def clean(self):
        for (row_widget, data_widget) in self.field_rows:
             row_widget.destroy()
             

class FieldViewDialog():
    """Creates a dialog box for entry of custom data fields
    
        Arguments:
            parent: Parent Window
            fields: Field values to display
    """
    
    def __init__(self, parent, window_caption, fields_dict, status_enable, status_inactivate):
        
        # Dialog variables
        self.toplevel = parent
        self.fields_dict = copy.deepcopy(fields_dict)
        self.fieldviews = []
        self.notebook = None
        
        # Setup widgets
        self.dialog_window = Gtk.Dialog(window_caption, parent, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.dialog_window.set_title(window_caption)
        self.dialog_window.set_resizable(True)
        self.dialog_window.set_border_width(5)
        self.dialog_window.set_default_size(int(misc.WINDOW_WIDTH*0.5),int(misc.WINDOW_HEIGHT*0.8))
        self.dialog_window.set_default_response(Gtk.ResponseType.OK)

        # Pack Dialog
        content_area = self.dialog_window.get_content_area()
        action_area = self.dialog_window.get_action_area()
        
        self.notebook = Gtk.Notebook()
        self.notebook.props.show_border = True
        content_area.pack_start(self.notebook, True, True, 0)
        action_area.props.margin_top = 12
        action_area.props.margin_bottom = 6
        
        for title, fields in self.fields_dict.items():
            # Setup fieldview
            
            def get_field_func(title):
                def get_field(code):
                    return self.fields_dict[title][code]
                return get_field
            
            def get_set_field(title):
                def set_field(code, value):
                    self.fields_dict[title][code]['value'] = value
                return set_field
                
            scrolled_window = Gtk.ScrolledWindow()
            listbox = Gtk.ListBox()
            scrolled_window.add_with_viewport(listbox)
            tab_label = Gtk.Label(title)
            self.notebook.append_page(scrolled_window, tab_label)
            field_view = FieldView(self.toplevel, listbox, 
                                   'status_enable', 'status_inactivate',
                                   caption_width=misc.FIELD_DIALOG_CAPTION_WIDTH)
            field_view.update(fields, None, get_field_func(title), get_set_field(title))
            self.fieldviews.append(field_view)

    def run(self):
        """Display dialog box and modify Item Values in place
        
            Save modified values to "item_values" (item passed by reference)
            if responce is Ok. Discard modified values if response is Cancel.
            
            Returns:
                modified fields on Ok
                False on Cancel
        """
        # Run dialog
        self.dialog_window.show_all()
        response = self.dialog_window.run()
        
        if response == Gtk.ResponseType.OK:
            # Get formated text and update item_values
            self.dialog_window.destroy()
            return self.fields_dict
        else:
            self.dialog_window.destroy()
            return None
             
 
