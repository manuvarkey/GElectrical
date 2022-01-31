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
from ..misc import undoable, group
from .graph import GraphView

# Get logger object
log = logging.getLogger(__name__)

class MouseButtons:
    LEFT_BUTTON = 1
    MIDDLE_BUTTON = 2
    RIGHT_BUTTON = 3


class DrawingView:
    """Class for drawing onto Gtk.DrawingArea using cairo"""
    
    def __init__(self, window, box, drawing_model, program_state, program_settings, properties_view, results_view, database_view):
        self.window = window
        self.box = box
        self.drawing_area = Gtk.DrawingArea()
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.add_with_viewport(self.drawing_area)
        self.box.pack_start(self.scrolled_window, True, True, 0)
        self.drawing_model = drawing_model
        self.program_state = program_state
        self.program_settings = program_settings
        self.properties_view = properties_view
        self.results_view = results_view
        self.database_view = database_view
        self.scale = 1.6
        
        self.select_x = 0
        self.select_y = 0
        self.x = 0
        self.y = 0
        self.on_end_callback = None
        self.hadjustment = 0
        self.vadjustment = 0
        
        self.dirty_draw = False
        self.background_surface = None
        self.background_context = None
        self.multiselect_fields = None
        
        # Setup
        self.drawing_area.set_can_focus(True)
        self.drawing_area.connect("draw", self.on_draw)
        self.drawing_area.connect("button-press-event", self.on_button_press)
        self.drawing_area.connect("motion-notify-event", self.on_pointer_move)
        self.drawing_area.connect("scroll-event", self.on_mouse_scroll)
        self.drawing_area.connect("key-press-event", self.on_key_press)
        self.drawing_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | 
                                     Gdk.EventMask.POINTER_MOTION_MASK | 
                                     Gdk.EventMask.SCROLL_MASK)
        
        # Setup page settings
        self.drawing_area.set_size_request(self.drawing_model.fields['page_width']['value'] * self.scale, 
                                           self.drawing_model.fields['page_height']['value'] * self.scale) 
        self.select_page()
        
    def set_mode(self, mode, data=None):
        
        self.drawing_area.grab_focus()  # Grab focus
        
        if mode == misc.MODE_DEFAULT:
            self.program_state['mode'] = misc.MODE_DEFAULT
            if self.on_end_callback:
                self.on_end_callback()
            self.drawing_area.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
            
        elif mode == misc.MODE_SELECTION:
            self.program_state['mode'] = misc.MODE_SELECTION
            self.drawing_area.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.CROSSHAIR))
            
        elif mode == misc.MODE_INSERT:
            self.program_state['mode'] = misc.MODE_INSERT
            if data:
                self.on_end_callback = data[0]
            self.drawing_area.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.CROSSHAIR))
            
        elif mode == misc.MODE_ADD_WIRE:
            self.program_state['mode'] = misc.MODE_ADD_WIRE
            self.drawing_model.reset_wire_points()
            self.drawing_area.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.CROSSHAIR))
            
        self.refresh()
            
    def get_mode(self):
        return self.program_state['mode']
    
    def save_scroll_position(self):
        self.hadjustment = self.scrolled_window.get_hadjustment().get_value()
        self.vadjustment = self.scrolled_window.get_vadjustment().get_value()
        
    def restore_scroll_position(self):
        self.scrolled_window.get_hadjustment().set_value(self.hadjustment)
        self.scrolled_window.get_vadjustment().set_value(self.vadjustment)
    
    def refresh(self):
        self.drawing_area.queue_draw()
        
    def select_page(self):
        def get_page_field(*data):
            return self.drawing_model.get_page_field(*data)
        def update_page_field(*data):
            self.drawing_model.update_page_field(*data)
            self.refresh() 
        self.properties_view.update(self.drawing_model.fields, 'Sheet Properties', get_page_field, update_page_field)  # Update properties
        self.database_view.update_from_database(None)
        
    def select_elements(self, elements):
        if len(elements) == 1:
            element = elements[0]
            
            def set_text_field(*data):
                element.set_text_field_value(*data)
                self.refresh() 
                
            # Element specific items
            if element.code in ('element_load', 'element_staticgenerator', 'element_async_motor'):
                element.fields['load_profile']['selection_list'] = self.drawing_model.parent.loadprofiles
            
            # Special class implementing undo for set text function
            class UndoableSetTextValue:
                def __init__(self, stack, refresh):
                    self.stack = stack
                    self.refresh = refresh
            
                @undoable
                def set_text_field_value_undo(self, code, value):
                    oldval = element.get_text_field(code)['value']
                    element.set_text_field_value(code, value)
                    self.refresh() 
                    yield "Modify '{}' '{}' element field from '{}' to '{}'".format(code, element.name, oldval, value)
                    # Undo action
                    element.set_text_field_value(code, oldval)
                    self.refresh() 
            
            set_text_field = UndoableSetTextValue(self.program_state['stack'], self.refresh).set_text_field_value_undo
            self.properties_view.update(element.fields, element.name, element.get_text_field, set_text_field)  # Update properties
            self.results_view.update(element.res_fields, element.name, element.get_res_field, None)  # Update results
            self.database_view.update_from_database(element.database_path)
        elif elements[0].code != 'element_wire':
            # Check if all items are similar
            code = elements[0].code
            for element in elements:
                if element.code != code:
                    break
            else:
                self.multiselect_fields = copy.deepcopy(elements[0].fields)
                # Filter out elements with mismatching values
                for element in elements:
                        
                    # Element specific items
                    if element.code in ('element_load', 'element_staticgenerator', 'element_async_motor'):
                        element.fields['load_profile']['selection_list'] = self.drawing_model.parent.loadprofiles
                        
                    for field_code, field in element.fields.items():
                        if field['value'] != self.multiselect_fields[field_code]['value']:
                            if field['type'] == 'str':
                                self.multiselect_fields[field_code]['value'] = ''
                            elif field['type'] in ('int', 'float'):
                                self.multiselect_fields[field_code]['value'] = 0
                            if field['type'] == 'bool':
                                self.multiselect_fields[field_code]['value'] = False
                            message = '<span foreground="{}"><i>&lt;multiple values&gt; </i></span>'.format(misc.COLOR_INACTIVE)
                            self.multiselect_fields[field_code]['click_to_edit_message'] = message
                def get_field(code):
                    return self.multiselect_fields[code]
                def set_field(*data):
                    for element in elements:
                        element.set_text_field_value(*data)
                    self.multiselect_fields[data[0]]['value'] = data[1]
                    self.refresh()
                self.properties_view.update(self.multiselect_fields, elements[0].name + ' (Mutliple)', get_field, set_field)  # Update properties
                self.database_view.update_from_database(elements[0].database_path)
                self.results_view.clean()
            
    ## Callbacks
        
    def on_draw(self, widget, context):
        """Instructions drawing the model"""
        
        def draw_background():
            if self.background_surface:
                context.save()
                context.scale(1/self.scale, 1/self.scale)
                context.set_source_surface(self.background_surface)
                context.paint()
                context.restore()
                
        screen = context.get_target()
        # Setup page settings
        self.drawing_area.set_size_request(int(self.drawing_model.fields['page_width']['value'] * self.scale), 
                                           int(self.drawing_model.fields['page_height']['value'] * self.scale)) 
                                           
        # Apply global scale
        context.scale(self.scale, self.scale)
        
        # Default mode or draw base layer
        if self.get_mode() == misc.MODE_DEFAULT or self.dirty_draw:
            # Set background
            self.background_surface = screen.create_similar(cairo.Content.COLOR_ALPHA, 
                                                         int(self.drawing_model.fields['page_width']['value']*self.scale), 
                                                         int(self.drawing_model.fields['page_height']['value']*self.scale))
            self.background_context = cairo.Context(self.background_surface)
            self.background_context.scale(self.scale, self.scale)
            self.drawing_model.draw_gridlines(self.background_context)
            self.drawing_model.draw_model(self.background_context, select=True)
            # Draw background image
            draw_background()       
            self.dirty_draw = False
            
        elif self.get_mode() == misc.MODE_SELECTION:
            # Draw background image
            draw_background()
            # Draw selection rubberband
            misc.draw_rectangle(context,
                                self.x, 
                                self.y,
                                self.select_x - self.x,
                                self.select_y - self.y,
                                color=misc.COLOR_SELECTION_BAND, 
                                line_style='dashed',
                                dash_pattern=misc.SELECT_DRAW_PATTERN,
                                stroke_width=misc.STROKE_WIDTH_SELECTION_BAND)
            
        elif self.get_mode() == misc.MODE_INSERT:
            # Draw background image
            draw_background()
            self.drawing_model.draw_floating_model(context, self.x, self.y, grid_constraint=True)
            
        elif self.get_mode() == misc.MODE_ADD_WIRE:
            # Draw background image
            draw_background()
            self.drawing_model.draw_wire(context, self.x, self.y, grid_constraint=True)
        
        # Draw rectangles around port on hovering
        port = self.drawing_model.get_port_around_coordinate(self.x, self.y, w=misc.SELECT_PORT_RECT, h=misc.SELECT_PORT_RECT)
        if port:
            # Draw port selection rectangle
            misc.draw_rectangle(context,
                                port[0] - misc.SELECT_PORT_RECT/2, 
                                port[1] - misc.SELECT_PORT_RECT/2,
                                misc.SELECT_PORT_RECT,
                                misc.SELECT_PORT_RECT,
                                color=misc.COLOR_SELECTED, 
                                stroke_width=misc.STROKE_WIDTH_SELECTED)
            self.refresh()

    def on_button_press(self, w, e):
        """Handle button press events"""
        self.drawing_area.grab_focus()  # Grab focus
        if e.type == Gdk.EventType.BUTTON_PRESS \
            and e.button == MouseButtons.MIDDLE_BUTTON:
            
            if self.get_mode() == misc.MODE_ADD_WIRE:
                # Check for any nearby port
                port = self.drawing_model.get_port_around_coordinate(self.x, self.y, w=misc.SELECT_PORT_RECT, h=misc.SELECT_PORT_RECT)
                if self.drawing_model.get_num_wire_points() > 0:
                    # Add port
                    if port:
                        self.drawing_model.make_wire_permenant(*port)
                    # Add current point
                    else:
                        self.drawing_model.make_wire_permenant(self.x, self.y)
                    self.drawing_model.reset_wire_points()
                    self.set_mode(misc.MODE_DEFAULT)  # End wire
                # Cancel
                else:
                    self.drawing_model.reset_wire_points()
                    self.set_mode(misc.MODE_DEFAULT)  # End wire
                    
        elif e.type == Gdk.EventType.BUTTON_PRESS \
            and e.button == MouseButtons.LEFT_BUTTON:
            
            if self.get_mode() == misc.MODE_DEFAULT:
                selected_initial = self.drawing_model.get_selected()
                if not(e.state & Gdk.ModifierType.SHIFT_MASK):  # If shift not pressed, deselect all items
                    self.drawing_model.deselect_all()
                selected = self.drawing_model.update_select(x=e.x/self.scale, y=e.y/self.scale)
                selected_list = self.drawing_model.get_selected()
                if selected is False:
                    self.properties_view.clean()  # Clear properties
                    self.results_view.clean()  # Clear results
                    self.select_page()
                    if selected_initial:  # If existing selection, deselect all
                        self.drawing_model.deselect_all()
                        self.refresh()
                    else:  # If no selection, start box select
                        self.select_x = self.x
                        self.select_y = self.y
                        self.set_mode(misc.MODE_SELECTION)  # Start box selection
                else:
                    self.select_elements(selected_list)
                    self.refresh()
            
            elif self.get_mode() == misc.MODE_SELECTION:
                x = min(e.x/self.scale, self.select_x)
                y = min(e.y/self.scale, self.select_y)
                w = abs(e.x/self.scale - self.select_x)
                h = abs(e.y/self.scale - self.select_y)
                selected = self.drawing_model.update_select(x=x, y=y, w=w, h=h)
                selected_list = self.drawing_model.get_selected()
                self.set_mode(misc.MODE_DEFAULT)
                if selected:
                    self.select_elements(selected_list)
                    self.refresh()
                else:
                    self.select_page()
            
            elif self.get_mode() == misc.MODE_INSERT:
                # Check for any nearby port
                port = self.drawing_model.get_port_around_coordinate(self.x, self.y, w=misc.SELECT_PORT_RECT, h=misc.SELECT_PORT_RECT)
                self.drawing_model.make_floating_model_permenant(port)
                # If shift pressed, continue insert
                if e.state & Gdk.ModifierType.SHIFT_MASK:
                    self.dirty_draw = True
                    self.refresh()
                else:
                    self.drawing_model.reset_floating_model()
                    self.set_mode(misc.MODE_DEFAULT)  # End insertion
                    
            elif self.get_mode() == misc.MODE_ADD_WIRE:
                # Check for any nearby port
                port = self.drawing_model.get_port_around_coordinate(self.x, self.y, w=misc.SELECT_PORT_RECT, h=misc.SELECT_PORT_RECT)
                if port:
                    # If first point
                    if self.drawing_model.get_num_wire_points() == 0:
                        self.drawing_model.add_wire_point(*port, grid_constraint=False)
                        self.refresh()
                    # Else end wire
                    else:
                        self.drawing_model.make_wire_permenant(*port, grid_constraint=False)
                        self.drawing_model.reset_wire_points()
                        self.set_mode(misc.MODE_DEFAULT)  # End wire
                # If not port continue wire
                else:
                    self.drawing_model.add_wire_point(self.x,self.y)
                    self.refresh()
                    
        elif e.type == Gdk.EventType.BUTTON_PRESS \
            and e.button == MouseButtons.RIGHT_BUTTON:
            if self.get_mode() in (misc.MODE_INSERT, misc.MODE_ADD_WIRE):
                self.set_mode(misc.MODE_DEFAULT)  # End insertion/ wire
                self.drawing_model.reset_floating_model()
                self.drawing_model.reset_wire_points()
                    
    def on_pointer_move(self, w, e):
        """Handle button move events"""
        if e.type == Gdk.EventType.MOTION_NOTIFY:
            self.x = e.x/self.scale
            self.y = e.y/self.scale
            if self.get_mode() in (misc.MODE_INSERT, misc.MODE_SELECTION, misc.MODE_ADD_WIRE):
                self.refresh()
                
    def on_mouse_scroll(self, w, e):
        """Handle scroll events"""
        mask = e.get_state()
        control_pressed = bool(mask & Gdk.ModifierType.CONTROL_MASK)
        # Zoom in
        if control_pressed and e.direction == Gdk.ScrollDirection.UP:
            if self.scale <= 2.4:
                self.scale += 0.2
                self.refresh()
        # Zoom out
        elif control_pressed and e.direction == Gdk.ScrollDirection.DOWN:
            if self.scale >= 0.6:
                self.scale -= 0.2
                self.refresh()
                    
    def on_key_press(self, w, e):
        """Handle key press events"""
        mask = e.get_state()
        keyname = e.get_keyval()[1]
        shift_pressed = bool(mask & Gdk.ModifierType.SHIFT_MASK)
        control_pressed = bool(mask & Gdk.ModifierType.CONTROL_MASK)
        
        if control_pressed:
            # Select all  
            if keyname in (Gdk.KEY_a, Gdk.KEY_A):
                self.drawing_model.select_all()
                self.refresh()
            # Cut
            elif keyname in (Gdk.KEY_x, Gdk.KEY_X):
                self.copy_selected()
                self.delete_selected()
            # Copy
            elif keyname in (Gdk.KEY_c, Gdk.KEY_C):
                self.copy_selected()
            # Paste
            elif keyname in (Gdk.KEY_v, Gdk.KEY_V):
                self.paste()
        else:
            # Rotate model
            if keyname in (Gdk.KEY_r, Gdk.KEY_R):
                if self.get_mode() == misc.MODE_INSERT:
                    self.drawing_model.rotate_floating_model()
                    self.refresh()
            # Cycle attachement points
            elif keyname in (Gdk.KEY_c, Gdk.KEY_C):
                if self.get_mode() == misc.MODE_INSERT:
                    self.drawing_model.modify_fm_attachment_port()
                    self.refresh()
            # Deselect all
            elif keyname == Gdk.KEY_Escape:
                self.drawing_model.deselect_all()
                self.refresh()
            # Delete
            elif keyname in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
                self.delete_selected()
    
    def copy_selected(self, button=None):
        """Copy selected item to clipboard"""
        elements = self.drawing_model.get_selected()
        if elements: # if selection exists
            test_string = "DrawingGroup"
            text = codecs.encode(pickle.dumps([test_string, elements]), "base64").decode() # dump item as text
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            clipboard.set_text(text,-1) # push to clipboard
            log.info('DrawingView - copy_selected - Items copied to clipboard')
        else:
            log.warning("DrawingView - copy_selected - No items selected to copy")

    def paste(self, button=None):
        """Paste rows from clipboard into schedule view"""
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        text = clipboard.wait_for_text() # get text from clipboard
        if text != None:
            test_string = "DrawingGroup"
            try:
                itemlist = pickle.loads(codecs.decode(text.encode(), "base64"))  # recover item from string
                if itemlist[0] == test_string:
                    group = itemlist[1]
                    self.drawing_model.add_floating_model(group)
                    self.set_mode(misc.MODE_INSERT)
                else:
                    log.warning('DrawingView - paste - No valid data in clipboard')
            except:
                log.warning('DrawingView - paste - No valid data in clipboard')
        else:
            log.warning('DrawingView - paste - No text in clipboard')
            
    def delete_selected(self, button=None):
        """Delete selected item"""
        self.drawing_model.delete_selected_rows()
        self.properties_view.clean()  # Clear properties
        self.results_view.clean()  # Clear properties
        self.refresh()
        log.info('DrawingView - delete_selected - Delete selected items')

            
