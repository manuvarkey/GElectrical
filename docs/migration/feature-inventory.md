# Feature inventory and parity checklist

Status: **current implementation inventory** plus migration tracking.
Navigation: [migration index](README.md) · [audit](existing-application-audit.md)
· [implementation plan](implementation-plan.md) · [documentation index](../README.md).

Every user-visible feature of the GTK application is listed here. The modern
application reaches parity only when every row is either **Done** (verified in
the modern app, with evidence linked from the validation log) or **Dropped**
(explicitly approved by the repository owner, with a reason). Nothing is removed
silently.

Columns: **ID** (stable, cite in commits/tests), **Feature**, **Current
behaviour/location**, **Target milestone** ([plan](implementation-plan.md)),
**Status** (`Not started`, `In progress`, `Done`, `Dropped`, `Changed`).
Update status only with evidence.

## A. Application and project management

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| A01 | New project | App action `new`; opens a new window with default settings | M9 | Not started |
| A02 | Open project | Popover with recent projects, *Other Projects...* file chooser; confirms discard of unsaved changes | M9 | Not started |
| A03 | Open from command line / file manager / drag-and-drop | `do_open`, `do_command_line`, `drag_data_received` on window | M9 | Not started |
| A04 | Recent projects list | Stored in program settings; shown in open popover | M9 | Not started |
| A05 | Save (`Ctrl+S`) | Writes `.gepro` ZIP in place; first save prompts for path | M9 | Not started |
| A06 | Save As | File chooser with overwrite confirmation, `.gepro` extension enforced | M9 | Not started |
| A07 | Unsaved-change guard on open/new/exit | Yes/No dialog when `stack.haschanged()` | M9 | Not started |
| A08 | Window title shows project file | `set_title` | M9 | Not started |
| A09 | Multiple windows | One `MainWindow` per *New* action | M9 | Changed (proposed: document tabs/rail, see [UI guidelines](../ui-guidelines.md)) |
| A10 | Project settings dialog | Pages Information, Simulation, Reports, Rules Check (`FieldViewDialog`), undoable | M11 | Not started |
| A11 | Program settings dialog | Defaults (title block fields), Interface (dark theme, advanced mode, show graphs, drawing/graph/report fonts), Paths (user library) | M11 | Not started |
| A12 | Bad font settings warning | `check_for_bad_font_settings` warns about unavailable fonts | M11 | Not started |
| A13 | Dark theme | Program setting; adjusts drawing colours; restart required | M6 | Not started |
| A14 | Advanced mode | Hides `ADVANCED_ELEMENTS` from palette unless enabled | M10 | Not started |
| A15 | Help | Opens online documentation | M9 | Not started |
| A16 | Keyboard shortcuts window | `shortcuts-overlay.ui` | M10 | Not started |
| A17 | About dialog | `aboutdialog.glade` | M9 | Not started |
| A18 | Status/info bar messages | Info/warning/error infobar with timeout | M6 | Not started |
| A19 | Progress display for long operations | `ProgressRevealer` with messages and fraction | M9 | Not started |
| A20 | Splash screen | `SplashScreen` at startup | M14 | Not started (may be dropped if startup is fast) |
| A21 | Show/hide left and right panes | Header bar toggles | M6 | Not started |
| A22 | Logging to user log directory | `gelectrical_launcher.py` | M4 | Not started |

