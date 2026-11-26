# Regression baseline

Status: sections 1–6 define the baseline; section 7 is **current** (implemented
in milestone M1 on 2026-11-26, Python 3.12.16, pandapower 3.2.1).
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

## 7. Implementation (current, M1)

| Item | Location |
| --- | --- |
| Capture harness | `tools/baseline/capture.py` (one subprocess per project), `tools/baseline/legacy.py` (drives `MainWindow`) |
| Canonical form and tolerances | `tools/baseline/canonical.py` (section 3 table as constants) |
| Comparison | `tools/baseline/compare.py` (CLI and test helper) |
| Coverage project generator | `tools/baseline/build_projects.py` |
| Coverage and edge projects | `tests/projects/*.gepro`, `tests/projects/edge/*.gepro` |
| Baseline | `tests/baseline/<project>/`, `tests/baseline/environment.json` |
| Test | `tests/test_baseline.py` |
| CI | `.github/workflows/quality.yml` |

Commands:

```bash
xvfb-run -a pixi run -e test test                    # capture afresh and compare
xvfb-run -a pixi run -e test baseline-capture --out /tmp/cap
pixi run -e test python tools/baseline/compare.py /tmp/cap tests/baseline
xvfb-run -a pixi run -e test build-test-projects     # regenerate tests/projects
```

`baseline-capture` without `--out` overwrites `tests/baseline/`. Do this only
for an approved re-baseline (section 6), never to make a change pass.

### 7.1 What a capture does

For each project, in fresh `MainWindow` instances with isolated XDG
directories, `GTK_THEME=Adwaita:light` and `LC_ALL=C.UTF-8`:

1. Open; write `model.json`, `curves.json` and `d8.json` (file values compared
   with values after load). Save with `MainWindow.on_save`, reopen in a new
   window and write `roundtrip.json` (`{"equal_to_model": true}` when the
   canonical model is unchanged, otherwise the full model).
2. Run six analysis modes, each in a new window: `pf_bal`, `pf_3ph`
   (*Power flow*), `pfdiv_bal`, `pfdiv_3ph` (*Power flow with diversity*),
   `ts_bal`, `ts_3ph` (*Time series*), each followed by symmetric and
   line-to-ground short circuit, `update_results` and the rules check. The
   chain stops at the first exception, as the GUI worker does; the exception is
   recorded in `<mode>/status.json` together with pandapower warnings.
   `topology.json`, `pp_input.json` and `diagnostics.json` come from `pf_bal`.
3. In the mode that matches the project's saved settings: export the report
   (`report.txt`) and rasterize every sheet (`drawing_<n>.png`).
4. `renumber.json`: each renumber mode, then undo.
5. `undo.json`: modify a field, insert a load, delete element 0, renumber all,
   run `setup_base_model`; then undo all, redo all, undo all.

### 7.2 Deviations from sections 2 and 4

- `pp_<mode>.json` is one `pp_input.json` with `powerflow`, `linefault` and
  `groundfault` nets. Bus references are canonical node keys; each row carries
  the source element (`__element`).
- `timeseries.json` is not separate: time-series aggregates are the
  `res_fields` in `ts_*/results.json` and `ts_*/node_results.json`.
- `sc.json` holds the pandapower `res_*_sc` tables left by the legacy calls
  (the `min` case, which runs last); the `max` values are in the result
  fields.
- `report.txt` is extracted from the generated `report.html` (the WeasyPrint
  input), not from the PDF: the environment has no PDF text extractor. The PDF
  is still generated (`status.json` → `report_pdf`).
- Drawings are rendered with the same `DrawingModel.export_drawing` code onto
  a Cairo image surface at 150 DPI. PNG comparison is skipped (with a warning)
  when the resolved fonts in `environment.json` differ from the baseline.
- Undo snapshots store element codes/references and the number of storage
  model differences against the initial model (floats compared with the
  field tolerance) instead of full models; `undo.json` contains no floats.
  `status.json` tracebacks list `file:function` frames without line numbers.
  Both keep these artefacts independent of last-bit float results and of
  unrelated code moves (the first CI run showed ~1e-14 differences in curve
  points between machines, inside tolerance everywhere else).
- Node keys are `N[...]` (sorted local node ids, e.g. `(0, 3):1`); virtual
  source/sink nodes are `T[<element>]`.
- The legacy analysis runs on the model as loaded, without drawing the sheets
  first. Ports that are only updated when an element is drawn (for example
  bus bar port counts) therefore come from the file.

### 7.3 Coverage

All 32 registered element codes appear in at least one project
(`element_display_node` through analysis). `element_async_motor`
(`generator.Motor`) is defined but not registered, so it cannot be loaded and
is not covered. Projects: 3 samples, 8 coverage projects (`cov_*`), 6 edge
projects (`edge/*`).

Analysis outcomes recorded in the baseline (legacy behaviour, not harness
errors):

| Project | Outcome |
| --- | --- |
| `cov_impedance` | Line-to-ground SC fails: `KeyError: 'gf0_pu'` (zero-sequence impedance columns expected by pandapower 3.2.1) |
| `cov_xward` | Line-to-ground SC fails: `FloatingPointError` in `makeYbus` (zero sequence) |
| `cov_trafo3w` | Line-to-ground SC fails: `AttributeError` (no vector group for `trafo3w`); 3-phase PF not implemented for `trafo3w` in pandapower |
| `cov_generation` | 3-phase PF fails with a synchronous generator: `KeyError: 'res_gen_3ph'` |
| `cov_radial_lv`, `cov_advanced` | 3-phase PF does not converge |
| `edge/empty`, `edge/islanded` | Diagnostics return critical errors; analysis stops |
| `cov_generation`, `cov_static_generation`, `edge/missing_loadprofile` | Report export fails (`KeyError`) because a load profile value is not a key of the project load profiles (static generators default to `0`) |

Every analysis mode completes in at least one project.

### 7.4 Known gaps

Not covered by the M1 baseline: the protection coordination dialog and
settings spreadsheet export, database application to elements, clipboard
copy/paste, printing, pandapower HTML/JSON and element-graph exports, link
references dialog, 60 Hz projects, OLTC tap control (`oltc=True`), page
add/remove/reorder undo, and the legacy UI itself. The Windows CI job runs
only the smoke test.
