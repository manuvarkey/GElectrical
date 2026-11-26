# 0015. Python 3.14 with Numba, and latest pandapower from PyPI through pixi

- Status: Accepted (owner decision 2026-11-26)
- Date: 2026-11-26
- Related: [ADR 0010](0010-python-environment-and-sidecar.md), [implementation plan M1b](../migration/implementation-plan.md#m1b--python-and-pandapower-upgrade), [regression baseline](../migration/regression-baseline.md)

## Context

`pixi.lock` currently pins Python 3.12.16, pandapower 3.2.1 (conda-forge),
numba 0.68.1 and WeasyPrint 69.0. The owner prefers the newest Python that
keeps Numba, and requires compatibility with the latest pandapower.

Checked on 2026-11-26:

| Package | Latest | Python support | conda-forge |
| --- | --- | --- | --- |
| pandapower | 3.5.6 (PyPI) | 3.10–3.14 | 3.2.1 only (noarch) |
| numba / llvmlite | 0.68.1 / 0.50.0 | 3.10–3.15 | builds for 3.11–3.15 |
| pygobject, pycairo, shapely, pydantic-core | — | — | builds for 3.11–3.15 |
| PyInstaller | 6.22.3 | — | builds for 3.11–3.14 |
| NumPy / pandas | 2.5.5 / 3.1.1 | — | pandapower 3.5.6 requires `numpy<2.5` and `pandas~=2.3`; the solver picks compatible older builds |

The newest Python supported by both pandapower and Numba (and by PyInstaller
on conda-forge) is **3.14**.

## Decision

- Target **Python 3.14** for the engine, backend, sidecar and (until
  retirement) the legacy GTK app.
- Keep compiled dependencies (NumPy, SciPy, pandas, Numba, Shapely, cairo,
  PyGObject, WeasyPrint natives) from **conda-forge**.
- Take **pandapower** (pure Python) from **PyPI** through pixi
  `[pypi-dependencies]`, pinned and recorded in `pixi.lock`. Its pure-Python
  dependencies come from conda-forge where available, otherwise PyPI through
  pixi. This is not "pip install": pixi resolves and locks it.
- Return pandapower to conda-forge once the feedstock publishes the version in
  use.
- The upgrade is a separate milestone **M1b**, after the baseline is captured
  on the current environment and before the M2 refactor.
- Code must use pandapower 3.5.x APIs; deprecated calls found during M1b are
  updated in `model/pandapower.py` with baseline evidence.

## Alternatives considered

- *Stay on conda-forge pandapower 3.2.1*: lags the latest release.
- *Wait for a conda-forge feedstock update*: delays the upgrade by an unknown time.
- *Python 3.15*: Numba supports it, pandapower does not declare support.

## Consequences

- AGENTS.md rule "do not use pip" is refined: PyPI packages are allowed only
  through pixi `[pypi-dependencies]` for pure-Python packages.
- The legacy packaging pins (`requirements.txt`, `setup.py`) are updated in M1b.
- Results may move between pandapower 3.2.1 and 3.5.x; M1b records every
  difference before re-baselining.

## Verification

M1b: environment solves on win-64, linux-64, osx-64, osx-arm64; legacy smoke
test passes on Python 3.14; baseline comparison 3.2.1 → 3.5.x documented in the
validation log; Numba JIT active in power flow (checked via pandapower's
`numba` option).
