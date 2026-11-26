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
    

# Integer rectangles (x, y, width, height), with the semantics of the
# cairo.Region operations they replace (pixman boxes [x, x+w) x [y, y+h)).
# An empty rectangle (width or height <= 0) contributes nothing to a region.

OVERLAP_OUT = 0
OVERLAP_IN = 1
OVERLAP_PART = 2

def rect_is_empty(rect):
    return rect[2] <= 0 or rect[3] <= 0

def region_extents(rects):
    """Bounding rectangle of the union of ``rects`` (empty ones ignored);
    (0, 0, 0, 0) for an empty region. Replaces ``cairo.Region(rects).get_extents()``."""
    boxes = [(int(x), int(y), int(x) + int(w), int(y) + int(h))
             for (x, y, w, h) in rects if int(w) > 0 and int(h) > 0]
    if not boxes:
        return (0, 0, 0, 0)
    x1 = min(b[0] for b in boxes)
    y1 = min(b[1] for b in boxes)
    x2 = max(b[2] for b in boxes)
    y2 = max(b[3] for b in boxes)
    return (x1, y1, x2 - x1, y2 - y1)

def rect_overlap(region_rect, rect):
    """Overlap of ``rect`` with the single-rectangle region ``region_rect``:
    OVERLAP_IN, OVERLAP_PART or OVERLAP_OUT.
    Replaces ``cairo.Region(region_rect).contains_rectangle(rect)``."""
    rx, ry, rw, rh = (int(v) for v in region_rect)
    if rw <= 0 or rh <= 0:
        return OVERLAP_OUT
    x1, y1 = int(rect[0]), int(rect[1])
    x2, y2 = x1 + int(rect[2]), y1 + int(rect[3])
    rx2, ry2 = rx + rw, ry + rh
    if not (rx2 > x1 and rx < x2 and ry2 > y1 and ry < y2):
        return OVERLAP_OUT
    if rx <= x1 and rx2 >= x2 and ry <= y1 and ry2 >= y2:
        return OVERLAP_IN
    return OVERLAP_PART

def rect_overlaps(region_rect, rect):
    """True when ``rect`` is inside or partly inside ``region_rect``"""
    return rect_overlap(region_rect, rect) != OVERLAP_OUT

def rect_contains_point(rect, x, y):
    """Replaces ``cairo.Region(rect).contains_point(x, y)``"""
    rx, ry, rw, rh = (int(v) for v in rect)
    if rw <= 0 or rh <= 0:
        return False
    return rx <= x < rx + rw and ry <= y < ry + rh