## B. Schematic capture

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| B01 | Component palette | Grouped list of registered elements with icons, tooltips and search filter | M10 | Not started |
| B02 | Insert element | Floating model follows pointer; grid snap; click to place | M10 | Not started |
| B03 | Insert-time properties | Left pane switches to insert view with fields marked `status_floating` | M10 | Not started |
| B04 | Rotate while inserting (`R`) | Toggles vertical/horizontal orientation | M10 | Not started |
| B05 | Cycle attachment port while inserting (`C`) | Changes which port follows the pointer | M10 | Not started |
| B06 | Draw wire (`Ctrl+W` or click on a port) | Click points on grid; double/middle click or ending on a port finishes; right click/Escape cancels | M10 | Not started |
| B07 | Wire junctions and branches | Coincident ports join nodes; T-connections by ending a wire on another wire's port or busbar port | M10 | Not started |
| B08 | Select (click), toggle with Shift, box select | `update_select`, `MODE_SELECTION` | M10 | Not started |
| B09 | Select all (`Ctrl+A`), deselect (`Escape`) | Drawing view key handler | M10 | Not started |
| B10 | Move element by drag | GTK drag on drawing area moves **one** element (not assemblies): it is deleted and re-inserted as a floating model at the end of the element list; attached wires are not moved | M10 | Not started |
| B11 | Delete (`Delete`) | Undoable `delete_rows` | M10 | Not started |
| B12 | Cut / copy / paste (`Ctrl+X/C/V`) | Pickled elements via clipboard; paste becomes a floating model | M10 | Changed (safe clipboard format required, see D2) |
| B13 | Group into assembly (`Ctrl+G`) | `add_assembly_from_selection`; assembly box moves/selects children | M10 | Not started |
| B14 | Busbar with multiple ports and adjustable width | `BusBar.set_model_from_param` recomputes ports | M10 | Not started |
| B15 | Cross-reference elements and linking | `element_reference(_box)`; *Link* dialog selects targets on other sheets; sheet numbers auto-filled (`reg_refs_sheets`) | M10 | Not started |
| B16 | Renumber references | Dialog: all / new only / selected only | M10 | Not started |
| B17 | Text display element | Multiline notes with optional fill/border | M10 | Not started |
| B18 | Multiple sheets | Notebook tabs: new sheet (`Ctrl+N`, copies sheet fields), delete sheet, reorder by drag; undoable | M10 | Not started |
| B19 | Sheet properties and title block | Page size (paper sizes), title, drawing number, sheet no., type, status, revision, date; project-wide title fields | M10 | Not started |
| B20 | Drawing border/template | `Template` element per sheet | M10 | Not started |
| B21 | Zoom in/out (`Ctrl++`/`Ctrl+-`, `Ctrl`+scroll), zoom label | Scale 0.4–2.6 in 0.2 steps; scroll position kept per sheet | M10 | Not started |
| B22 | Grid display and snapping | `GRID_WIDTH = 16` drawing units | M10 | Not started |
| B23 | Dynamic element labels | Text model shows field values (ref, rating, length, ...) | M10 | Not started |
| B24 | Out-of-service rendering | Inactive colour for elements with `in_service = False` | M10 | Not started |
| B25 | Undo / redo (`Ctrl+Z`, `Ctrl+Shift+Z`) | Header bar buttons with action descriptions | M10 | Not started |
| B26 | Selection highlighting by messages | Selecting a message selects related elements/ports (warning colour) | M12 | Not started |

## C. Properties, results and databases

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| C01 | Properties pane | Field editor: str, float, int, multiline, bool, selection lists with images, font, path, graph, data, heading; units; tooltips; validation with arithmetic entry | M11 | Not started |
| C02 | Multi-selection editing | Same-type elements; mismatched values shown as `<multiple values>` | M11 | Not started |
| C03 | Derived field updates | Selection lists, enabled states and calculated values update on change | M11 | Not started |
| C04 | Click-to-edit messages | `click_to_edit_message` confirmation before editing | M11 | Not started |
| C05 | Results pane | Read-only `res_fields` of selected element, including result graphs | M12 | Not started |
| C06 | Messages pane | Diagnostics and rules-check messages with selection callback | M12 | Not started |
| C07 | Load values from database | Searchable tree dialog per element `database_path`; Enter/double click applies; undoable | M11 | Not started |
| C08 | User library directory | Overrides bundled database files by name | M11 | Not started |
| C09 | Graph fields in properties | Inline graph preview for `graph`/`data` fields (setting *show graphs*), open editor dialog | M11 | Not started |
| C10 | Path fields | Activating a read-only path field copies the path to the clipboard and opens the file | M11 | Not started |

