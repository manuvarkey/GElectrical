"""Pure geometry replacing cairo.Region (M2 step 5)."""

import random

import cairo
import pytest

from gelectrical.core import geometry as g

OVERLAP = {cairo.RegionOverlap.IN: g.OVERLAP_IN,
           cairo.RegionOverlap.PART: g.OVERLAP_PART,
           cairo.RegionOverlap.OUT: g.OVERLAP_OUT}


def _rect(rng):
    return (rng.randint(-20, 20), rng.randint(-20, 20), rng.randint(-3, 15), rng.randint(-3, 15))


@pytest.mark.parametrize('seed', range(4))
def test_matches_cairo_region(seed):
    rng = random.Random(seed)
    for _ in range(5000):
        a, b = _rect(rng), _rect(rng)
        if g.rect_is_empty(a):
            # cairo logs a pixman error for invalid rectangles; the region is empty
            assert g.rect_overlap(a, b) == g.OVERLAP_OUT
            assert not g.rect_contains_point(a, 0, 0)
        else:
            region = cairo.Region(cairo.RectangleInt(*a))
            assert g.rect_overlap(a, b) == OVERLAP[region.contains_rectangle(cairo.RectangleInt(*b))]
            x, y = rng.randint(-20, 20), rng.randint(-20, 20)
            assert g.rect_contains_point(a, x, y) == region.contains_point(x, y)
        rects = [r for r in (_rect(rng) for _ in range(rng.randint(0, 5))) if not g.rect_is_empty(r)]
        rects += [(rng.randint(-5, 5), rng.randint(-5, 5), 0, rng.randint(0, 5))]
        e = cairo.Region([cairo.RectangleInt(*r) for r in rects if r[2] >= 0 and r[3] >= 0]).get_extents()
        assert g.region_extents(rects) == (e.x, e.y, e.width, e.height)


def test_empty_region_extents():
    assert g.region_extents([]) == (0, 0, 0, 0)
    assert g.region_extents([(5, 5, 0, 10)]) == (0, 0, 0, 0)


def test_rect_from_points():
    assert g.rect_from_points((3, 4), (1, 9)) == (1, 4, 2, 5)
    assert g.rect_from_points((3, 4)) is None
