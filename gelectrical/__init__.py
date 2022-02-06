#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# __init__
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

import os, platform, sys, queue, threading, logging, traceback, json, pickle, codecs, importlib, copy, gi
import appdirs

gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')

from gi.repository import Gtk, Gdk, GLib, Gio, GdkPixbuf

# local files import
from . import misc, undo
from .model import drawing
from .elementmodel import switch, busbar, grid, transformer, load, line, impedance, shunt, ward, generator
from .model.project import ProjectModel
from .view.field import FieldView, FieldViewDialog
from .view.message import MessageView
from .view.database import DatabaseView

# Add current path to sys for importing plugins
sys.path.append(misc.abs_path(''))

# Get logger object
log = logging.getLogger(__name__)

class MainWindow():
    """Class handles main window"""

    ## General Methods

    def display_status(self, status_code, message='', timeout=misc.MESSAGE_TIMEOUT):
        """Displays a formated message in Infobar
            
            Arguments:
                status_code: Specifies the formatting of message.
                             (Takes the values misc.ERROR,
                              misc.WARNING, misc.INFO]
                message: The message to be displayed
        """
        infobar_main = self.builder.get_object("infobar_main")
        label_infobar_main = self.builder.get_object("label_infobar_main")
        
        if status_code is not None:
            if status_code == misc.ERROR:
                infobar_main.set_message_type(Gtk.MessageType.ERROR)
                label_infobar_main.set_text(message)
                infobar_main.show()
            elif status_code == misc.WARNING:
                infobar_main.set_message_type(Gtk.MessageType.WARNING)
                label_infobar_main.set_text(message)
                infobar_main.show()
            elif status_code == misc.INFO:
                infobar_main.set_message_type(Gtk.MessageType.INFO)
                label_infobar_main.set_text(message)
                infobar_main.show()
            GLib.timeout_add_seconds(timeout, infobar_main.hide)
        else:
            infobar_main.hide()
        
    def set_title(self, title):
        self.gtk_header = self.builder.get_object("gtk_header")
        self.gtk_header.set_subtitle(title)
        
    def run_command(self, exec_func, data=None, end_timeout=5, error_timeout=20):
        """Return progress object"""
        
        # Setup progress object
        progress = misc.ProgressRevealer(parent=self.progress_revealer, 
                                        label=self.progress_label, 
                                        progress=self.progress_bar)
        
        def callback_combined(progress, data):
                
            # Run process
            progress.show()
            
            try:
                if data:
                    exec_func(progress, data)
                else:
                    exec_func(progress)
            except Exception as e:
                log.error('run_command - callback_combined - ' + repr(e))
                log.error(traceback.format_exc())
                progress.pulse(end=True)
                progress.add_message("<span font_weight='bold' fgcolor='red'>Error encounterd during process. Process terminated \n" + repr(e) + '</span>')
                GLib.timeout_add_seconds(error_timeout, progress.close)
                return
            
            # End progress
            progress.pulse(end=True)
            GLib.timeout_add_seconds(end_timeout, progress.close)
        
        # Hide display_status 
        self.display_status(None)
        # Run process in seperate thread
        que = queue.Queue()
        thread = threading.Thread(target=lambda q, arg: q.put(callback_combined(progress, data)), args=(que, 2))
        thread.daemon = True
        thread.start()
    
    def update(self):
        """Refreshes all displays"""
        log.info('MainWindow update called')
        self.project.drawing_view.set_mode(misc.MODE_DEFAULT)
        self.properties_view.clean()
        self.results_view.clean()
        self.insert_view.clean()
        
    def open_project(self, filename):
        # get filename and set project as active
        self.filename = filename
        
        with open(self.filename, 'r') as fileobj:
            try:
                data = json.load(fileobj)  # load data structure
                if data[0] == misc.PROJECT_FILE_VER:
                    self.project.set_model(data[1])

                    self.display_status(misc.INFO, "Project successfully opened")
                    log.info('MainWindow - open_project - Project successfully opened - ' +self.filename)
                    # Setup window name
                    self.window.set_title(self.filename + ' - ' + misc.PROGRAM_NAME)
                    # Clear undo/redo stack
                    self.stack.clear()
                    # Set flags
                    self.project_active = True
                    # Save point in stack for checking change state
                    self.stack.savepoint()
                    # Refresh all displays
                    self.update()
                else:
                    self.display_status(misc.ERROR, "Project could not be opened: Wrong file type selected")
                    log.warning('MainWindow - open_project - Project could not be opened: Wrong file type selected - ' +self.filename)
            except:
                log.exception("Error parsing project file - " + self.filename)
                self.display_status(misc.ERROR, "Project could not be opened: Error opening file")
                    
    ## Main Window callbacks

    def on_exit(self, *args):
        """Callback called on pressing the close button of main window"""
        
        log.info('MainWindow - on_exit called')
            
        # Ask confirmation from user
        if self.stack.haschanged():
            message = 'You have unsaved changes which will be lost if you continue.\n Are you sure you want to exit ?'
            title = 'Confirm Exit'
            dialogWindow = Gtk.MessageDialog(transient_for=self.window,
                                     modal=True,
                                     destroy_with_parent=True,
                                     message_type=Gtk.MessageType.QUESTION,
                                     buttons=Gtk.ButtonsType.YES_NO,
                                     text=message)
            dialogWindow.set_transient_for(self.window)
            dialogWindow.set_title(title)
            dialogWindow.set_default_response(Gtk.ResponseType.NO)
            dialogWindow.show_all()
            response = dialogWindow.run()
            dialogWindow.destroy()
            if response == Gtk.ResponseType.NO:
                # Do not propogate signal
                log.info('MainWindow - on_exit - Cancelled by user')
                return True

        log.info('MainWindow - on_exit - Exiting')
        return False

    def on_open(self, button):
        """Open project selected by  the user"""
        # Create a filechooserdialog to open:
        # The arguments are: title of the window, parent_window, action,
        # (buttons, response)
        if platform.system() == 'Linux':
            open_dialog = Gtk.FileChooserNative.new("Open project File", self.window,
                                                Gtk.FileChooserAction.OPEN,
                                                "Open", "Cancel")
        elif platform.system() == 'Windows':
            open_dialog = Gtk.FileChooserDialog(title="Open project File", 
                                                parent=self.window,
                                                action=Gtk.FileChooserAction.OPEN)
            open_dialog.add_buttons("Open project File", self.window,
                                                Gtk.FileChooserAction.OPEN,
                                                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))

        # Remote files can be selected in the file selector
        open_dialog.set_local_only(True)
        # Dialog always on top of the textview window
        open_dialog.set_modal(True)
        # Set filters
        open_dialog.set_filter(self.builder.get_object("filefilter_project"))
        
        response_id = open_dialog.run()
        # If response is "ACCEPT" (the button "Save" has been clicked)
        if response_id == Gtk.ResponseType.ACCEPT:
            self.open_project(open_dialog.get_filename())
        # If response is "CANCEL" (the button "Cancel" has been clicked)
        elif response_id == Gtk.ResponseType.CANCEL:
            log.info("cancelled: FileChooserAction.OPEN")
        # Destroy dialog
        open_dialog.destroy()
        # Hide fileselector
        self.builder.get_object('popup_open').hide()
    
    def on_open_project_selected(self, recent):
        uri = recent.get_current_uri()
        filename = misc.uri_to_file(uri)
        self.open_project(filename)
        window_title = self.filename
        self.set_title(window_title)
        # Hide fileselector
        self.builder.get_object('popup_open').hide()

    def on_save(self, button):
        """Save project to file already opened"""
        if self.project_active is False:
            self.on_saveas(button)
        else:
            # Parse data into object
            data = []
            data.append(misc.PROJECT_FILE_VER)
            data.append(self.project.get_model())
            # Try to open file
            with open(self.filename, 'w') as fileobj:
                try:
                    json.dump(data, fileobj)
                except:
                    log.error("MainWindow - on_save - Error opening file - " + self.filename)
                    self.display_status(misc.ERROR, "Project file could not be opened for saving")
                    return
            self.display_status(misc.INFO, "Project successfully saved")
            log.info('MainWindow - on_save -  Project successfully saved')
            self.window.set_title(self.filename + ' - ' + misc.PROGRAM_NAME)
            # Save point in stack for checking change state
            self.stack.savepoint()

    def on_saveas(self, button):
        """Save project to file selected by the user"""
        # Create a filechooserdialog to open:
        # The arguments are: title of the window, parent_window, action,
        # (buttons, response)
        if platform.system() == 'Linux':
            open_dialog = Gtk.FileChooserNative.new("Save project File", self.window,
                                                    Gtk.FileChooserAction.SAVE,
                                                    "Save", "Cancel")
        elif platform.system() == 'Windows':
            open_dialog = Gtk.FileChooserDialog("Save project as...", self.window,
                                            Gtk.FileChooserAction.SAVE,
                                            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                             Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
        # Remote files can be selected in the file selector
        open_dialog.set_local_only(False)
        # Dialog always on top of the textview window
        open_dialog.set_modal(True)
        # Set filters
        open_dialog.set_filter(self.builder.get_object("filefilter_project"))
        # Set overwrite confirmation
        open_dialog.set_do_overwrite_confirmation(True)
        # Set default name
        open_dialog.set_current_name("newproject.gepro")
        response_id = open_dialog.run()
        # If response is "ACCEPT" (the button "Save" has been clicked)
        if response_id == Gtk.ResponseType.ACCEPT:
            # Get filename and set project as active
            self.filename = open_dialog.get_filename()
            self.project_active = True
            # Call save project
            self.on_save(button)
            # Setup window name
            self.window.set_title(self.filename + ' - ' + misc.PROGRAM_NAME)
            # Save point in stack for checking change state
            self.stack.savepoint()
            
            log.info('MainWindow - on_saveas -  Project successfully saved - ' + self.filename)
        # If response is "CANCEL" (the button "Cancel" has been clicked)
        elif response_id == Gtk.ResponseType.CANCEL:
            log.info("cancelled: FileChooserAction.OPEN")
        # Destroy dialog
        open_dialog.destroy()
        
    def on_export(self, widget):
        """Export project report"""
        
        # Setup file save dialog
        if platform.system() == 'Linux':
            dialog = Gtk.FileChooserNative.new("Save project report as...", self.window,
                                               Gtk.FileChooserAction.SAVE, "Save", "Cancel")
        elif platform.system() == 'Windows':
            dialog = Gtk.FileChooserDialog("Save project report as...", self.window,
                                           Gtk.FileChooserAction.SAVE,
                                           (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                            Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT))
        file_filter = Gtk.FileFilter()
        file_filter.add_pattern("*.pdf")
        file_filter.set_name("PDF")
        
        # Set directory from project filename (Not supported by sandbox)
        if platform.system() == 'Windows':
            if self.filename:
                directory = misc.dir_from_path(self.filename)
                if directory:
                    dialog.set_current_folder(directory)
        
        dialog.set_current_name('drawing.pdf')
        dialog.add_filter(file_filter)
        dialog.set_filter(file_filter)
        dialog.set_do_overwrite_confirmation(True)
        
        # Run dialog and evaluate code
        response = dialog.run()
        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            dialog.destroy()
            self.project.export_drawing(filename)
            self.display_status(misc.INFO, "Project report exported")
            log.info('MainWindow - on_export - File saved as - ' + filename)
        elif response == Gtk.ResponseType.CANCEL:
            dialog.destroy()
            self.display_status(misc.WARNING, "Project export cancelled by user")
            log.info('MainWindow - on_export - Cancelled')
        
    def on_project_settings(self, button):
        """Display dialog to input project settings"""
        log.info('MainWindow - on_project_settings - Launch project settings')
        # Setup project settings dialog
        project_settings_dialog = FieldViewDialog(self.window, 
                                      'Project Settings',
                                       self.project.get_project_fields(full=True), 
                                      'status_enable', 'status_inactivate')
        # Show settings dialog
        fields = project_settings_dialog.run()
        if fields:
            self.project.update_project_fields(fields)
        
    def on_program_settings(self, button):
        """Display dialog to input program settings"""
        log.info('MainWindow - on_project_settings - Launch project settings')
        # Setup project settings dialog
        program_settings_dialog = FieldViewDialog(self.window, 
                                      'Program Settings',
                                       self.program_settings, 
                                      'status_enable', 'status_inactivate')
        # Show settings dialog
        fields = program_settings_dialog.run()
        if fields:
            self.program_settings.update(fields)
            with open(self.settings_filename, 'w') as fp:
                json.dump(self.program_settings, fp)
                log.info('MainWindow - on_project_settings - Program settings saved at ' + str(self.settings_filename))

    def on_infobar_close(self, widget, response=0):
        """Hides the infobar"""
        widget.hide()

    def on_redo(self, button):
        """Redo action from stack"""
        redotext = self.stack.redotext()
        if redotext == None:
            redotext = 'Nothing to Redo'
        log.info(redotext)
        self.stack.redo()
        self.update()
        self.display_status(misc.INFO, redotext)

    def on_undo(self, button):
        """Undo action from stack"""
        undotext = self.stack.undotext()
        if undotext == None:
            undotext = 'Nothing to Undo'
        log.info(undotext)
        self.stack.undo()
        self.update()
        self.display_status(misc.INFO, undotext)
        
    def on_draw_cut(self, button=None):
        """Copy selected item to clipboard"""
        self.project.drawing_view.copy_selected()
        self.project.drawing_view.delete_selected()
        
    def on_draw_copy(self, button=None):
        """Copy selected item to clipboard"""
        self.project.drawing_view.copy_selected()

    def on_draw_paste(self, button=None):
        """Paste rows from clipboard into schedule view"""
        self.project.drawing_view.paste()
        
    def on_draw_delete(self, button=None):
        """Delete selected item"""
        self.project.drawing_view.delete_selected()
    
    def on_new_tab(self, button):
        self.project.append_page()
        
    def on_edit_loadprofiles(self, button):
        self.project.edit_loadprofiles()
        
    def on_run_analysis(self, widget):
        """Export project to spreadsheet"""

        def exec_func(progress):
            progress.add_message('Building Base Model...')
            progress.set_fraction(0)
            self.project.setup_base_model()
            
            progress.add_message('Building Power Model...')
            progress.set_fraction(0.2)
            self.project.build_power_model()
            
            progress.add_message('Running Diagnostics...')
            progress.set_fraction(0.3)
            ret_code = self.project.run_diagnostics()
            
            if ret_code != misc.ERROR:
            
                progress.add_message('Running Power Flow...')
                progress.set_fraction(0.5)
                #self.project.run_powerflow()
                self.project.run_powerflow_timeseries()
                
                progress.add_message('Running Symmetric Short Circuit Calculation...')
                progress.set_fraction(0.7)
                self.project.run_sym_sccalc()
                
                progress.add_message('Running Line to Ground Short Circuit Calculation...')
                progress.set_fraction(0.8)
                self.project.run_linetoground_sccalc()
                
                progress.add_message('Updating Results...')
                progress.set_fraction(0.9)
                self.project.update_results()
                
                #progress.add_message('Setting up HTML Report...')
                #progress.set_fraction(0.9)
                #self.project.export_html_report('network.html')  #TODO
                
                #progress.add_message('Exporting pandapower network to JSON...')
                #progress.set_fraction(0.95)
                #self.project.export_json('network.json')  #TODO
                
                progress.set_fraction(1)
                progress.add_message('<b>Analysis run Successfully</b>')
                progress.pulse(end=True)
                
            else:
                raise RuntimeError("Diagnostics run returned critical errors. Please see <i>Warnings</i> pane.")
            
        self.run_command(exec_func)
        log.info('MainWindow - on_run_analysis - analysis run')
    
    # Draw signal handler methods
        
    def on_draw_zoomin(self, button):
        """Zoom in draw view"""
        if self.project.drawing_view.scale <= 2.4:
            self.project.drawing_view.scale += 0.2
            self.project.drawing_view.drawing_area.queue_draw()
        else:
            self.display_status(misc.WARNING, "Scale not changed (Reached maximum scale).")
        print(self.project.drawing_models)
        
    def on_draw_zoomout(self, button):
        """Zoom out draw view"""
        if self.project.drawing_view.scale >= 0.6:
            self.project.drawing_view.scale -= 0.2
            self.project.drawing_view.drawing_area.queue_draw()
        else:
            self.display_status(misc.WARNING, "Scale not changed (Reached minimum scale).")
            
    def on_draw_renumber(self, button):
        """Renumber elements"""
        
        # Setup dialog window
        dialog_window = Gtk.Dialog("Select numbering method", self.window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog_window.set_border_width(5)
        dialog_window.get_content_area().set_spacing(15)
        dialog_window.set_size_request(400,-1)
        dialog_window.set_default_response(Gtk.ResponseType.OK)
        
        # Setup Data model
        rounding_values = ("All",
                           "New elements only",
                           "Selected elements only")
        
        # Pack Dialog
        dialog_box = dialog_window.get_content_area()
        box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        dialog_box.add(box)
        rounding_combo = Gtk.ComboBoxText()
        for value in rounding_values:
            rounding_combo.append_text(value)
        box.pack_start(rounding_combo, True, True, 3)
        rounding_combo.set_active(2)
        
        # Run dialog
        dialog_window.show_all()
        response = dialog_window.run()
        if response == Gtk.ResponseType.OK:
            # Update quantity
            selected = rounding_combo.get_active_text()
            self.project.renumber_elements(selected)
            self.display_status(misc.INFO, "Elements renumbered")
            
        # Destroy dialog
        dialog_window.destroy()
        
    def on_draw_drawwire(self, widget):
        """Start drawing wire"""
        self.project.drawing_view.set_mode(misc.MODE_ADD_WIRE)
        
    def on_draw_addassembly(self, widget):
        """Insert an assembly from selection"""
        self.project.drawing_model.add_assembly_from_selection()
        self.project.drawing_view.refresh()
        
    def on_draw_element_add(self, list_box, row):
        code = row.props.name
        self.project.drawing_view.save_scroll_position()
        floating_model = self.project.drawing_model.set_floating_model_from_code(code)
        if floating_model:
            stack_toolbar_left = self.builder.get_object("stack_toolbar_left")
            
            def on_end_callback():
                stack_toolbar_left.set_visible_child_name('page_elements')
                self.insert_view.clean()
            
            self.insert_view.update(floating_model.fields, floating_model.name, floating_model.get_text_field, floating_model.set_text_field_value)
            self.project.drawing_view.set_mode(misc.MODE_INSERT, [on_end_callback])
            stack_toolbar_left.set_visible_child_name('page_insert')
            self.project.drawing_view.restore_scroll_position()
            
    def draw_element_add_header_func(self, row, before, group_dict):
        code = row.props.name
        group = group_dict[code]
        if before:
            code_before = before.props.name
            group_before = group_dict[code_before]
        else:
            group_before = ''
        if group and group != group_before:
            caption = Gtk.Label('', xalign=0)
            caption.set_use_markup(True)
            caption.set_markup('<b>' + group + '</b>')
            caption.props.margin = 6
            row.set_header(caption)
            
    def draw_element_add_sort_func(self, row1, row2, group_dict, name_dict):
        code1 = row1.props.name
        code2 = row2.props.name
        name1 = name_dict[code1]
        name2 = name_dict[code2]
        group1 = group_dict[code1]
        group2 = group_dict[code2]
        if group1 < group2:
            return -1
        if group1 > group2:
            return 1
        else:
            if name1 < name2:
                return -1
            if name1 > name2:
                return 1
            else:
                return 0
        
    def draw_element_add_filter_func(self, row, group_dict, name_dict, search_box):
        code = row.props.name
        name = name_dict[code].lower()
        group = group_dict[code].lower()
        search_string = search_box.get_text().lower()
        if search_string:
            if search_string in name or search_string in group:
                return True
            else:
                return False
        else:
            return True
    
    def on_draw_element_search_changed(self, entry):
        self.draw_element_listbox.invalidate_filter()
    
    ## Insert element tab callbacks
    
    def on_insert_element_rotate(self, widget):
        self.project.drawing_model.rotate_floating_model()
        
    def on_insert_element_cycle_port(self, widget):
        self.project.drawing_model.modify_fm_attachment_port()
        
        
    def __init__(self, id=0):
        
        log.info('MainWindow - Start initialisation')
        
        self.id = id
        self.project_active = False
        
        # Setup main data model
        self.program_settings = dict()
        self.program_state = dict()
        
        # Initialise undo/redo stack
        self.stack = undo.Stack()
        undo.setstack(self.stack)
        # Save point in stack for checking change state
        self.stack.savepoint()
        
        # Dynamically load elements from library
        #self.program_state['element_models'] = dict()
        #file_names = [f for f in os.listdir(misc.abs_path('element_library'))]
        #module_names = []
        #for f in file_names:
            #if f[-3:] == '.py' and f != '__init__.py':
                #module_names.append(f[:-3])
        #module_names.sort()
        #for module_name in module_names:
            #try:
                #spec = importlib.util.spec_from_file_location(module_name, misc.abs_path('element_library', module_name + '.py'))
                #module = importlib.util.module_from_spec(spec)
                #sys.modules[spec.name] = module
                #spec.loader.exec_module(module)
                #custom_object = module.CustomItem()
                #self.program_state['element_models'][custom_object.code] = custom_object
                #log.info('Model loaded - ' + module_name)
            #except ImportError:
                #log.error('Error Loading model - ' + module_name)
        
        # Setup elements
        self.program_state['element_models'] = dict()
        self.program_state['element_models'][switch.Switch().code] = switch.Switch
        self.program_state['element_models'][switch.CircuitBreaker().code] = switch.CircuitBreaker
        self.program_state['element_models'][switch.Contactor().code] = switch.Contactor
        self.program_state['element_models'][busbar.BusBar().code] = busbar.BusBar
        self.program_state['element_models'][grid.Grid().code] = grid.Grid
        self.program_state['element_models'][drawing.Reference().code] = drawing.Reference
        self.program_state['element_models'][transformer.Transformer().code] = transformer.Transformer
        self.program_state['element_models'][transformer.Transformer3w().code] = transformer.Transformer3w
        self.program_state['element_models'][load.Load().code] = load.Load
        self.program_state['element_models'][line.Line().code] = line.Line
        self.program_state['element_models'][line.LTCableIEC().code] = line.LTCableIEC
        self.program_state['element_models'][impedance.Impedance().code] = impedance.Impedance
        self.program_state['element_models'][impedance.Inductance().code] = impedance.Inductance
        self.program_state['element_models'][shunt.Shunt().code] = shunt.Shunt
        self.program_state['element_models'][shunt.ShuntCapacitor().code] = shunt.ShuntCapacitor
        self.program_state['element_models'][ward.Ward().code] = ward.Ward
        self.program_state['element_models'][ward.XWard().code] = ward.XWard
        self.program_state['element_models'][generator.Generator().code] = generator.Generator
        self.program_state['element_models'][generator.StaticGenerator().code] = generator.StaticGenerator
        self.program_state['element_models'][generator.Motor().code] = generator.Motor
                
        # Fill in default values
        self.program_state['mode'] = misc.MODE_DEFAULT
        self.program_state['stack'] = self.stack
        # Project Filename
        self.filename = None
            
        log.info('Setting up program settings')
        dirs = appdirs.AppDirs(misc.PROGRAM_NAME, misc.PROGRAM_AUTHOR, version=misc.PROGRAM_VER)
        settings_dir = dirs.user_data_dir
        self.user_library_dir = misc.posix_path(dirs.user_data_dir,'database')
        self.settings_filename = misc.posix_path(settings_dir,'settings.ini')
        # Create directory if does not exist
        if not os.path.exists(settings_dir):
            os.makedirs(settings_dir)
        if not os.path.exists(self.user_library_dir):
            os.makedirs(self.user_library_dir)
        
        try:
            if os.path.exists(self.settings_filename):
                with open(self.settings_filename, 'r') as fp:
                    self.program_settings = json.load(fp)
                    log.info('Program settings opened at ' + str(self.settings_filename))
            else:
                self.program_settings = copy.deepcopy(misc.default_program_settings)
                with open(self.settings_filename, 'w') as fp:
                    json.dump(self.program_settings, fp)
                log.info('Program settings saved at ' + str(self.settings_filename))
        except:
            # If an error load default program preference
            self.program_settings = copy.deepcopy(misc.default_program_settings)
            log.info('Program settings initialisation failed - falling back on default values')
        self.program_state['program_settings_main'] = self.program_settings['Defaults']
        log.info('Program settings initialised')
        
        # Setup main window
        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "mainwindow.glade"))
        self.builder.connect_signals(self)
        self.window = self.builder.get_object("window_main")
        self.drawing_notebook = self.builder.get_object("drawing_notebook")
        self.program_state['window'] = self.window
        self.program_state['drawing_notebook'] = self.drawing_notebook
        
        # Setup element addition toolbar
        self.draw_element_groups = dict()
        self.draw_element_names = dict()
        self.draw_element_listbox = self.builder.get_object("draw_element_listbox")
        self.draw_element_searchbox = self.builder.get_object("draw_element_searchbox")
        self.draw_element_listbox.set_activate_on_single_click(True)
        self.draw_element_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.draw_element_listbox.set_header_func(self.draw_element_add_header_func, self.draw_element_groups)
        self.draw_element_listbox.set_sort_func(self.draw_element_add_sort_func, self.draw_element_groups, self.draw_element_names)
        self.draw_element_listbox.set_filter_func(self.draw_element_add_filter_func, self.draw_element_groups, self.draw_element_names, self.draw_element_searchbox)
        self.draw_element_listbox.connect("row_activated", self.on_draw_element_add)
        self.draw_element_searchbox.connect("search-changed", self.on_draw_element_search_changed)
        for code, model in self.program_state['element_models'].items():
            model_obj = model()
            name = model_obj.name
            group = model_obj.group
            icon_path = model_obj.icon
            icon = Gtk.Image.new_from_file(icon_path)
            icon.set_size_request(40, 40)
            caption = Gtk.Label(name, xalign=0)
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            hbox.pack_start(icon, False, False, 12)
            hbox.pack_start(caption, True, True, 12)
            row = Gtk.ListBoxRow()
            row.props.name = code
            row.set_activatable(True)
            row.add(hbox)
            self.draw_element_groups[code] = group
            self.draw_element_names[code] = name
            self.draw_element_listbox.add(row)
        self.draw_element_listbox.show_all()
        
        # Setup field views
        self.insert_field_listbox = self.builder.get_object("insert_element_listbox")
        self.insert_view = FieldView(self.window, self.insert_field_listbox, 
                                     'status_floating', 'status_inactivate')
        self.draw_properties_listbox = self.builder.get_object("draw_properties_listbox")
        self.properties_view = FieldView(self.window, self.draw_properties_listbox, 
                                         'status_enable', 'status_inactivate')
        self.draw_result_listbox = self.builder.get_object("draw_result_listbox")
        self.results_view = FieldView(self.window, self.draw_result_listbox, 
                                      'status_enable', 'status_inactivate')
        self.draw_diagnostic_listbox = self.builder.get_object("draw_diagnostic_listbox")
        self.diagnostics_view = MessageView(self.window, 
                                            self.draw_diagnostic_listbox)
        self.program_state['insert_view'] = self.insert_view
        self.program_state['properties_view'] = self.properties_view
        self.program_state['results_view'] = self.results_view
        self.program_state['diagnostics_view'] = self.diagnostics_view
        
        self.draw_load_database_button = self.builder.get_object("draw_load_database_button")
        self.database_view = DatabaseView(self.window, 
                                          self.draw_load_database_button,
                                          self.properties_view,
                                          self.program_state)
        self.program_state['database_view'] = self.database_view
        
        # Setup ProjectView
        self.program_state['project_settings_main'] = None  # Updated inside ProjectModel constructor
        self.project = ProjectModel(self.window, self.program_state)
        self.program_state['project'] = self.project
        
        # Setup infobar/ revealer
        self.progress_revealer = self.builder.get_object("progress_revealer")
        self.progress_label = self.builder.get_object("progress_label")
        self.progress_bar = self.builder.get_object("progress_bar")
        self.builder.get_object("infobar_main").hide()
        
        # Setup about dialog
        self.about_dialog = self.builder.get_object("aboutdialog")
        
        self.window.show_all()
        log.info('MainWindow - Initialised')
        
        
