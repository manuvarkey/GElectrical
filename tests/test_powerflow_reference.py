#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2026 ViviBeri contributors
# SPDX-License-Identifier: GPL-3.0-or-later

"""Reference regression test for GElectrical's symmetric power-flow runner.

The expected receiving-bus voltage is calculated independently from the
single-phase equivalent of a balanced, unity-power-factor two-bus network.
"""

import math

import pytest

pp = pytest.importorskip("pandapower")
pytest.importorskip("numpy")
pytest.importorskip("pandas")

from gelectrical.model.pandapower import PandaPowerModel


def test_two_bus_powerflow_matches_analytical_voltage_reference():
    """A balanced 400 V, two-bus feeder matches the closed-form voltage."""
    net = pp.create_empty_network(f_hz=50)
    source_bus = pp.create_bus(net, vn_kv=0.4, name="Source")
    load_bus = pp.create_bus(net, vn_kv=0.4, name="Load")

    pp.create_ext_grid(net, bus=source_bus, vm_pu=1.0, va_degree=0.0)
    pp.create_line_from_parameters(
        net,
        from_bus=source_bus,
        to_bus=load_bus,
        length_km=1.0,
        r_ohm_per_km=0.1,
        x_ohm_per_km=0.01,
        c_nf_per_km=0.0,
        max_i_ka=1.0,
    )
    pp.create_load(net, bus=load_bus, p_mw=0.1, q_mvar=0.0)

    # Supply the minimal result mappings normally populated during model build.
    model = PandaPowerModel.__new__(PandaPowerModel)
    model.power_model = net
    model.base_elements = {}
    model.power_nodes_inverted = {
        source_bus: "source",
        load_bus: "load",
    }
    model.node_results = {}
    model.power_elements = {}
    model.element_results = {}

    model.run_powerflow("Power flow", runpp_3ph=False)

    # For a unity-PF load, the single-phase equivalent satisfies
    # Vs^2 = (V + P_phase*R/V)^2 + (P_phase*X/V)^2.
    # Solve the resulting quadratic in V^2 and select the high-voltage root.
    source_phase_voltage = 400.0 / math.sqrt(3.0)
    resistance_ohm = 0.1
    reactance_ohm = 0.01
    phase_power_w = 100_000.0 / 3.0
    coefficient = 2 * phase_power_w * resistance_ohm - source_phase_voltage**2
    constant = phase_power_w**2 * (resistance_ohm**2 + reactance_ohm**2)
    discriminant = coefficient**2 - 4 * constant
    expected_phase_voltage = math.sqrt((-coefficient + math.sqrt(discriminant)) / 2.0)
    expected_voltage_pu = expected_phase_voltage / source_phase_voltage

    actual_voltage_pu = net.res_bus.vm_pu.at[load_bus]
    assert actual_voltage_pu == pytest.approx(expected_voltage_pu, abs=1e-5)
