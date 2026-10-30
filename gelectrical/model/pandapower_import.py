#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pandapower_import
#
# Copyright 2026 ViviBeri contributors
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

"""Read-only import helpers for external pandapower JSON networks.

Imported networks are deliberately kept separate from GElectrical's editable
schematic/project model. This prevents an external pandapower network from
being mistaken for a native .gepro project.
"""

import os

_NETWORK_TABLES = (
    ("bus", "Buses"),
    ("line", "Lines"),
    ("trafo", "Transformers"),
    ("trafo3w", "Three-winding transformers"),
    ("load", "Loads"),
    ("sgen", "Static generators"),
    ("gen", "Generators"),
    ("ext_grid", "External grids"),
    ("switch", "Switches"),
    ("shunt", "Shunts"),
    ("impedance", "Impedances"),
    ("ward", "Ward elements"),
    ("xward", "Extended Ward elements"),
    ("storage", "Storage elements"),
)


def load_network_json(filename):
    """Load and minimally validate a pandapower JSON network.

    The pandapower dependency is imported lazily so importing this module does
    not add startup cost or make non-import workflows depend on this helper.
    The returned network is not converted into a GElectrical schematic.
    """
    if not filename or not os.path.isfile(filename):
        raise ValueError("The selected JSON file does not exist.")

    if os.path.getsize(filename) == 0:
        raise ValueError("The selected JSON file is empty.")

    try:
        import pandapower as pp
    except ImportError as exc:
        raise RuntimeError(
            "Pandapower is required to import a network JSON file. "
            "Please install the application's pandapower dependency."
        ) from exc

    try:
        network = pp.from_json(filename)
    except Exception as exc:
        raise ValueError("Pandapower could not read this JSON network file: {}".format(exc)) from exc

    if not isinstance(network, dict) or "bus" not in network:
        raise ValueError("The JSON file does not contain a valid pandapower network.")

    bus_table = network["bus"]
    if bus_table is None or not hasattr(bus_table, "__len__"):
        raise ValueError("The imported pandapower network has no valid bus table.")

    return network


def get_network_summary(network):
    """Return element counts for the standard pandapower network tables."""
    if not isinstance(network, dict) or "bus" not in network:
        raise ValueError("A valid pandapower network is required.")

    summary = []
    for table_name, label in _NETWORK_TABLES:
        table = network.get(table_name)
        if table is not None:
            try:
                count = len(table)
            except TypeError:
                count = 0
            if count:
                summary.append((label, count))

    return summary