class MainApp(Gtk.Application):
    """Class handles application related tasks"""

    def __init__(self, *args, **kwargs):
        log.info('MainApp - Start initialisation')
        
        super().__init__(*args, application_id=misc.APPID,
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
                         **kwargs)
                         
        self.window = None
        self.about_dialog = None
        self.windows = []
        
        self.add_main_option("test", ord("t"), GLib.OptionFlags.NONE,
                             GLib.OptionArg.NONE, "Command line test", None)
                             
        log.info('MainApp - Initialised')
        

    # Application function overloads
    
    def do_startup(self):
        log.info('MainApp - do_startup - Start')
        
        Gtk.Application.do_startup(self)
        
        action = Gio.SimpleAction.new("new", None)
        action.connect("activate", self.on_new)
        self.add_action(action)
        
        action = Gio.SimpleAction.new("help", None)
        action.connect("activate", self.on_help)
        self.add_action(action)

        action = Gio.SimpleAction.new("about", None)
        action.connect("activate", self.on_about)
        self.add_action(action)

        action = Gio.SimpleAction.new("quit", None)
        action.connect("activate", self.on_quit)
        self.add_action(action)
        
        log.info('MainApp - do_startup - End')
    
    def do_activate(self):
        log.info('MainApp - do_activate - Start')
        
        self.window = MainWindow(len(self.windows))
        self.windows.append(self.window)
        self.add_window(self.window.window)
        
        log.info('MainApp - do_activate - End')
        
    def do_open(self, files, hint):
        
        def call_open(window, filename):
            if window.finished_setting_up:
                log.info('MainApp - do_open - call_open - Start')
                window.on_open_project_clicked(None, filename)
                log.info('MainApp - do_open - call_open - opened file ' + filename)
                return False
            else:
                return True
        
        log.info('MainApp - do_open - Start')
        self.activate()
        if len(files) > 0:
            filename = files[0].get_path()
            GLib.timeout_add(500, call_open, self.window, filename)
        log.info('MainApp - do_open  - End')
        return 0
    
    def do_command_line(self, command_line):
        
        def call_open(window, filename):
            if window.finished_setting_up:
                log.info('MainApp - do_command_line - call_open - Start')
                window.on_open_project_clicked(None, filename)
                log.info('MainApp - do_command_line - call_open - opened file ' + filename)
                return False
            else:
                return True
                
        log.info('MainApp - do_command_line - Start')
        options = command_line.get_arguments()
        self.activate()
        if len(options) > 1:
            filename = misc.uri_to_file(options[1])
            GLib.timeout_add(500, call_open, self.window, filename)
        log.info('MainApp - do_command_line - End')
        return 0
        
    # Application callbacks
        
    def on_about(self, action, param):
        """Show about dialog"""
        log.info('MainApp - Show About window')
        # Setup about dialog
        self.builder = Gtk.Builder()
        self.builder.add_from_file(misc.abs_path("interface", "aboutdialog.glade"))
        self.about_dialog = self.builder.get_object("aboutdialog")
        self.about_dialog.set_transient_for(self.get_active_window())
        self.about_dialog.set_modal(True)
        self.about_dialog.run()
        self.about_dialog.destroy()
        
    def on_help(self, action, param):
        """Launch help file"""
        log.info('onHelpClick - Launch Help file')
        misc.open_file('https://kavilgroup.com/', abs=False)
        
    def on_new(self, action, param):
        log.info('MainApp - Raise new window')
        self.do_activate()
        
    def on_quit(self, action, param):
        self.quit()
