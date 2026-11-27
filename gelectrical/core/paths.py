#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# paths
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

"""File system helpers: package resources, platform paths and equipment
library resolution. No GUI imports."""

import os, posixpath, platform, pathlib, subprocess, logging
from urllib.parse import urlparse
from urllib.request import url2pathname

# Setup logger object
log = logging.getLogger(__name__)

# Root of the gelectrical package (resources: database, templates, icons)
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# User equipment library folder (set by the application at start-up)
USER_LIBRARY_DIR = ''


def set_user_library_dir(path):
    """Set the user library folder searched first by :func:`open_library`."""
    global USER_LIBRARY_DIR
    USER_LIBRARY_DIR = path

def abs_path(*args):
    """Returns absolute path to the relative path provided (package resources)"""
    return os.path.join(PACKAGE_DIR, *args)
    
def dir_from_path(path):
    """Returns directory path from file path"""
    return os.path.dirname(path)

def posix_path(*args):
    """Returns platform independent filename"""
    if platform.system() == 'Linux': 
        if len(args) > 1:
            return posixpath.join(*args)
        else:
            return args[0]
    elif platform.system() == 'Windows':
        if len(args) > 1:
            path = os.path.normpath(posixpath.join(*args))
        else:
            path = os.path.normpath(args[0])
        # remove any leading slash
        if path[0] == '\\':
            return path[1:]
        else:
            return path

def file_to_uri(filename):
    if platform.system() == 'Windows':
        path = pathlib.PureWindowsPath(filename)
        uri = path.as_uri()
        # If network path
        if filename.startswith(r'\\'):
            uri = uri[0:7] + '//' + uri[7:]
    else:
        path = pathlib.Path(filename)
        uri = path.as_uri()
    return uri
    
def uri_to_file(uri):
    return url2pathname(urlparse(uri).path)

def get_file_path_from_dnd_dropped_uri(uri):
    # Get the path to file
    path = ""
    if uri.startswith('file:\\\\\\'): # windows
        path = uri[8:] # 8 is len('file:///')
    elif uri.startswith('file://'): # nautilus, rox
        path = uri[7:] # 7 is len('file://')
    elif uri.startswith('file:'): # xffm
        path = uri[5:] # 5 is len('file:')

    path = url2pathname(path) # escape special chars
    path = path.strip('\r\n\x00') # remove \r\n and NULL

    return path

def open_file(filename, abs=False):
    """Open a file or URL with the desktop default application"""
    if abs:
        filename_mod = abs_path(filename)
    else:
        filename_mod = filename
        
    if platform.system() == 'Linux':
        ret_code = subprocess.call(('xdg-open', filename_mod))
        if ret_code:
            log.error('open_file - Error opening file - ' + filename_mod)
    elif platform.system() == 'Windows':
        os.startfile(filename_mod)

def open_library(filename):
    """Resolve an equipment library file: user library first, then bundled"""
    filename_abs = posix_path(USER_LIBRARY_DIR, filename)
    filename_abs_lib = abs_path('database', filename)
    if os.path.isfile(filename_abs):
        return filename_abs
    elif os.path.isfile(filename_abs_lib):
        return filename_abs_lib
    else:
        return None