## D. Load profiles and protection

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| D01 | Load profile editor | Add, delete, edit, rename profiles; 24 hourly diversity values; click to edit points; import from `load_profiles.csv`; undoable as one change | M11 | Not started |
| D02 | Load profile selection on loads/sgens | `load_profile` field selection list | M11 | Not started |
| D03 | Protection coordination view | Select protection/damage elements and nodes, open dialog; line/ground mode | M11 | Not started |
| D04 | Coordination plot | Log-log time-current plot: device bands (hatched), cable/transformer/motor damage and starting curves, max disconnection time, node fault currents | M11 | Not started |
| D05 | Edit protection parameters in coordination view | Per-element parameter fields, live curve update | M11 | Not started |
| D06 | Export protection settings to spreadsheet | `export_settings_spreadsheet` (openpyxl) | M11 | Not started |
| D07 | Protection/damage curve editor for elements | `pcurve_l`, `pcurve_g`, `dcurve` fields via database and graph views | M11 | Not started |

## E. Analysis

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| E01 | Analysis settings dialog | Diagnostics, asymmetric PF, PF on/off, method, SC symmetric, SC line-ground, export results and folder | M12 | Not started |
| E02 | Diagnostics | `pp.diagnostic`; critical errors abort the run | M12 | Not started |
| E03 | Power flow | Balanced and 3-phase (`runpp_3ph`) with tap control | M12 | Not started |
| E04 | Power flow with diversity | Busbar DF via compensating sgens | M12 | Not started |
| E05 | Time-series power flow | 24 h from load profiles; aggregated results and graphs | M12 | Not started |
| E06 | Symmetric short circuit (IEC 60909, max/min) | `sc.calc_sc` 3ph | M12 | Not started |
| E07 | Line-to-ground short circuit (max/min) | `sc.calc_sc` 1ph with earthing resistances | M12 | Not started |
| E08 | Display short-circuit impedances | Simulation setting | M12 | Not started |
| E09 | Node display elements with results | Overlay node markers on drawings; results per node | M12 | Changed (approved 2026-11-26: results overlay, not document elements) |
| E10 | Clear results | Removes node elements and results (undoable) | M12 | Not started |
| E11 | Electrical rules check | Requires PF + both SC runs; 15 rules; messages pane | M12 | Not started |
| E12 | Mixed earthing systems (TN-S/TN-C/TT/IT) | Element fields and `gnode_res_mapping` | M12 | Not started |
| E13 | Custom-geometry line parameters | `LTCableCustom.calculate_parameters` | M11 | Not started |
| E14 | IEC cable parameters and derating | `LTCableIEC` | M11 | Not started |

## F. Output

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| F01 | Export drawing PDF | All sheets, vector, PDF metadata | M12 | Not started |
| F02 | Print drawings | `Gtk.PrintOperation` with page selection | M12 | Changed (approved 2026-11-26: print via generated PDF and OS viewer) |
| F03 | Project report (HTML + PDF) | Jinja2 + WeasyPrint; sections controlled by *Reports* settings | M12 | Not started |
| F04 | Report graphs | Matplotlib SVG images | M12 | Not started |
| F05 | Bill of quantities in report | Aggregated element quantities | M12 | Not started |
| F06 | Analysis export folder | pandapower HTML, element graph HTML, pandapower JSON, report, drawing | M12 | Not started |
| F07 | pandapower JSON export | `pp.to_json` | M12 | Not started |

## G. Platform and distribution

| ID | Feature | Current behaviour / location | Target | Status |
| --- | --- | --- | --- | --- |
| G01 | Windows installer | NSIS + PyInstaller | M14 | Not started |
| G02 | Flatpak (Flathub) | GNOME runtime manifest | M14 | Not started |
| G03 | Snap | core22 | M14 | Not started |
| G04 | `.gepro` file association and MIME type | Desktop file, appdata | M14 | Not started |
| G05 | osifont for schematics | Recommended user install | M14 | Changed (approved 2026-11-26: bundle osifont, GPL-3.0 with font exception) |

## Parity acceptance

A row moves to **Done** when:

1. The modern UI exposes the behaviour, including keyboard access.
2. Engineering outcomes match the [regression baseline](regression-baseline.md)
   within the stated tolerances.
3. A test exists at the appropriate level ([testing guide](../testing.md)).
4. The validation log records the evidence (date, commit, check).

`Changed` rows need an approved decision record in [decisions](../decisions/).
