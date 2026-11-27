#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# misc
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

"""Legacy compatibility module for the GTK UI (M2 transition).

The contents of the former ``misc.py`` moved to:

* :mod:`gelectrical.core.constants`, :mod:`gelectrical.core.style`,
  :mod:`gelectrical.core.fields`, :mod:`gelectrical.core.paths`,
  :mod:`gelectrical.core.undoable`, :mod:`gelectrical.core.interpolation`
* :mod:`gelectrical.symbols.render` (Cairo drawing primitives)
* :mod:`gelectrical.reports.tables`, :mod:`gelectrical.reports.spreadsheet`
* :mod:`gelectrical.gtk.widgets` (GTK dialogs and helpers)

This module re-exports them for ``gelectrical.gtk``. It imports GTK, so
engine modules must not import it. Run-time style values (colours, fonts)
and ``USER_LIBRARY_DIR`` are forwarded live to their owning modules, for
reading and for assignment.
"""

import sys, types

from .core.constants import *
from .core import style as _style, paths as _paths
from .core.style import (set_dark_mode_drawing_values, reset_dark_mode_drawing_values,
                         check_dark_mode, rgb2hex, hex2rgb)
from .core.fields import *
from .core.fields import (default_program_settings, default_project_settings,
                          loadprofile_blank_fields)
from .core.paths import (abs_path, dir_from_path, posix_path, file_to_uri, uri_to_file,
                         get_file_path_from_dnd_dropped_uri, open_file, open_library)
from .core.undoable import _Action, undoable, _Group, group, get_undoable_set_field, \
                           get_undoable_set_field_multiple
from .core.interpolation import log_interpolate, log_interpolate_piecewise
from .core.geometry import rect_from_points
from .symbols.render import draw_rectangle, draw_line, draw_text
from .reports.tables import clean_markup, elements_to_table, fields_to_table, params_to_table
from .reports.spreadsheet import Spreadsheet
from .gtk.widgets import (SpreadsheetDialog, ProgressRevealer, SplashScreen, Command, pprint,
                          display_message, get_user_input_text, set_widget_font,
                          font_str_parse, font_str_encode, get_image_from_path)

_FORWARDED = {name: _style for name in _style.MUTABLE_NAMES}
_FORWARDED['USER_LIBRARY_DIR'] = _paths


class _LegacyModule(types.ModuleType):
    """Forward run-time style values to gelectrical.core.style/paths"""

    def __getattr__(self, name):
        owner = _FORWARDED.get(name)
        if owner is None:
            raise AttributeError("module %r has no attribute %r" % (self.__name__, name))
        return getattr(owner, name)

    def __setattr__(self, name, value):
        owner = _FORWARDED.get(name)
        if owner is None:
            super().__setattr__(name, value)
        else:
            setattr(owner, name, value)


sys.modules[__name__].__class__ = _LegacyModule
