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


def load_database(data_path):
    """Read a ``;``-separated equipment library CSV into
    ``{category: {item_name: {field_code: text}}}`` (insertion order kept).
    Moved from the GTK database dialog (M4)."""
    import csv
    data = dict()
    with open(data_path, encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file, delimiter=';')
        for row in csv_reader:
            item_name = row['item_name']
            item_category = row['item_category']
            if item_category in data:
                category_dict = data[item_category]
            else:
                category_dict = dict()
                data[item_category] = category_dict
            row.pop('item_category')
            row.pop('item_name')
            category_dict[item_name] = row
    return data


def validate_database_item(fields, item, data_path):
    """Convert the text values of a library ``item`` to field values using
    the field types of ``fields``; returns ``{field_code: value}``.

    Same conversions as the legacy GTK database dialog (moved in M4):
    ``int``/``float``/``bool`` fall back to 0/0/False, ``graph`` values name a
    JSON file next to the library, ``data`` values are protection curve
    references (:func:`parse_data_reference`). Unreadable references give
    ``None`` and are logged. Codes missing from ``fields`` raise ``KeyError``
    as before."""
    import json, logging, os
    import numpy as np
    log = logging.getLogger(__name__)
    dirname = os.path.dirname(data_path)
    validated_dict = dict()
    for code, value in item.items():
        data_type = fields[code]['type']
        if data_type == 'int':
            try:
                validated = int(value)
            except:
                validated = 0
        elif data_type == 'float':
            try:
                validated = float(value)
            except:
                validated = 0
        elif data_type == 'bool':
            try:
                validated = bool(value)
            except:
                validated = False
        elif data_type == 'graph':
            try:
                valuepath = os.path.normpath(os.path.join(dirname, value))
                with open(valuepath, 'r', encoding='utf-8') as fileobj:
                    validated = json.load(fileobj)
            except:
                validated = None
                log.exception('validate_database_item - validation failure while reading graph field')
        elif data_type == 'data':
            try:
                if value:
                    (subdir, data_filename, params_filename) = parse_data_reference(value)
                    valuepath_params = os.path.normpath(os.path.join(dirname, subdir, params_filename))
                    with open(valuepath_params, 'r', encoding='utf-8') as fp:
                        data_struct = json.load(fp)
                    validated = data_struct
                    if data_filename:
                        valuepath = os.path.normpath(os.path.join(dirname, subdir, data_filename))
                        data = np.loadtxt(valuepath, delimiter=',')
                        curve_u = []
                        curve_l = []
                        for row in data:
                            curve_u.append(('point', str(row[0])+'*f.In', str(row[1])))
                            curve_l.append(('point', str(row[2])+'*f.In', str(row[3])))
                        validated['data']['curve_u'] = curve_u
                        validated['data']['curve_l'] = curve_l
                else:
                    validated = None
            except:
                validated = None
                log.exception('validate_database_item - validation failure while reading data field')
        else:
            validated = value
        validated_dict[code] = validated
    return validated_dict
