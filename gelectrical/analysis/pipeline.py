#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# pipeline
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

"""Analysis pipeline (moved from ``MainWindow.on_run_analysis``, M2 step 7).

The order of calculations and the project state they produce are those of
the legacy GTK callback: build base model, build power models, diagnostics,
power flow (single, with diversity or time series), symmetric and
line-to-ground short circuit, update results. The rules check is separate
(``MainWindow.on_run_rulescheck``). Exceptions of a calculation propagate
unchanged, like in the GUI worker thread.

``progress`` is an optional callable ``progress(fraction, message)``.
"""

import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from ..core import constants

# Get logger object
log = logging.getLogger(__name__)

POWERFLOW_METHODS = ('Power flow', 'Power flow with diversity', 'Time series')


class AnalysisError(RuntimeError):
    """Analysis stopped (critical diagnostics)"""


@dataclass
class AnalysisSettings:
    """What to run. ``three_phase`` is read from the project Simulation
    field ``power_flow_3ph`` by the power-flow step, as before."""
    diagnostics: bool = True
    powerflow: bool = True
    pf_method: str = 'Power flow'
    sc_sym: bool = True
    sc_gf: bool = True

    @classmethod
    def from_project(cls, project, run_all=True):
        """Settings from the project Simulation fields. With ``run_all`` every
        calculation runs (the analysis dialog's defaults for a full run)."""
        sim = project.get_project_fields(page='Simulation')
        if run_all:
            return cls(diagnostics=True, powerflow=True, pf_method=sim['pf_method']['value'],
                       sc_sym=True, sc_gf=True)
        return cls(diagnostics=bool(sim['run_diagnostics']['value']),
                   powerflow=bool(sim['run_powerflow']['value']),
                   pf_method=sim['pf_method']['value'],
                   sc_sym=bool(sim['run_sc_sym']['value']),
                   sc_gf=bool(sim['run_sc_gf']['value']))


@dataclass
class AnalysisStep:
    name: str
    ok: bool = True


@dataclass
class AnalysisResult:
    """Typed outcome of :func:`run_analysis`"""
    settings: AnalysisSettings
    steps: List[AnalysisStep] = field(default_factory=list)
    diagnostics_ret_code: Optional[int] = None
    diagnostics: Optional[list] = None   # diagnostic messages (MessageView data)
    completed: bool = False
    # Flags of the legacy program_state used to enable the rules check
    build_networkmodel: bool = False
    run_powerflow: bool = False
    run_sc_sym: bool = False
    run_sc_lg: bool = False

    @property
    def rules_check_ready(self):
        return self.build_networkmodel and self.run_powerflow and self.run_sc_sym and self.run_sc_lg


def _diagnostics_listener(store):
    def listener(event, **data):
        if event == 'diagnostics':
            store.append(data['results'])
    return listener


def run_analysis(project, settings=None, progress: Optional[Callable] = None):
    """Run the analysis chain on ``project``; return an AnalysisResult.

    Raises AnalysisError when the diagnostics report critical errors (after
    recording them in the result, attribute ``result``)."""
    if settings is None:
        settings = AnalysisSettings.from_project(project)
    if settings.pf_method not in POWERFLOW_METHODS:
        raise ValueError('Unknown power flow method: %r' % settings.pf_method)
    result = AnalysisResult(settings=settings)

    def report(fraction, message):
        if progress:
            progress(fraction, message)

    def step(name):
        result.steps.append(AnalysisStep(name))

    report(0, 'Building Base Model...')
    project.setup_base_model()
    step('setup_base_model')

    report(0.1, 'Building Power Model...')
    project.build_power_model()
    step('build_power_model')
    result.build_networkmodel = True

    if settings.diagnostics:
        report(0.2, 'Running Diagnostics...')
        messages = []
        listener = _diagnostics_listener(messages)
        project.subscribe(listener)
        try:
            ret_code = project.run_diagnostics()
        finally:
            project.unsubscribe(listener)
        step('run_diagnostics')
        result.diagnostics = messages[-1] if messages else None
    else:
        ret_code = constants.OK
    result.diagnostics_ret_code = ret_code

    if ret_code == constants.ERROR:
        error = AnalysisError('Diagnostics run returned critical errors')
        error.result = result
        raise error

    if settings.powerflow:
        if settings.pf_method in ('Power flow with diversity', 'Power flow'):
            report(0.3, 'Running Power Flow...')
            project.run_powerflow(settings.pf_method)
            step('run_powerflow')
        elif settings.pf_method == 'Time series':
            report(0.3, 'Running Time Series Power Flow...')
            project.run_powerflow_timeseries()
            step('run_powerflow_timeseries')
        result.run_powerflow = True

    if settings.sc_sym:
        report(0.4, 'Running Symmetric Short Circuit Calculation...')
        project.run_sym_sccalc()
        step('run_sym_sccalc')
        result.run_sc_sym = True

    if settings.sc_gf:
        report(0.5, 'Running Line to Ground Short Circuit Calculation...')
        project.run_linetoground_sccalc()
        step('run_linetoground_sccalc')
        result.run_sc_lg = True

    report(0.6, 'Updating Results...')
    project.update_results()
    step('update_results')
    result.completed = True
    log.info('run_analysis - analysis run')
    return result


def run_rules_check(project):
    """Run the electrical rules check; return its messages"""
    messages = []
    listener = _diagnostics_listener(messages)
    project.subscribe(listener)
    try:
        project.run_rulescheck()
    finally:
        project.unsubscribe(listener)
    return messages[-1] if messages else []
