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

``text_model`` expressions are Mako templates over the element field values
(``"${sn_kva}kVA"``), as before M2. Replacing Mako by a declarative format is
scheduled with the safe-expressions work (D3, M3).
"""

from mako.template import Template as ExprTemplate

_templates = dict()


def format_label(expr, values):
    """Render the label expression ``expr`` with field ``values``"""
    template = _templates.get(expr)
    if template is None:
        template = ExprTemplate(expr)
        _templates[expr] = template
    return template.render(**values)