class FieldView:
    """Class for drawing onto Gtk.DrawingArea using cairo"""
    
    def __init__(self, window, listbox, enable_code, inactivate_code):
        self.window = window
        self.listbox = listbox
        self.fields = None
        self.caption = None
        self.get_field = None
        self.set_field = None
        self.enable_code = enable_code
        self.inactivate_code = inactivate_code
        
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
        self.name_widget = Gtk.Label('<b>' + self.caption + '</b>', xalign=0)
        self.name_widget.set_use_markup(True)
        self.name_widget.props.margin_top = 6
        self.name_widget.props.margin_bottom = 6
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
                    widget.set_text(str(validated))
                elif field['type'] == 'int':
                    try:
                        validated = int(eval(text))
                    except:
                        validated = 0
                    widget.set_text(str(validated))
            set_field(code, validated)  # set value
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'dialog-ok')
            if field['alter_structure'] == True:
                self.update_widgets()
            
        def activate_callback_list(widget, get_field, set_field, code):
            field = get_field(code)
            text = widget.get_active_text()
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
                self.update_widgets()
        
        def activate_callback_bool(widget, state, get_field, set_field, code):
            field = get_field(code)
            set_field(code, state)  # set value
            if field['alter_structure'] == True:
                self.update_widgets()
                
        def activate_callback_graphtitle(widget, get_field, set_field, code):
            field = get_field(code)
            text = widget.get_text()
            set_field(code, text)  # set value
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'dialog-ok')
            if field['alter_structure'] == True:
                self.update_widgets()
                
        def activate_callback_graphlist(widget, set_field, graphview, code):
            index = widget.get_active()
            set_field(code, graphview, index)  # set value
            if field['alter_structure'] == True:
                self.update_widgets()
                            
        def changed_callback(widget):
            widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'dialog-cancel')
            
        def activate_callback_multiline(button, textbuffer, get_field, set_field, code):
            field = get_field(code)
            start, end =  textbuffer.get_bounds()
            text = textbuffer.get_text(start, end, False)
            set_field(code, text)  # set value
            button.props.image.set_from_icon_name('dialog-ok', Gtk.IconSize.BUTTON)
            if field['alter_structure'] == True:
                self.update_widgets()
            
        def changed_callback_multiline(textbuffer, textview, button):
            button.props.image.set_from_icon_name('dialog-cancel', Gtk.IconSize.BUTTON)
                        
        # Add fields
        for code, field in self.fields.items():
            if field[self.enable_code]:
                row = Gtk.ListBoxRow()
                data_widget = None
                # Create widgets
                hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                caption_widget = Gtk.Label('', xalign=0)
                caption_widget.set_markup(field['caption'])
                caption_widget.set_use_markup(True)
                caption_widget.set_size_request(misc.FIELD_CAPTION_WIDTH, -1)
                
                if field['type'] in ('str', 'int', 'float'):
                    
                    if field['selection_list']:
                        data_widget = Gtk.ComboBoxText.new()
                        # Populate
                        for text in field['selection_list']:
                            data_widget.append_text(str(text))
                        # Set value
                        if field['value'] in field['selection_list']: 
                            index = field['selection_list'].index(field['value'])
                        else:
                            index = 0
                        data_widget.set_active(index)
                        
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
                            data_widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'dialog-ok')
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
                    set_button = Gtk.Button.new_from_icon_name('dialog-ok', Gtk.IconSize.BUTTON)
                    if field[self.inactivate_code] == False:
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
                    
                elif field['type'] in ('bool'):
                    data_widget = Gtk.Switch()
                    data_widget.set_state(field['value'])
                    data_widget.set_valign(Gtk.Align.CENTER)
                    data_widget.connect("state-set", activate_callback_bool, get_field, set_field, code)
                    # Pack
                    hbox.pack_start(caption_widget, False, False, 0)
                    hbox.pack_start(data_widget, False, False, 0)
                    
                elif field['type'] in ('graph'):
                    data_widget = Gtk.Box()
                    (xlim, ylim, xlabel, ylabel) = field['graph_options']
                    graphview = GraphView(data_widget, xlim, ylim, xlabel=xlabel, ylabel=ylabel,
                                          inactivate=field[self.inactivate_code])
                        
                    if field['selection_list']:
                        index = field['value']
                        title_widget = Gtk.ComboBoxText.new()
                        for (text, models) in field['selection_list']:
                            title_widget.append_text(str(text))
                        title_widget.set_active(index)
                        if index < len(self.fields[code]['selection_list']):
                            (title, models) = self.fields[code]['selection_list'][index]
                        else:
                            (title, models) = self.fields[code]['selection_list'][0]
                            index = 0
                        graphview.clear_plots()
                        for model in models:
                            graphview.add_plot(model)
                        
                        def set_field(code, graphview, index):
                            self.set_field(code, index)
                            (title, models) = self.fields[code]['selection_list'][index]
                            graphview.clear_plots()
                            for model in models:
                                graphview.add_plot(model)
                            graphview.model.title = text
                            
                        title_widget.connect("changed", activate_callback_graphlist, set_field, graphview, code)
                    else:
                        (title, models) = field['value']
                        for model in models:
                            graphview.add_plot(model)
                        title_widget = Gtk.Entry()
                        title_widget.set_text(title)
                        if field[self.inactivate_code] == False:
                            def set_title(code, text):
                                field = self.fields[code]
                                field['value'][0][0] = text
                                graphview.model.title = text
                            title_widget.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'dialog-ok')
                            title_widget.connect("activate", activate_callback_graphtitle, get_field, set_title, code)
                            title_widget.connect("changed", changed_callback)
                        else:
                            title_widget.props.sensitive = False
                    vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    hbox_sub = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    # Pack
                    hbox_sub.pack_start(caption_widget, False, False, 0)
                    hbox_sub.pack_start(title_widget, True, True, 0)
                    vbox.pack_start(hbox_sub, True, True, 0)
                    vbox.pack_start(data_widget, True, True, 0)
                    hbox.pack_start(vbox, True, True, 0)
                
                # If click_to_edit_message set, hide edit option under a stack
                if field['click_to_edit_message'] is not None:
                    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
                    caption = Gtk.Label('', xalign=0)
                    caption.set_markup(field['caption'])
                    caption.set_use_markup(True)
                    caption.set_size_request(misc.FIELD_CAPTION_WIDTH, -1)
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
    
    def __init__(self, parent, window_caption, fields, status_enable, status_inactivate):
        
        # Dialog variables
        self.toplevel = parent
        self.fields = copy.deepcopy(fields)
        self.fieldview = None
        
        # Setup widgets
        self.dialog_window = Gtk.Dialog(window_caption, parent, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.dialog_window.set_title(window_caption)
        self.dialog_window.set_resizable(True)
        self.dialog_window.set_border_width(5)
        self.dialog_window.set_size_request(int(self.toplevel.get_size_request()[0]*0.6),int(self.toplevel.get_size_request()[1]*0.6))
        self.dialog_window.set_default_response(Gtk.ResponseType.OK)

        # Pack Dialog
        content_area = self.dialog_window.get_content_area()
        action_area = self.dialog_window.get_action_area()
        scrolled_window = Gtk.ScrolledWindow()
        listbox = Gtk.ListBox()
        scrolled_window.add_with_viewport(listbox)
        content_area.pack_start(scrolled_window, True, True, 0)
        action_area.props.margin_top = 12
        action_area.props.margin_bottom = 6
        
        # Setup fieldview
        def get_field(code):
            return self.fields[code]
        def set_field(code, value):
            self.fields[code]['value'] = value
        self.field_view = FieldView(self.toplevel, listbox, 'status_enable', 'status_inactivate')
        self.field_view.update(self.fields, window_caption, get_field, set_field)
        
                
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
            return self.fields
        else:
            self.dialog_window.destroy()
            return None
             
             
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
                data_widget.set_text(message[0])
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
