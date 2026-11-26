#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# geometry
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

"""Pure geometry for schematic queries (no Cairo, no GUI)."""

def rect_from_points(*points):
    if len(points) > 1:
        maxx = minx = points[0][0]
        maxy = miny = points[0][1]
        for point in points[1:]:
            x, y = point
            maxx = x if x > maxx else maxx
            maxy = y if y > maxy else maxy
            minx = x if x < minx else minx
            miny = y if y < miny else miny
        x0 = int(minx)
        y0 = int(miny)
        width = int(maxx-minx)
        height = int(maxy-miny)
        return (x0, y0, width, height)
    else:
        return None
    
