# Backend protocol and services

Status: **current** (milestone M4, 2026-11-27). Design and rationale:
[backend architecture](backend.md) sections 3–8,
[ADR 0003](../decisions/0003-backend-transport.md),
[ADR 0008](../decisions/0008-project-format-compatibility.md),
[ADR 0009](../decisions/0009-undo-transactions.md),
[ADR 0019](../decisions/0019-service-layer-implementation.md).
Navigation: [index](../README.md) · [architecture overview](../../ARCHITECTURE.md).

The headless backend lives in `modern/backend/` and imports the engine
(`gelectrical`), never GTK. It is used by the future Tauri shell (M5/M9) and
MCP server (M13); there is no frontend integration yet.

```bash
pixi run backend                         # python -m modern.backend (JSON Lines on stdin/stdout)
pixi run python -m modern.backend --print-methods
pixi run python -m modern.backend --write-schemas modern/backend/schemas
pixi run -e test test-services           # service, undo-label, baseline and protocol tests
```

## 1. Process and transport

- One request per line on stdin, one response or event per line on stdout,
  UTF-8 JSON. Diagnostics go to stderr and to
  `<user data>/logs/gelectrical-backend.log` (rotating, feature A22;
  `--no-log-file` disables it). File descriptor 1 is redirected to stderr at
  start-up, so library prints (pandapower diagnostics) never reach the
  protocol stream.
- Requests are queued to the **owner thread** as they arrive; several may be
  outstanding and responses can arrive out of order. Match them by `id`.
- `shutdown` answers `true` and exits; end of input also exits. Pending
  requests are answered first.
- `GELECTRICAL_USER_DATA_DIR` overrides the user data directory (program
  settings `settings.ini`, user library `database/`, logs).

## 2. Envelope

| Message | Shape |
| --- | --- |
| Request | `{"id": "r-17", "session": "main", "method": "drawing.move", "params": {...}}` (`session` optional: the active session) |
| Response | `{"id": "r-17", "result": ...}` |
| Error | `{"id": "r-17", "error": {"code", "message", "field"?, "details"?}}` (`id` is `null` when the request id could not be read) |
| Event | `{"event": "changed" \| "progress" \| "job_finished" \| "session_closed", ...}` (no `id`) |

Error codes: `INVALID_REQUEST` (malformed request, unknown method or
parameter, wrong parameter type), `VALIDATION_ERROR` (well-formed but not
allowed, for example a read-only field or a value outside a selection
list), `NOT_FOUND`, `STALE_REVISION`, `CONFLICT`, `FILE_ERROR`, `JOB_ERROR`,
`CANCELLED`, `BACKEND_ERROR` (unexpected failure; details in the log).

Limits: 2,000,000 characters per line, 100 characters per id, 10,000 items
per array or object, nesting depth 64, 32 sessions.

JSON Schemas of the envelope and DTOs are in
[`modern/backend/schemas/`](../../modern/backend/schemas/) (generated from
`modern/backend/schemas.py`; `tests/services/test_schemas.py` checks that
they are current and that service output conforms). Non-finite floats are
sent as `null`.

## 3. Sessions, revisions and commands

- The runtime starts with session `main` holding a new project.
  `session.create`, `session.activate`, `session.close` and `session.list`
  manage further documents; sessions share nothing.
- Elements and sheets are addressed by `uid` (UUID4). Files keep positional
  references and gain additive `uid` keys on sheets and elements,
  `children_uids` on assemblies and an `app` provenance key in
  `document.json` (ADR 0008; file version unchanged). Files without `uid`s
  get new ones on open.
