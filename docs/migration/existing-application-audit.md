# Existing application audit

Status: **current implementation**, audited against `master` at commit `8b630f6`
(2026-11-26). Navigation: [migration index](README.md) ·
[feature inventory](feature-inventory.md) · [risks and decisions](risks-and-decisions.md)
· [documentation index](../README.md).

This page describes GElectrical as it exists today: a GTK3/PyGObject desktop
application in which engineering models, Cairo drawing and GTK widgets are
interleaved. Nothing on this page is a proposal. Proposals are in
[ARCHITECTURE.md](../../ARCHITECTURE.md) and [docs/architecture/](../architecture/).

## 1. Size and shape

| Area | Files | Lines (approx.) |
| --- | --- | --- |
| `gelectrical/__init__.py` (MainApp, MainWindow) | 1 | 1,210 |
| `gelectrical/misc.py` (constants, fields, GTK helpers, Cairo helpers, settings) | 1 | 1,800 |
| `gelectrical/model/` (project, drawing, network, pandapower, protection, rules, graph) | 7 | 5,550 |
| `gelectrical/elementmodel/` (element classes) | 18 | 5,870 |
| `gelectrical/view/` (GTK views and dialogs) | 8 | 2,950 |
| `gelectrical/undo.py` (vendored undo library) | 1 | 325 |
| `gelectrical/interface/` (Glade `.glade`/`.ui`) | 9 | n/a |
| `gelectrical/database/` (CSV + JSON equipment libraries) | 23 entries | 1.3 MB |
| `gelectrical/templates/` (Jinja2 report HTML/CSS) | 2 | n/a |
| `tools/smoke_test.py` | 1 | 113 |

There is no unit-test suite. `tools/smoke_test.py` is the only automated check.

## 2. Entry points and lifecycle

1. `gelectrical_launcher.py` configures logging (user log directory from
   `appdirs`), then runs `gelectrical.MainApp`.
2. `MainApp(Gtk.Application)` (`gelectrical/__init__.py`) registers the
   application actions `new`, `help`, `keyboardshortcuts`, `about`, `quit`,
   handles command-line file arguments (`do_open`, `do_command_line`) and
   creates one `MainWindow` per window.
3. `MainWindow.__init__` loads `interface/mainwindow.glade`, reads program
   settings from the user config directory, applies dark mode, builds the
   **element registry** (`program_state['element_models']`, a dict of
   `code → class`), populates the component sidebar, creates the
   `undo.Stack`, and constructs `ProjectModel`.
4. `program_state` is a shared mutable dict that carries the window, stack,
   notebook, field views, project, settings and analysis flags to every model
   and view. It is the main coupling mechanism of the code base.
5. Long operations (`run_command`) run in a worker thread with a
   `ProgressRevealer`; the worker calls model methods that also touch GTK views.

**Important coupling fact:** importing *any* `gelectrical.*` submodule first
executes `gelectrical/__init__.py`, which imports `gi`, requires GTK 3.0 and
imports every view. No engine module can currently be imported without GTK.

## 3. Project and drawing models

### ProjectModel (`model/project.py`)

- Owns `drawing_models` (one `DrawingModel` per sheet), the project `fields`
  (settings pages: Information, Simulation, Reports, Rules Check) and the
  `loadprofiles` dictionary.
- Also owns GTK objects: the drawing `Gtk.Notebook`, one `DrawingView` per
  sheet, the properties/results/messages/database views. Adding a page creates
  a `Gtk.Box` and a `DrawingView`.
- Orchestrates analysis (`setup_base_model`, `build_power_model`,
  `run_diagnostics`, `run_powerflow`, `run_powerflow_timeseries`,
  `run_sym_sccalc`, `run_linetoground_sccalc`, `update_results`,
  `run_rulescheck`), renumbering, cross-reference linking, report export
  (`export_pdf_report`), drawing export (`export_drawing`, Cairo PDF), JSON
  export, HTML pandapower report and element graph export.
- Opens GTK dialogs directly (`edit_loadprofiles` → `GraphViewDialog`,
  `view_protection_coordination` → `ProtectionViewDialog`).
