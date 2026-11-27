# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Manu Varkey

"""Load profiles of the project (one undo entry per change, as the legacy
editor). Profile format: ``{uid: [title, [graph model, ...]]}`` with graph
models ``{"mode", "title", "xval": [...], "yval": [...]}``."""

import copy
import math
import numbers

from ..protocol import json_safe, invalid, validation
from ..registry import query, command

MAX_PROFILES = 500
MAX_POINTS = 10_000


def _check_series(values, field):
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_POINTS:
        raise invalid('Expected a list of numbers', field=field)
    for value in values:
        if isinstance(value, bool) or not isinstance(value, numbers.Real) or not math.isfinite(value):
            raise invalid('Expected finite numbers', field=field)


def validate_profiles(profiles):
    if not isinstance(profiles, dict) or not profiles or len(profiles) > MAX_PROFILES:
        raise invalid('Expected an object of load profiles', field='profiles')
    for key, profile in profiles.items():
        field = 'profiles.' + key
        if not key or not isinstance(profile, list) or len(profile) != 2 or not isinstance(profile[0], str):
            raise invalid('Expected [title, graphs]', field=field)
        graphs = profile[1]
        if not isinstance(graphs, list) or not graphs:
            raise invalid('Expected a list of graphs', field=field)
        for graph in graphs:
            if not isinstance(graph, dict) or 'xval' not in graph or 'yval' not in graph:
                raise invalid('Expected graphs with xval and yval', field=field)
            _check_series(graph['xval'], field)
            _check_series(graph['yval'], field)
            if len(graph['xval']) != len(graph['yval']):
                raise validation('xval and yval must have the same length', field=field)
    return copy.deepcopy(profiles)


@query('loadprofiles.get')
def get(ctx):
    """Load profiles of the project"""
    return json_safe(ctx.project.loadprofiles)


@command('loadprofiles.set', label='Update load profiles')
def set_profiles(ctx, profiles):
    """Replace all load profiles"""
    profiles = validate_profiles(profiles)
    ctx.project.modify_loadprofiles(profiles)
    for drawing_model in ctx.project.drawing_models:
        for element in drawing_model.elements:
            if 'load_profile' in element.fields:
                element.fields['load_profile']['selection_list'] = ctx.project.loadprofiles
    return json_safe(ctx.project.loadprofiles)