- **Commands** (kind `command` below) follow the contract of
  [backend §5](backend.md#command-contract): validation before any change,
  one transaction, one history entry, `revision + 1`, a `changed` event, full
  rollback on failure. Generic parameters: `preview` (run, report, roll back)
  and `if_revision` (`STALE_REVISION` when the session moved on). Result:
  `{"value", "changes", "label", "revision", "preview"}`. A command that
  changes nothing records nothing (`label: null`).
- `changed` event: `{"event": "changed", "session", "revision", "changes":
  [{"kind", "uids"?}], "source", "dirty"}` with kinds `document`,
  `project`, `loadprofiles`, `sheet`, `sheet_removed`, `element_added`,
  `element`, `element_removed`, `analysis`, `saved`.
- `history.undo` / `history.redo` restore snapshots (ADR 0009; default 200
  entries). `project.new` and `project.open` clear the history, as today.
- `project.save` / `project.save_as` write atomically (temporary file,
  re-read check, `fsync`, `os.replace`) and keep the previous file as
  `<name>.gepro.bak`. A failed save leaves the file untouched.
- Numeric field values may be sent as numbers or as arithmetic text, which
  is evaluated by `core.expressions.evaluate_numeric` (ADR 0011).

## 4. Analysis and exports (jobs)

`analysis.start` returns `{"job", "status": "queued", ...}` at once. The job
runs the legacy pipeline on a copy of the committed snapshot on the job
thread; `progress` events report `stage` (`prepare`, `base_model`,
`power_model`, `diagnostics`, `powerflow`, `sc_sym`, `sc_gf`, `results`,
`rules_check`) and `fraction`; `job_finished` reports `status` (`finished`,
`failed` with a `JOB_ERROR`, `cancelled`). Cancellation is cooperative
between stages. Results are stored per session with their revision and are
reported `stale` after any change. Optional `settings` are first saved into
the project's Simulation settings, as the legacy analysis dialog does (owner
decision 2026-11-27); when they change this is one undo entry `Update
analysis settings` and the run uses the new revision. The live document never receives node display
elements (E09 *Changed*): `analysis.results` returns result fields per
element `uid`, a node overlay (node key `N[uid:port|...]`, members, port
positions, results), diagnostics and rules-check messages with `uids`.

Exports are jobs too and never change the project. Analysis-based exports
need current results.

## 5. Undo labels (legacy action → service command)

Labels are recorded from the engine's own `@undoable` calls, so they are
the legacy texts. `tests/services/test_undo_labels.py` performs each legacy
action and its command on the same file and checks label, granularity (one
entry), resulting document, undo and redo.

| Legacy action | Service command | Undo label |
| --- | --- | --- |
| Edit a property (one element) | `drawing.set_fields` (one field) | `Modify '<code>' field  of '<name>' element` |
| Edit a property (multi-selection) | `drawing.set_fields` (several uids) | `Modify '<code>' field  of '<name>' (multiple) elements` |
| Insert from palette / paste | `drawing.insert`, `drawing.paste` | `Insert element(s) at <port or None>` |
| Delete | `drawing.delete` | `Delete draw elements at '[<indices>]'` |
| Draw wire | `drawing.add_wire` | `Add draw element at '<index>'` |
| Group into assembly | `drawing.assemble` | `Add draw element at '<index>'` (`Update draw element at '<index>'` when extending) |
| Delete an assembly | `drawing.ungroup` | `Delete draw elements at '[<index>]'` |
| Renumber | `drawing.renumber` | `Renumber Elements - <mode>` |
| Link references | `drawing.link_references` | `Link reference <ref>` |
| New / delete / reorder sheet | `drawing.add_sheet`, `drawing.remove_sheet`, `drawing.reorder_sheet` | `Add page at <n>`, `Remove page at <n>`, `Reorder tab - from <a> to <b>` |
| Sheet property | `drawing.set_sheet_fields` (one field) | `Update page field` |
| Project settings | `project.set_settings` | `Update project settings` |
| Load profiles | `loadprofiles.set` | `Update load profiles` |
| Load values from database | `library.apply` | `Update data from database` |
| Protection parameters | `protection.set_parameters` | `Update protection parameters - <name>` |

Differences (not legacy actions, or deliberately changed; move and clear
results approved by the owner 2026-11-27,
[ADR 0019](../decisions/0019-service-layer-implementation.md)):

