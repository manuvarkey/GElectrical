#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# ids
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

"""Stable identifiers of elements and sheets (ADR 0008).

A ``uid`` is a UUID4 string. Services, events and the frontend address
elements and sheets by ``uid``, never by list position. The ``.gepro`` format
stores it as an additive key that the legacy loader ignores. No GUI imports.
"""

import re
import uuid

_UID_RE = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')


def new_uid():
    """Return a new identifier (UUID4, lower-case hex with dashes)"""
    return str(uuid.uuid4())


def is_uid(value):
    """True when ``value`` is an identifier as written by :func:`new_uid`"""
    return isinstance(value, str) and bool(_UID_RE.match(value))
