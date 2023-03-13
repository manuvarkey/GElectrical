#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# run.py
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

import sys, tempfile, logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, GObject

# Get logger object
log = logging.getLogger()

# Override stdout and stderr with NullWriter in GUI --noconsole mode
# This allow to avoid a bug where tqdm try to write on NoneType
# https://github.com/tqdm/tqdm/issues/794#issuecomment-1426204074
class NullWriter:
    def write(self, data):
        pass
if sys.stdout is None:
    sys.stdout = NullWriter()
if sys.stderr is None:
    sys.stderr = NullWriter()

from gelectrical import MainApp

if __name__ == '__main__':
    # Setup logging
    
    # Setup Logging to temporary file
    log_file = tempfile.NamedTemporaryFile(mode='w', prefix='electricdesign_', 
                                               suffix='.log', delete=False)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=log_file,level=logging.INFO)
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        stream=sys.stdout,level=logging.INFO)
    # Logging to stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    # Log all uncaught exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    sys.excepthook = handle_exception
    
    # Initialise main window
    
    log.info('Start Program Execution')
    app = MainApp()
    log.info('Entering Gtk main loop')
    app.run(sys.argv)
    log.info('End Program Execution')
    