- `self.fields = misc.default_project_settings` and
  `self.loadprofiles = misc.DEFAULT_LOAD_PROFILE` alias module-level globals
  without copying (see [defects](#12-defects-and-weaknesses)).

### DrawingModel (`model/drawing.py`)

- Holds `elements` (a list; **list index is the element identity**), sheet
  `fields` (name, page size, title block fields), a `Template` (border) and a
  `TitleBlock`.
- Implements selection, hit-testing (`cairo.Region`), insertion of a floating
  model, wire drawing state, assemblies, copy helpers and `draw_model`.
- Undoable mutations: `update_page_field`, `update_element_at_index`,
  `update_element_field_at_index`, `insert_element_at_index`, `delete_rows`.
- `set_model` instantiates elements from `program_state['element_models']` and
  re-links assembly children by `(page, index)`.

### Elements (`elementmodel/`)

`ElementModel` (`element.py`) is the base class. Each element class defines:

| Attribute / method | Meaning |
| --- | --- |
| `code`, `name`, `group`, `icon`, `tooltip` | Identity, palette group and SVG icon |
| `x`, `y`, `orientation` (`vertical`/`horizontal`) | Placement in drawing units |
| `ports` | Port offsets in grid multiples (`misc.M = 8` drawing units) |
| `fields` | Field dicts (`type`, `caption`, `unit`, `value`, `selection_list`, `status_enable`, `status_inactivate`, `decimal`, `validation_func`, `alter_structure`, `tooltip`, ...) |
| `res_fields` | Analysis results in the same field-dict shape, not persisted |
| `schem_model` | Imperative list of drawing primitives (`LINE`, `CURVE`, `ARC`, `CIRCLE`, `RECT`, `PATH`) in grid units |
| `text_model` | List of `[(x, y), mako_expr, display, size, weight, alignment]` |
| `render_element(context)` | Draws with Cairo/Pango and **computes `model_width/height` as a side effect** |
| `get_nodes(code)` | Ports that form electrical nodes, including cross-sheet references |
| `get_power_model(code, mode)` | pandapower element tuples per model mode |
| `set_text_field_value(code, value)` | Field change with side effects: selection lists, enabled flags, recalculation (`calculate_parameters`) |
| `get_model()` / `set_model()` | Persistence (values only; derived state is recomputed) |

Registered element codes (from `MainWindow.__init__`):

| Group | Codes |
| --- | --- |
| Switching devices | `element_switch`, `element_fuse`, `element_circuitbreaker`, `element_contactor`, `element_co_switch` |
| Sources | `element_grid`, `element_generator`, `element_staticgenerator`, `element_single_phase_staticgenerator` |
| Transformers | `element_transformer`, `element_transformer3w` |
| Components | `element_busbar`, `element_line`, `element_line_cable`, `element_line_custom`, `element_line_bus`, `element_impedance`, `element_inductance` |
| Loads | `element_load`, `element_asymmetric_load`, `element_single_phase_load`, `element_async_motor_3ph`, `element_async_motor_1ph`, `element_async_motor` (generator-based), `element_shunt`, `element_shunt_cap`, `element_ward`, `element_xward` |
| Miscellaneous | `element_reference`, `element_reference_box`, `element_display_text` |
| Non-palette | `element_wire`, `element_assembly`, `element_display_node` (analysis overlay), `element_template` (border and title block share this code) |

`misc.ADVANCED_ELEMENTS` hides six codes unless *advanced mode* is enabled.
Element-code groupings used by analysis and rules (`LINE_ELEMENT_CODES`,
`PROTECTION_ELEMENT_CODES`, `DAMAGE_ELEMENT_CODES`, ...) live in `misc.py`.

Domain calculations embedded in elements include IEC cable parameters and
ampacity derating (`LTCableIEC`), custom overhead-line geometry impedances
(`LTCableCustom`), bus-trunking parameters, conductor damage curves, transformer
parameters and damage/inrush curves, motor starting/damage curves, and breaker
and fuse protection settings (`switch.py`, with Shapely geometry).

## 4. Network connectivity and topology (`model/networkmodel.py`)

Connectivity is **geometric**: ports whose global coordinates coincide on the
same sheet belong to the same node. There are no explicit connection records.

1. `setup_base_elements` keys every element as `(page, index)`.
2. `setup_global_nodes` asks each element for `get_nodes(code)`. A node lists
   one or more ports; a 2-tuple port is a same-page `(x, y)`, a 3-tuple is
   `(page, x, y)`, and a 1-tuple `(ref,)` joins cross-reference elements that
   share the same reference string across sheets. Busbars and wires return all
   their ports for one node. Duplicate-port sets are merged with NetworkX
   connected components, and global nodes are renumbered without gaps.
3. `build_graph_model` builds a NetworkX graph with elements as edges and
   global nodes as nodes, with virtual source/sink nodes, with and without
   switch status.
4. Upstream/downstream queries (`get_upstream_element`, `get_downstream_element`,
   ...) are used by rules checks, protection coordination and reports.
5. `setup_node_elements` creates `element_display_node` overlay elements, which
   `ProjectModel.setup_base_model` inserts into the drawings under an undo
   group. **Running an analysis therefore mutates the drawing and the undo
   stack.** Display nodes are excluded when saving.
6. Busbar `DF` values populate `gnode_df_mapping` (diversity), and earthing data
   populate `gnode_res_mapping`.

## 5. pandapower integration (`model/pandapower.py`)

- `PandaPowerModel` builds three networks: power flow, line fault and ground
  fault (`POWER_MODEL_POWERFLOW/LINEFAULT/GROUNDFAULT`), mapping element tuples
  to `pp.create_*` calls (bus, switch, ext_grid, trafo, trafo3w, gen, sgen,
  asymmetric sgen, storage, impedance, line, dcline, load, asymmetric load,
  shunt, ward, xward).
- Diagnostics use `pp.diagnostic` (adapted for pandapower 3.x) and return
  message structures shown in the Messages pane.
- Power flow: `pp.runpp` or `pp.runpp_3ph`, optional discrete tap control;
  *Power flow with diversity* injects compensating static generators at busbars
  with `DF < 1`.
- Time series: 24 hourly steps using `ConstControl` and `DFData` from load
  profiles, then aggregates (max/avg) into result graphs.
- Short circuit: `sc.calc_sc` for `3ph` and `1ph`, `max` and `min` cases, using
  `lv_tol_percent`, fault impedance and optional impedance display.
- `update_results` copies node and element results into `res_fields`
  (field-dict shape with captions and units: presentation mixed with results).
- Exports: `pplot.to_html` and `pp.to_json`.

## 6. Protection models and curve editors

- `model/protection.py` (`ProtectionModel`) evaluates protection and damage
  curve definitions into upper/lower curves, Shapely `LineString`s and polygons
  in linear and log space. It supports IEC/IEEE/US inverse curves, thermal,
  I²t, RI, HV/FR fuse, poly-log and point-list curves, and selection criteria.
- Curve definitions are data structures that contain **Python expression
  strings** (for example `"3600 if f.In <= 63 else 2*3600"`). They come from the
  equipment database JSON and are **copied into each element's saved fields**
  (`pcurve_l`, `pcurve_g`, `dcurve`). They are evaluated with `eval()`.
- `get_protection_model` / `get_thermal_protection_models` build parametric
  breaker models used by `switch.py`.
- `view/protection.py` (`ProtectionViewDialog`) is the coordination editor:
  line/ground mode switch, combined Matplotlib plot of device bands, damage and
  starting curves, disconnection-time limit and node fault-current markers,
  per-element parameter editing and export of settings to a spreadsheet.
- `view/graph.py` provides `GraphView` (Matplotlib embedded via
  `backend_gtk3agg`, click to add/remove points, cycle active curve),
  `GraphViewDialog` (load-profile editor with database import) and `GraphImage`
  (SVG images for reports). `model/graph.py` (`GraphModel`) stores curves.

## 7. Electrical rules check (`model/rulescheck.py`)

Rules are tuples of expression strings evaluated with `eval()` against element
wrappers (`e.f.<field>`, `e.r.<result>`), settings (`ss`, `sr`) and
upstream/downstream elements. Results become pass/fail message structures for
the Messages pane. `electrical_rules` defines 15 rules: line loading and loss;
protection of lines, transformers and motors by upstream devices; line and load
disconnection time; CPE sizing for fault current; transformer and motor inrush
coordination; breaker breaking capacity against fault level; breaker
coordination with upstream device; load voltage drop; and three-phase loads on
three-phase lines (see [user docs](../features.md)). Rules depend on Shapely
geometry operations exposed by `ProtectionModel.contains/get_time/get_current`.

## 8. Equipment databases (`gelectrical/database/`)

- Semicolon-separated CSV catalogues: `cable_iec.csv`, `cb.csv`, `fuse.csv`,
  `line*.csv`, `motor*.csv`, `transformer*.csv`, `load_profiles.csv`.
- Per-manufacturer folders of protection-curve JSON (`acb_*`, `mccb_*`,
  `mcb_*`, `fuse_*`). CSV rows reference them as Python tuple strings
  (`('mcb_lnt', '', 'lnt_mcb_b.json')`), parsed with `eval()` in
  `view/database.py`.
- `misc.open_library` resolves a user library directory first, then the bundled
  folder. Sources for the CSVs are the `.ods` files in `source/`.
- `DatabaseView` is a searchable tree dialog that copies matching field values
  into the selected element (undoable).

## 9. Persistence (`.gepro`)

Documented in detail in [project format](../architecture/project-format.md).
In short: a ZIP containing `document.json` (`_file_version`, `_files`,
`proj_drawing_names`, `proj_fields`), one `proj_drawing_page_N.json` per sheet
and `proj_loadprofiles.json`. Only field values and types are stored; field
metadata is recreated from code. `MainWindow.on_save` writes the ZIP in place
(not atomic). Loading checks `_file_version == 'GELECTRICAL_FILE_REFERENCE_VER_0'`.

## 10. Undo/redo

`gelectrical/undo.py` is a vendored generator-based undo library. Model methods
decorated with `misc.undoable` apply a change, `yield` a description and then
perform the inverse. `misc.group(self, desc)` batches actions. The stack is
per window (`program_state['stack']`), supports `savepoint()`/`haschanged()`
for dirty tracking and is cleared on open. Field edits go through
`misc.get_undoable_set_field(_multiple)`, which also restores derived fields
reported by `set_text_field_value`.

## 11. Reports, export and printing

- **Report**: `ProjectModel.export_pdf_report` renders `templates/report.html`
  with Jinja2 (no autoescape) and converts it to PDF with WeasyPrint. Sections:
  elements, bill of quantities, load profiles, analysis options and results,
  optional graphs (Matplotlib `GraphImage` SVG). Controlled by project
  settings *Reports*.
- **Drawing PDF**: `export_drawing` renders every sheet to a `cairo.PDFSurface`
  with metadata; dark-mode colours are reset during export.
- **Printing**: `Gtk.PrintOperation` draws pages with the same Cairo code.
- **Analysis export folder** (optional): pandapower HTML, element graph HTML,
  pandapower JSON, report HTML/PDF and drawing PDF, produced in parallel threads.
- **Spreadsheets**: `misc.Spreadsheet` (openpyxl) for protection-settings export
  and data import; `misc.SpreadsheetDialog` (GTK) for tabular entry.

## 12. Defects and weaknesses

These are existing issues, recorded separately from migration tasks. Fixing any
of them may change behaviour and needs an explicit decision and verification.

| ID | Issue | Location | Impact |
| --- | --- | --- | --- |
| D1 | `eval()` of expression strings stored in project files and databases | `model/protection.py`, `model/rulescheck.py`, `view/database.py`, `misc.py`, `view/field.py` | Opening an untrusted `.gepro` can execute arbitrary code; unacceptable once MCP or file association exposes it |
| D2 | `pickle` round trip through the system clipboard | `view/drawing.py` copy/paste | Pasting crafted clipboard text executes code |
| D3 | Mako templates for symbol text (`${int(length_km*1000)}`) | `elementmodel/*` | Templates are code-defined today, but the mechanism executes Python; unsuitable for declarative symbols |
| D4 | Project defaults alias module globals (`default_project_settings`, `DEFAULT_LOAD_PROFILE`) | `model/project.py` | Edits leak into later "new project" instances in the same process; blocks multi-session backends |
| D5 | Element identity is the list index `(page, index)`; assemblies store child indices | `model/drawing.py`, `elementassembly.py` | Fragile across deletes/reorders; unsuitable for MCP references and frontend diffing |
| D6 | Non-atomic save (ZIP written over the target) | `__init__.py:on_save` | A crash during save can corrupt the project |
| D7 | Analysis mutates the drawing (display nodes) inside the undo stack | `model/project.py:setup_base_model` | Undo history and dirty state change when only analysing |
| D8 | Field-load order can reset values: loading a field that changes a dependent selection list may coerce an already loaded value | `set_model` + `set_field_selection_list` | Possible silent value change on load; must be measured by round-trip tests |
| D9 | Worker threads update GTK widgets and models during analysis | `run_command`, `ProjectModel.update_results` | Thread-safety risk; analysis cannot be isolated |
| D10 | Report HTML not autoescaped; WeasyPrint resolves URLs in content | `export_pdf_report` | User text can inject markup or reference local files in reports |
| D11 | `requirements.txt` pins pandapower 2.14.9 while `pixi.toml` requires `>=3.2` | packaging | Legacy packaging builds a different solver version |
| D12 | Source headers state GPL-2.0-or-later; `LICENSE` is GPLv3 text | all modules | Licence statement inconsistent; see [ADR 0013](../decisions/0013-licensing.md) |
| D13 | Duplicate `code` for `Template` and `TitleBlock` (`element_template`) | `elementmodel/template.py` | Breaks the "unique code" invariant if templates become registry entries |
| D14 | Element registry built inside the GTK window | `__init__.py` | No headless registry; must be duplicated by any other front end |
| D15 | Mutable default argument `alter_values_dict={}` shared between fields | `misc.get_field_dict` | Latent shared-state bug |

## 13. GTK, Cairo and Matplotlib dependency map

| Module | Direct GUI dependency | Nature |
| --- | --- | --- |
| `gelectrical/__init__.py` | Gtk, Gdk, GLib, Gio, GdkPixbuf | Application shell; imported by every submodule |
| `misc.py` | Gtk, Gdk, GLib, Pango, PangoCairo, GdkPixbuf, cairo | Mixed: constants and field helpers (engine) with dialogs, spreadsheet dialog, progress, splash, text drawing (UI) |
| `elementmodel/*.py` | `gi.repository` (PangoCairo, Gtk, Gdk), cairo | Rendering and extents inside domain classes |
| `model/drawing.py` | Gtk, Gdk, cairo | Hit-testing with `cairo.Region`; drawing |
| `model/graph.py` | Gtk, Gdk, cairo imports (unused in logic) | Incidental |
| `model/project.py` | Gtk, Gdk, GLib, cairo; imports `view.drawing`, `view.graph`, `view.protection` | Owns views and dialogs |
| `model/networkmodel.py` | Matplotlib (lazy, export only) | Optional export |
| `model/pandapower.py`, `protection.py`, `rulescheck.py`, `undo.py` | none directly | GUI-free logic, but import `misc` (and therefore GTK) |
| `view/*`, `interface/*` | GTK, Matplotlib GTK3Agg backend | UI only |

Indirect dependencies: every engine module imports `misc`, which imports GTK;
`GraphImage` (report graphs) lives in `view/graph.py`, which imports the
Matplotlib GTK backend at module level, so report generation also requires GTK.

## 14. Tooling, tests and distribution

- **Development:** pixi (`pixi.toml`, `pixi.lock`), Python 3.12, conda-forge
  GTK/PyGObject/pandapower/WeasyPrint; tasks `start` and `smoke`.
- **Tests:** `tools/smoke_test.py` builds an unshown `MainWindow`, opens each
  sample project and runs diagnostics, power flow, both short-circuit
  calculations, rules check and exports. It checks that outputs exist, not
  their values. It needs a display (`xvfb-run` on Linux CI). No CI workflow is
  committed.
- **Sample projects:** `sample_files/sample.gepro` (2 sheets),
  `short_circuit_calculation_kerala_insp/kerala_inspectorate_sample.gepro` and
  `cable_voltage_drop_test/voltage_test.gepro` (with a notebook and reference
  PDFs). They do not cover every element type.
- **Distribution:** Windows NSIS installer from PyInstaller (`installer.nsi`,
  `pyinstaller_spec.spec`), Flatpak (`com.kavilgroup.gelectrical.json`, GNOME 46
  runtime, builds GEOS and Python dependencies), Snap (`snapcraft.yaml`, core22),
  `setup.py`/`MANIFEST.in`. User manual on Read the Docs (Sphinx + MyST, `docs/`).
- **Assets:** `source/` holds `.ods` database sources and artwork;
  `mockups/` holds a Xournal++ planning sketch (handwritten, 5 pages).

## 15. Major technical constraints for migration

1. Engine import requires GTK until `gelectrical/__init__.py`, `misc.py` and the
   element rendering code are split.
2. Element geometry (extents) is a side effect of Cairo/Pango rendering.
3. Connectivity is defined only by coordinate coincidence and reference strings.
4. Identity is positional; the file format stores positions.
5. Curve and rule semantics are expressed as Python expression strings that are
   evaluated with `eval()`; a safe evaluator must reproduce them exactly.
6. Field change side effects (selection lists, enabled flags, recalculation)
   live inside element classes and must remain the single source of truth.
7. Results are presentation-shaped field dicts, not typed result records.
8. The undo mechanism is inverse-operation based and spread across models.
9. Report graphs depend on Matplotlib through a GTK module.
10. Packaging must ship the scientific stack (NumPy, SciPy, pandas, Numba,
    llvmlite, Shapely, NetworkX, pandapower) and WeasyPrint's native libraries.