- **Move:** the legacy drag deletes one element and re-inserts a copy at the
  end of the list (two entries: delete, then `Insert element(s) at None`).
  `drawing.move` moves elements in place, keeps their order and identity and
  is one entry `Move element(s)`; moving an assembly moves its children.
- **New commands:** `drawing.rotate` (`Rotate element`), `drawing.edit_wire`
  (`Update draw element at '<index>'`), several fields in one
  `drawing.set_fields` (`Modify <n> fields`) or `drawing.set_sheet_fields`
  (`Update page fields`).
- **No-op commands** record no entry (the legacy stack records one).
- **Clear results** is not a document change in the services (results are
  not in the document), so it has no undo entry.
- **Analysis settings** passed to `analysis.start` are saved with the undo
  entry `Update analysis settings` (the legacy dialog wrote them without an
  undo entry).
- **Undo of a delete** restores elements at their positions; the legacy undo
  of deleting element 0 re-appends it at the end of the list.

## 6. Methods

Generated from the service registry
(`python -m modern.backend --print-methods`); kinds: `query` (read-only),
`command` (contract above), `session` (session-level actions and jobs),
`runtime` (no session).

<!-- BEGIN GENERATED METHOD TABLE -->
| Method | Kind | Parameters | Summary |
| --- | --- | --- | --- |
| `analysis.cancel` | session | `job` | Cancel a job (between stages) |
| `analysis.clear` | session | - | Clear stored results (not a document change; nothing to undo) |
| `analysis.job` | session | `job` | State of a job (with its result once finished) |
| `analysis.results` | query | `uids?`, `nodes?` | Result fields per element uid, node overlay, diagnostics and rules messages |
| `analysis.rules_check` | session | - | Run the electrical rules check on the stored results (job) |
| `analysis.start` | session | `settings?`, `rules_check?` | Start an analysis job; returns the job id at once. |
| `analysis.status` | query | - | Summary of the stored results (``null`` if none) and running jobs |
| `catalog.element_type` | runtime | `code` | One element type with field schemas and ports |
| `catalog.element_types` | runtime | `advanced?` | Placeable element types in palette order (advanced elements on request) |
| `drawing.add_sheet` | command | `copy_from?`, `preview?`, `if_revision?` | Append a sheet; fields copied from ``copy_from`` (default: first sheet) |
| `drawing.add_wire` | command | `sheet`, `points`, `preview?`, `if_revision?` | Add a wire; points snap to nearby ports, otherwise to the grid |
| `drawing.assemble` | command | `uids`, `preview?`, `if_revision?` | Group elements of one sheet into an assembly (an assembly in the selection is extended) |
| `drawing.connectivity` | query | - | Electrical nodes as sets of (element uid, port) with port positions |
| `drawing.copy` | query | `uids` | Clipboard text (versioned JSON) of elements of one sheet |
| `drawing.delete` | command | `uids`, `preview?`, `if_revision?` | Delete elements |
| `drawing.edit_wire` | command | `uid`, `points`, `preview?`, `if_revision?` | Replace the points of a wire |
| `drawing.element` | query | `uid` | One element with values, field schemas and derived field state |
| `drawing.hit_test` | query | `sheet`, `x`, `y`, `size?` | Element and port around a drawing coordinate (selection helper) |
| `drawing.insert` | command | `sheet`, `code`, `x`, `y`, `orientation?`, `attachment_port?`, `fields?`, `preview?`, `if_revision?` | Insert an element; its attachment port goes to (x, y), snapped to a nearby port or the grid |
| `drawing.link_references` | command | `uid`, `targets`, `copy_titles?`, `preview?`, `if_revision?` | Link a cross-reference element with reference elements on other sheets |
| `drawing.move` | command | `uids`, `dx`, `dy`, `preview?`, `if_revision?` | Move elements by (dx, dy) in place; moving an assembly moves its children |
| `drawing.paste` | command | `sheet`, `text`, `x`, `y`, `attachment_port?`, `preview?`, `if_revision?` | Insert elements from clipboard text (validated JSON, never executed) |
| `drawing.remove_sheet` | command | `sheet`, `preview?`, `if_revision?` | Remove a sheet (not the first one, as in the legacy app) |
| `drawing.renumber` | command | `mode`, `uids?`, `preview?`, `if_revision?` | Renumber element references: All, New elements only, Selected elements only |
| `drawing.reorder_sheet` | command | `sheet`, `index`, `preview?`, `if_revision?` | Move a sheet to a new position |
| `drawing.rotate` | command | `uid`, `preview?`, `if_revision?` | Toggle orientation of a placed element about its first port |
| `drawing.set_fields` | command | `uids`, `values`, `preview?`, `if_revision?` | Set field values of one element or of several elements of one type |
| `drawing.set_sheet_fields` | command | `sheet`, `values`, `preview?`, `if_revision?` | Set sheet fields (name, page size, title block) |
| `drawing.sheet` | query | `sheet`, `detail?` | Sheet fields, page size and elements (``detail`` adds field schemas) |
| `drawing.sheets` | query | - | Sheets in order |
| `drawing.ungroup` | command | `uid`, `preview?`, `if_revision?` | Remove an assembly; its children stay |
| `export.drawing_pdf` | session | `path`, `with_results?` | Export all sheets to a vector PDF (job) |
| `export.element_graph` | session | `path` | Export the element graph HTML (job) |
| `export.network_html` | session | `path` | Export the pandapower HTML report (job) |
| `export.network_json` | session | `path` | Export the pandapower network to JSON (job) |
| `export.report` | session | `folder` | Export the project report (report.html, report.css, report.pdf) to a folder (job) |
| `history.redo` | session | - | Redo the last undone command |
| `history.state` | query | - | Undo/redo availability and labels |
| `history.undo` | session | - | Undo the last command (one entry per command) |
| `library.apply` | command | `uid`, `category`, `item`, `preview?`, `if_revision?` | Load the values of a database item into the element (one undo entry) |
| `library.catalogue` | query | `uid`, `search?` | Categories and item names of the element's database (optional case-insensitive search) |
| `library.item` | query | `uid`, `category`, `item` | Text values of one database item |
| `loadprofiles.get` | query | - | Load profiles of the project |
| `loadprofiles.set` | command | `profiles`, `preview?`, `if_revision?` | Replace all load profiles |
| `project.new` | session | - | Replace the document with a new project (history cleared, not undoable) |
| `project.open` | session | `path` | Open a ``.gepro`` file into this session (history cleared) |
| `project.save` | session | - | Save to the current file (atomic, previous file kept as ``.bak``) |
| `project.save_as` | session | `path` | Save to a new file (``.gepro`` added when missing) |
| `project.set_settings` | command | `values`, `preview?`, `if_revision?` | Change project settings (``{page: {code: value}}``), one undo entry |
| `project.settings` | query | - | Project settings pages (Information, Simulation, Reports, Rules Check) |
| `project.state` | query | - | Session state: path, revision, dirty flag, history, sheets, analysis |
| `protection.curves` | query | `uids` | Evaluated protection and damage curves (unscaled) of elements |
| `protection.set_parameters` | command | `uid`, `curve`, `parameters`, `preview?`, `if_revision?` | Change parameters of an element's protection or damage curve (one undo entry) |
| `runtime.info` | runtime | - | Backend version, limits, events and the method list |
| `session.activate` | runtime | `session` | Mark the session the desktop shows (MCP acts on it) |
| `session.close` | runtime | `session` | Close a document session (unsaved changes are discarded) |
| `session.create` | runtime | `session?` | Open a new document session with a new project |
| `session.list` | runtime | - | Open document sessions and the active one |
| `settings.get` | runtime | - | Program settings pages with field schemas and values |
| `settings.set` | runtime | `values` | Change program settings (``{page: {code: value}}``; not undoable, like the legacy dialog) |
<!-- END GENERATED METHOD TABLE -->
