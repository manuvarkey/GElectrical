#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# formatter
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

"""Label text of schematic symbols.

``text_model`` expressions are templates over the element field values
(``"${sn_kva}kVA"``, ``"${'%g'%(In)}A"``). Each ``${...}`` is evaluated with
the safe expression evaluator and replaced by ``str`` of its value, as the
Mako templates used before M3 did (D3, ADR 0011).
"""

from ..core.expressions import format_template, Policy

# Names are field values; no attribute access or method calls are needed
LABEL_POLICY = Policy()


def format_label(expr, values):
    """Render the label expression ``expr`` with field ``values``"""
    return format_template(expr, values, LABEL_POLICY)
