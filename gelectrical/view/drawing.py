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
    
    def __init__(self, window, box, drawing_model, program_state, program_settings, properties_view, results_view, database_view, whitelist=None):
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
        self.whitelist = whitelist
        self.scale = 1.6
        
        self.select_x = 0
        self.select_y = 0
        self.x = 0
        self.y = 0
        self.on_end_callback = None
        self.hadjustment = 0
        self.vadjustment = 0
        
        self.dirty_draw = True  # Flag to keep track of whether a drawing is to be fully redrawn
        self.highlighted_port = None  # Flag to keep track of the currently highlighted port
        self.savepoint = None  # Undo stack save point
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
        
        if mode == misc.MODE_DEFAULT:
            self.program_state['mode'] = misc.MODE_DEFAULT
            if self.on_end_callback:
                self.on_end_callback()
            self.drawing_area.get_window().set_cursor(None)
            
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
        
        self.grab_keyboard_focus()
        self.refresh()
            
    def get_mode(self):
        return self.program_state['mode']
    
    def save_scroll_position(self):
        self.hadjustment = self.scrolled_window.get_hadjustment().get_value()
        self.vadjustment = self.scrolled_window.get_vadjustment().get_value()
        
    def restore_scroll_position(self):
        self.scrolled_window.get_hadjustment().set_value(self.hadjustment)
        self.scrolled_window.get_vadjustment().set_value(self.vadjustment)

    def grab_keyboard_focus(self):
        self.save_scroll_position()
        self.drawing_area.grab_focus()
        self.restore_scroll_position()
    
    def refresh(self, redraw=False):
        if 'zoom_display_label' in self.program_state:
            self.program_state['zoom_display_label'].set_label(
                str(int(self.scale*100)) + '%')
        if redraw:
            self.dirty_draw = True
        self.drawing_area.queue_draw()
    
    def select_page(self):
        def get_page_field(*data):
            return self.drawing_model.get_page_field(*data)
        def update_page_field(*data):
            self.drawing_model.update_page_field(*data)
            self.refresh() 
        if self.properties_view:
            self.properties_view.update(self.drawing_model.fields, 'Sheet Properties', get_page_field, update_page_field)  # Update properties
        if self.database_view:
            self.database_view.update_from_database(None)
        self.drawing_model.update_elements()
        self.refresh(redraw=True)
        
    def select_elements(self, elements):
        if len(elements) == 1:
            element = elements[0]
            
            def set_text_field(*data):
                element.set_text_field_value(*data)
                self.refresh() 
                
            # Element specific items
            if element.code in misc.LOADPROFILE_CODES:
                element.fields['load_profile']['selection_list'] = self.drawing_model.parent.loadprofiles
            
            set_text_field = misc.get_undoable_set_field(self.program_state['stack'], self.refresh, element)

            def select_action():
                if self.properties_view:
                    self.properties_view.update(element.fields, element.name, element.get_text_field, set_text_field)  # Update properties
                if self.results_view:
                    self.results_view.update(element.res_fields, element.name, element.get_res_field, None)  # Update results
                if self.database_view:
                    self.database_view.update_from_database(element.database_path)
            GLib.timeout_add(200, select_action)

        elif elements and elements[0].code != 'element_wire':
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
                    if element.code in misc.LOADPROFILE_CODES:
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

                set_text_fields = misc.get_undoable_set_field_multiple(self.program_state['stack'], self.refresh, elements, self.multiselect_fields)
                
                def select_action():
                    if self.properties_view:
                        self.properties_view.update(self.multiselect_fields, elements[0].name + ' (Mutliple)', get_field, set_text_fields)  # Update properties
                    if self.database_view:
                        self.database_view.update_from_database(elements[0].database_path)
                    if self.results_view:
                        self.results_view.clean()
                GLib.timeout_add(200, select_action)
            
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

        # Check status of stack and set dirty flag
        # Handle case with stack
        if self.program_state['stack']:
            savepoint = self.program_state['stack'].undocount()
            if self.savepoint is None or self.savepoint != savepoint:
                self.dirty_draw = True
            self.savepoint = savepoint
        # Handle case with no stack
        else:
            if self.savepoint is None:
                self.dirty_draw = True
                self.savepoint = -1

        # Draw base layer
        if self.dirty_draw:
            # Set background
            self.background_surface = screen.create_similar(cairo.Content.COLOR_ALPHA, 
                                                         int(self.drawing_model.fields['page_width']['value']*self.scale), 
                                                         int(self.drawing_model.fields['page_height']['value']*self.scale))
            self.background_context = cairo.Context(self.background_surface)
            self.background_context.scale(self.scale, self.scale)
            self.drawing_model.draw_gridlines(self.background_context)
            self.drawing_model.draw_model(self.background_context, select=True, whitelist=self.whitelist)
            # Reset flags
            self.dirty_draw = False

        # Draw background image
        draw_background()

        if self.get_mode() == misc.MODE_DEFAULT:
            pass

        elif self.get_mode() == misc.MODE_SELECTION:
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
            self.drawing_model.draw_floating_model(context, self.x, self.y, grid_constraint=True)
            
        elif self.get_mode() == misc.MODE_ADD_WIRE:
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

    def on_button_press(self, w, e):
        """Handle button press events"""
        
        if (e.type == Gdk.EventType.BUTTON_PRESS \
            and e.button == MouseButtons.MIDDLE_BUTTON) \
            or e.type == Gdk.EventType._2BUTTON_PRESS :
            
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
            else:
                self.set_mode(misc.MODE_DEFAULT)
                    
        elif e.type == Gdk.EventType.BUTTON_PRESS \
            and e.button == MouseButtons.LEFT_BUTTON:
            
            if self.get_mode() == misc.MODE_DEFAULT:
                selected_initial = self.drawing_model.get_selected()
                if not(e.state & Gdk.ModifierType.SHIFT_MASK):  # If shift not pressed, deselect all items
                    self.drawing_model.deselect_all()
                selected = self.drawing_model.update_select(x=e.x/self.scale, y=e.y/self.scale, whitelist=self.whitelist)
                selected_list = self.drawing_model.get_selected()
                if selected is False:
                    if self.properties_view:
                        self.properties_view.clean()  # Clear properties
                    if self.results_view:
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
                selected = self.drawing_model.update_select(x=x, y=y, w=w, h=h, whitelist=self.whitelist)
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

        self.grab_keyboard_focus()
        self.dirty_draw = True
                    
    def on_pointer_move(self, w, e):
        """Handle button move events"""
        if e.type == Gdk.EventType.MOTION_NOTIFY:
            self.x = e.x/self.scale
            self.y = e.y/self.scale
            if self.get_mode() in (misc.MODE_INSERT, misc.MODE_SELECTION, misc.MODE_ADD_WIRE):
                self.refresh()
            else:
                port = self.drawing_model.get_port_around_coordinate(self.x, self.y, w=misc.SELECT_PORT_RECT, h=misc.SELECT_PORT_RECT)
                if port != self.highlighted_port:
                    self.highlighted_port = port
                    self.refresh()
                
    def on_mouse_scroll(self, w, e):
        """Handle scroll events"""
        mask = e.get_state()
        control_pressed = bool(mask & Gdk.ModifierType.CONTROL_MASK)
        # Zoom in
        if control_pressed and e.direction == Gdk.ScrollDirection.UP:
            if self.scale <= 2.4:
                self.scale += 0.2
                self.refresh(redraw=True)
        # Zoom out
        elif control_pressed and e.direction == Gdk.ScrollDirection.DOWN:
            if self.scale >= 0.6:
                self.scale -= 0.2
                self.refresh(redraw=True)
                    
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
                if self.get_mode() in (misc.MODE_INSERT, misc.MODE_ADD_WIRE):
                    self.set_mode(misc.MODE_DEFAULT)  # End insertion/ wire
                    self.drawing_model.reset_floating_model()
                    self.drawing_model.reset_wire_points()
                else:
                    self.drawing_model.deselect_all()
                    self.refresh()
                
            # Delete
            elif keyname in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
                self.delete_selected()
    
    def copy_selected(self, button=None):
        """Copy selected item to clipboard"""
        elements = self.drawing_model.get_selected(assembly_info=True)
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
                    group, assembly_dict = itemlist[1]
                    self.drawing_model.add_floating_model(group, assembly_dict)
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
        if self.properties_view:
            self.properties_view.clean()  # Clear properties
        if self.results_view:
            self.results_view.clean()  # Clear properties
        self.refresh()
        log.info('DrawingView - delete_selected - Delete selected items')
        
        
