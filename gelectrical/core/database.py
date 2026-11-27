#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# database
#
#  Copyright 2026 Manu Varkey <manuvarkey@gmail.com>
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

"""Equipment database helpers (no GUI imports).

``data`` columns of the CSV libraries (``pcurve_l``, ``pcurve_g``) hold a
reference to protection curve files written as a Python tuple literal:
``('mcb_lnt', '', 'lnt_mcb_b.json')`` = (sub directory, curve data CSV or
empty, parameters JSON). The reference is parsed with ``ast.literal_eval``
and validated instead of ``eval`` (ADR 0011).
"""

import ast
import posixpath


class DatabaseReferenceError(ValueError):
    """A database file reference is malformed or unsafe"""


def _check_part(part, value, allow_empty):
    if not isinstance(part, str):
        raise DatabaseReferenceError('Database reference parts must be text: %r' % (value,))
    if not part:
        if allow_empty:
            return
        raise DatabaseReferenceError('Empty file name in database reference: %r' % (value,))
    normalized = part.replace('\\', '/')
    if (normalized.startswith('/') or ':' in normalized
            or '..' in normalized.split('/')):
        raise DatabaseReferenceError('Database reference must stay inside the library: %r' % (value,))
    if posixpath.normpath(normalized) != normalized.rstrip('/'):
        raise DatabaseReferenceError('Database reference is not a plain path: %r' % (value,))


def parse_data_reference(value):
    """Parse ``"('subdir', 'data.csv', 'params.json')"`` into a 3-tuple of
    relative paths. Raises :class:`DatabaseReferenceError`."""
    try:
        parsed = ast.literal_eval(value.strip()) if isinstance(value, str) else value
    except (ValueError, SyntaxError, MemoryError, RecursionError):
        raise DatabaseReferenceError('Invalid database reference: %r' % (value,)) from None
    if not isinstance(parsed, (tuple, list)) or len(parsed) != 3:
        raise DatabaseReferenceError('Database reference must have three parts: %r' % (value,))
    subdir, data_filename, params_filename = parsed
    _check_part(subdir, value, allow_empty=True)
    _check_part(data_filename, value, allow_empty=True)
    _check_part(params_filename, value, allow_empty=False)
    return subdir, data_filename, params_filename
