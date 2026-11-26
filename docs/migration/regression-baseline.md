# Regression baseline

Status: **proposed** (to be implemented in milestone M1, before any refactor).
Navigation: [migration index](README.md) · [testing guide](../testing.md) ·
[implementation plan](implementation-plan.md#m1--regression-baseline-and-test-scaffold).

The baseline is the numerical and functional oracle for the migration. It is
captured from the **current GTK-coupled code** so that every later refactor is
compared against the behaviour users have today.

## 1. Inputs

| Set | Location | Purpose |
| --- | --- | --- |
| Sample projects | `sample_files/**/*.gepro` (3 files) | Real user-style projects |
| Coverage projects | `tests/projects/*.gepro` (to create) | Every registered element code, every analysis mode, earthing types, cross-sheet references, assemblies, out-of-service elements, multiple load profiles, advanced elements |
| Edge projects | `tests/projects/edge/*.gepro` (to create) | Empty project, unconnected ports, islanded network, missing load profile, unusual field values, many sheets |
| Malicious projects | `tests/projects/malicious/*.gepro` (M3) | Must be rejected safely after M3; excluded from the legacy capture |

Coverage gaps in the current samples (to close with coverage projects):
generators, static generators (1ph/3ph), motors (1ph/3ph, generator-based),
3-winding transformers, impedance/inductance, shunts, ward/xward, changeover
switch, contactor, asymmetric loads, 3-phase (asymmetric) power flow,
time-series power flow, power flow with diversity, TT/IT earthing.

## 2. Captured artefacts per project

Stored as canonical, sorted JSON under `tests/baseline/<project>/`.

| Artefact | Content | Comparison |
| --- | --- | --- |
| `model.json` | Canonical project model after load: sheets, page fields, elements (code, position, orientation, ports, all field values, derived field state: selection lists, enabled flags) | Exact (floats via tolerance table) |
| `roundtrip.json` | Model after save → load | Must equal `model.json` exactly |
| `topology.json` | Node sets as sorted lists of `(page, index, port)` plus reference joins; graph edges; upstream/downstream maps for each element | Exact set equality (node numbering normalized) |
| `pp_<mode>.json` | pandapower input tables for power flow, line-fault and ground-fault nets (bus, line, trafo, trafo3w, switch, ext_grid, gen, sgen, load, shunt, impedance, ward, ...), columns sorted | Numeric tolerance |
| `diagnostics.json` | Diagnostic message structures | Exact text, sorted |
| `pf.json` | `res_bus`, `res_line`, `res_trafo`, ... for each power flow method enabled | Tolerance |
| `timeseries.json` | Aggregated time-series outputs used by results and graphs | Tolerance |
| `sc_sym.json`, `sc_lg.json` | Short-circuit results (max/min) per bus/branch | Tolerance |
| `results.json` | Every element's `res_fields` after `update_results` (values, units, captions) | Tolerance for values; exact for captions/units |
| `node_results.json` | Node display results | Tolerance |
| `rules.json` | Rules-check pass/fail sets per rule caption and element | Exact |
| `curves.json` | Evaluated protection (line/ground) and damage curves per element, polygon vertices | Tolerance |
| `renumber.json` | Element references after each renumber mode | Exact |
| `undo.json` | Scripted action sequences with undo labels, model after each undo/redo | Exact |
| `report.txt` | Text extracted from the report PDF (dates removed) | Exact after normalization |
| `drawing_*.png` | Each sheet of the drawing PDF rasterized at fixed DPI | Pixel diff threshold |
| `environment.json` | Python, pandapower, NumPy, SciPy, pandas, Shapely, NetworkX versions, pixi lock hash, platform | Informational; mismatch reported |

## 3. Tolerances

Values are compared as `|a - b| <= abs_tol + rel_tol * |b|`.

| Quantity | abs_tol | rel_tol | Rationale |
| --- | --- | --- | --- |
| Element field values from element calculations (impedances, ratings, derating) | 1e-12 | 1e-9 | Deterministic float arithmetic |
| pandapower input parameters | 1e-12 | 1e-9 | Copied from fields |
| Bus voltage magnitude (p.u.) | 1e-8 | 0 | Newton-Raphson convergence tolerance (pandapower default 1e-8 MVA mismatch) |
| Voltage angle (degrees) | 1e-6 | 0 | Solver tolerance |
| Branch currents (kA), powers (MW/Mvar) | 1e-9 | 1e-6 | Solver tolerance relative to magnitude |
| Loading, losses, voltage drop (%) | 1e-6 | 1e-6 | Derived from the above |
| Short-circuit currents (kA), impedances (Ω) | 1e-9 | 1e-7 | Direct linear algebra |
| Curve points (A, s) | 1e-12 | 1e-9 | NumPy evaluation |
| Polygon vertices | 1e-9 | 1e-9 | Shapely operations |
| Drawing raster | — | ≤ 0.1 % differing pixels at 150 DPI after anti-aliasing tolerance | Font hinting differences |

Tolerances apply to repeat runs in the same environment. When dependency
versions change (for example a pandapower update), differences larger than the
tolerances are investigated, explained in the validation log and the baseline
is regenerated only with an explicit note of what moved and why. A baseline is
**never** regenerated to make a refactor pass.

## 4. Normalization rules

- Sort dict keys and set members; convert NumPy types to Python numbers.
- Replace global node numbers by canonical node keys (sorted port tuples).
- Remove timestamps, file paths, program versions and creation dates.
- Represent `NaN`/`inf` explicitly (`"NaN"`, `"Infinity"`).
- Record pandapower warnings separately; they are not failures.

## 5. Use during migration

| Milestone | Check |
| --- | --- |
| M1 | Capture twice on the current environment (Python 3.12, pandapower 3.2.1); must be identical within tolerance |
| M1b | Compare after the Python 3.14 / latest pandapower upgrade; explain every difference; re-baseline after owner approval |
| M2 | Headless engine output equals baseline (legacy GTK app also still equal) |
| M3 | Curves, rules and results unchanged with the safe evaluator |
| M4 | Service-driven load/analyse/save equals baseline; service-saved files load in legacy app with equal results |
| M9–M12 | Values displayed in the UI equal baseline (Playwright reads displayed values for selected elements) |
| M13 | MCP-built network reproduces baseline results |

## 6. Intentional changes

An intentional change of engineering behaviour (for example fixing D8 or
changing display-node handling) requires:

1. An ADR describing the change and the engineering justification.
2. A before/after table of affected values on the sample and coverage projects.
3. Owner approval.
4. A baseline update in the same pull request, referencing the ADR.
