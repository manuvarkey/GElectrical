# Project format (`.gepro`)

Status: sections 1–3 describe the **current implementation**; section 4 is
**proposed** policy; sections 5–6 are current in the application services
since M4 (the legacy GTK app is unchanged). Navigation: [index](../README.md) · [backend](backend.md)
· [ADR 0008](../decisions/0008-project-format-compatibility.md).

## 1. Container (current)

A `.gepro` file is a ZIP archive written by `MainWindow.on_save`:

| Member | Content |
| --- | --- |
| `document.json` | `_file_version`, `_files` (ordered member list), `proj_drawing_names`, `proj_fields` |
| `proj_drawing_page_<N>.json` | One per sheet, `N` from 0 |
| `proj_loadprofiles.json` | Load profile dictionary |

`_file_version` is `misc.PROJECT_FILE_VER = "GELECTRICAL_FILE_REFERENCE_VER_0"`.
Loading rejects other values. JSON is written with `indent=2`, without an
explicit encoding argument to `json.dumps` (ASCII escapes are used).

## 2. Documents (current)

### `document.json`

```json
{
  "_file_version": "GELECTRICAL_FILE_REFERENCE_VER_0",
  "_files": ["proj_drawing_page_0.json", "proj_drawing_page_1.json", "proj_loadprofiles.json"],
  "proj_drawing_names": ["proj_drawing_page_0.json", "proj_drawing_page_1.json"],
  "proj_fields": {
    "Information": {"project_name": {"value": "PROJECT", "type": "str"}, "...": {}},
    "Simulation": {"...": {}},
    "Reports": {"...": {}},
    "Rules Check": {"...": {}}
  }
}
```

Only `value` and `type` are stored per field (`misc.get_fields_trunc`). On load,
`misc.update_fields_dict` copies values onto the current default definitions
**only when the key exists and the type matches**; unknown keys are ignored and
missing keys keep defaults. This is the de facto migration mechanism.

### Drawing page

```json
["DrawingModel", {
  "fields": {"name": {"value": "Sheet 1", "type": "str"}, "page_size": {"value": "A3", "type": "str"}, "...": {}},
  "elements": [
    {"code": "element_busbar", "x": 152.0, "y": 432.0, "orientation": "vertical",
     "ports": [[17, 0], [1, 4], [17, 4], [33, 4]],
     "fields": {"ref": {"value": "B1", "type": "str"}, "...": {}}},
    {"code": "element_wire", "x": 160.0, "y": 512.0, "orientation": "vertical",
     "ports": [[0.0, 0.0], [0.0, 4.0]], "points": [[160.0, 512.0], [160.0, 544.0]], "fields": {}},
    {"code": "element_assembly", "x": 142, "y": 374, "orientation": "vertical", "ports": [[0, 0]],
     "element_rect_width": 350, "element_rect_height": 149,
     "children_codes": [[0, 4], [0, 5], [0, 16]], "fields": {"...": {}}}
  ]
}]
```

- Coordinates are drawing units (points at 100 % zoom). Port offsets are in grid
  multiples of `misc.M = 8` units; the snap grid is `GRID_WIDTH = 16` units.
- Element identity is the index in `elements`. Assemblies reference children by
  `[page, index]`.
- `element_display_node` overlay elements are never saved.
- Protection and damage curve fields (`pcurve_l`, `pcurve_g`, `dcurve`) store
  complete curve definitions, including **expression strings**, in the field
  value (several kilobytes per breaker).
- Cross-sheet connectivity is defined by equal `ref` values on
  `element_reference`/`element_reference_box` elements.

### `proj_loadprofiles.json`

`{"load_prof_1": ["Flat", [{"mode": 1, "title": "Default", "xval": [0, 23], "yval": [1, 1]}]], ...}`
— key → `[title, [graph models]]`; `mode` uses `GRAPH_DATATYPE_*`.

## 3. Load and save behaviour (current)

- Sheets are loaded in `_files` order, filtered by the `proj_drawing_page_`
  prefix (not by `proj_drawing_names`).
- Each element is instantiated from the registry by `code`, then `set_model`
  copies values with `model_loading = True` and calls `set_model_cleanup()`
  (usually `calculate_parameters()`).
- Derived field state (selection lists, enabled flags) is recomputed, not read.
- Saving overwrites the target file directly (legacy GTK app). The services
  (M4) save atomically, see section 6.

## 4. Compatibility policy (proposed)

1. **Every existing `.gepro` must open** in the modern application and produce
   the same canonical model and engineering results (see
   [regression baseline](../migration/regression-baseline.md)).
2. **Additive changes keep `VER_0`.** New optional keys that the legacy loader
   ignores (for example element `uid`) may be written without a version bump,
   provided the legacy GTK application can still open the file with identical
   results. A test opens modern-saved files with the legacy loader while the
   legacy code exists.
3. **Breaking changes require a new version** (`GELECTRICAL_FILE_REFERENCE_VER_1`),
   a migration function `migrate_v0_to_v1` in `gelectrical/persistence/migrations.py`,
   tests on all sample files and an ADR. Old versions stay loadable indefinitely.
4. Element `code`s are permanent. A renamed class keeps its `code`; a retired
   element keeps a loader that maps it to a replacement with documented semantics.
5. Field codes and value semantics are permanent. A changed meaning requires a
   new field code plus migration.
6. Unknown element codes or fields are preserved on round trip where possible
   and reported, never silently dropped.

## 5. Additive keys (current since M4)

| Key | Location | Purpose |
| --- | --- | --- |
| `uid` | each element, each drawing page object | Stable identity for commands, MCP and the frontend |
| `children_uids` | `element_assembly` | Robust assembly membership; `children_codes` kept for legacy readers |
| `app` | `document.json` | `{"name": "GElectrical", "version": "...", "saved_by": "modern"}` provenance |

*Current (M4):* the services write all three keys
(`modern/backend/document.py`, `storage_model`); files without them get new
`uid`s on open. The legacy GTK app ignores them and drops them when it saves.
`tests/services/test_services.py` checks that a modern-saved file loads in
the legacy loader to the same model.

Curve definitions stay embedded in element fields (owner decision Q8,
2026-11-26). They are evaluated with the safe evaluator from M3
([ADR 0011](../decisions/0011-safe-expressions.md)).

## 6. Save procedure (current in the services since M4)

1. Serialize all members in memory and validate the result by re-reading it.
2. Write to a temporary file in the target directory, flush and `fsync`.
3. Keep the previous file as `<name>.gepro.bak` (configurable count).
4. Atomically replace the target (`os.replace`).
5. Write JSON as UTF-8 with explicit `encoding='utf-8'` when reading/writing
   member streams.
6. Report failures without modifying the existing file.

*Current (M4):* `persistence.write_gepro(..., atomic=True, backup=True)`
implements steps 1–6 with one backup (`<name>.gepro.bak`); the legacy GTK
save still writes in place.

Recovery checkpoints (autosave of the working document to the user data
directory) follow GEstimator's model and are planned in milestone M9.