class DrawingSelectionDialog:
    """Class for handling element selection from Drawing views"""
    
    def __init__(self, window, drawing_models, program_settings, title='', whitelist=None):
        self.window = window
        self.drawing_models = drawing_models
        self.program_settings = program_settings
        self.whitelist = whitelist
        self.title = title
        
        self.drawing_views = []
        self.state = dict()
        self.global_scale = 1.6
        
        # Setup GUI objects
        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "drawingselectiondialog.glade"))
        self.dialog = self.builder.get_object("selection_dialog")
        self.dialog.set_resizable(True)
        self.dialog.set_default_size(int(misc.WINDOW_WIDTH*0.9),int(misc.WINDOW_HEIGHT*0.9))
        self.label_title = self.builder.get_object("label_title")
        self.dialog.set_transient_for(self.window)
        self.builder.connect_signals(self)
        self.drawing_notebook = self.builder.get_object('drawing_notebook')
        self.label_title.set_text(self.title)
        self.program_state = {'mode': misc.MODE_DEFAULT, 'stack': None}
        for whitelist_page, drawing_model in enumerate(self.drawing_models):
            drawing_model.deselect_all()
            page = Gtk.Box()
            sheet_name = drawing_model.fields['name']['value']
            sheet_label = Gtk.Label(sheet_name)
            self.drawing_notebook.insert_page(page, sheet_label, -1)
            drawing_view = DrawingView(self.window, page, drawing_model, self.program_state, self.program_settings, 
                                       None, None, None, whitelist=self.whitelist[whitelist_page])
            drawing_view.scale = self.global_scale
            self.drawing_views.append(drawing_view)
        self.drawing_notebook.show_all()
        
    def run(self):
        # Show settings dialog
        response = self.dialog.run()
        selected_dict = dict()
        if response == 1:
            # Set settings
            for slno, drawing_model in enumerate(self.drawing_models):
                selected = drawing_model.get_selected_codes()
                selected_dict[slno] = selected
            self.dialog.destroy()
            return selected_dict
        self.dialog.destroy()
