# MCP server

Status: **proposed** (Phase 1). Navigation: [index](../README.md) ·
[backend](backend.md) · [design services](design-services.md) ·
[ADR 0007](../decisions/0007-mcp-server.md).

The MCP server lets AI assistants inspect, build and analyse GElectrical
projects through the same application services as the desktop UI. It is an
adapter: it owns tool schemas, permissions and resources, not project state.

## 1. Patterns reused from GEstimator

GEstimator (`modern/backend/mcp_*.py`, `docs/architecture/mcp.md`) provides a
working design. Reused patterns:

| Pattern | GEstimator behaviour | GElectrical use |
| --- | --- | --- |
| Off by default | Enabled in program settings; Start/Stop in an MCP ribbon | Same |
| Local only | Binds `127.0.0.1`, bearer token, Host/Origin checks | Same |
| Access modes | Read only / Read and write | Same; file writes gated by write mode |
| Serialized execution | Every tool runs on the runtime owner thread; bounded waits | Same |
| Revision guards | Optional `if_revision`; each response returns `revision` | Same |
| Envelope | `structuredContent: {data, revision, warnings}`; compact JSON text copy; errors with `code, message, field, allowed, hint` | Same |
| Preview | Writes accept `preview: true`, rolled back | Same, via service transactions |
| Batch | Related writes in one transaction and one undo entry | Same |
| Consolidated tools | ~19 intent-level tools instead of one per method | Same discipline; schema size budget asserted by tests |
| Skills as resources | Library manifests with `SKILL.md` and references; URIs `gestimator://skills/...` | `gelectrical://skills/...` |
| Desktop sync | Desktop polls a change sequence | Replaced by pushed `changed` events ([backend](backend.md#revisions-and-change-events)) |

Difference: GEstimator implements the Streamable HTTP protocol by hand on
`http.server`. GElectrical uses the **official Python MCP SDK** (`mcp`, MIT) for
protocol handling, negotiation and transport, keeping GEstimator's
authentication, envelope and serialization rules on top of it.

## 2. Process and transport

- The MCP server runs inside the backend sidecar on its own thread with an
  asyncio event loop (SDK Streamable HTTP app served by `uvicorn`, bound to
  `127.0.0.1` on a configurable port, default to be chosen to avoid
  GEstimator's 8765).
- Tool handlers translate arguments, then submit a service call to the runtime
  owner queue and await the result with a timeout (reads 30 s, writes 110 s;
  analysis tools return a job handle when work exceeds a short wait).
- A stdio transport would require a separate process with its own project copy
  and is therefore **not** offered. A thin stdio-to-HTTP proxy may be added for
  clients without HTTP support (it holds no project state).
- Listener generation is checked when queued requests execute, so requests from
  a stopped listener cannot write after a restart.

## 3. Tool surface (draft)

Names are snake_case. `tools/list` is authoritative once implemented.

| Read tools | Purpose |
| --- | --- |
| `get_state` | Start-here guide, active project, sheets, counts, dirty flag, revision, analysis status, available skills |
| `describe_elements` | Element catalogue: codes, groups, ports, field schemas (on demand per code to limit size) |
| `search_library` | Search equipment databases (cables, breakers, fuses, transformers, motors, load profiles) |
| `get_drawing` | Elements, wires and labels of a sheet; optional geometry |
| `get_elements` | Full fields, field state and results for `uid`s |
| `get_topology` | Nodes, connected elements, upstream/downstream relations, islands, unconnected ports |
| `get_results` | Analysis results and stale flag; filters by element/node/type |
| `get_messages` | Diagnostics and rules-check messages |
| `get_protection` | Evaluated curves and coordination checks for selected devices |

| Write tools | Purpose |
| --- | --- |
| `project` | new / open / save / save_copy / set_settings / set_sheet_fields |
| `edit_drawing` | Ops list: insert, move, rotate, delete, set_fields, add_wire, edit_wire, assemble, link_references, renumber, add_sheet, remove_sheet |
| `apply_library_item` | Copy database values into elements |
| `edit_load_profiles` | Create/update/delete profiles |
| `generate_schematic` | Place and wire a structured single-line description (later milestone; see [design services](design-services.md)) |
| `run_analysis` | Start analysis with settings; wait briefly or return a job id; `get_results` polls |
| `run_rules_check` | Run rules check on current results |
| `run_design` | Execute a design service (later milestone) |
| `export` | Report PDF/HTML, drawing PDF, pandapower JSON, protection settings workbook |
| `batch` | Several write ops in one transaction and one undo entry |
| `history` | Undo / redo |

Conventions:

- Elements are addressed by `uid`; new elements in one call can declare `ref`
  labels used by later ops in the same call (GEstimator pattern).
- Numeric inputs that may contain arithmetic are strings evaluated by the safe
  evaluator; plain JSON numbers are accepted for engineering values.
- Wire ops accept explicit points or `{"from": {"uid", "port"}, "to": {...}}`
  for which the backend computes an orthogonal grid route (still stored as a
  plain wire). Responses report connectivity deltas.
- Every write returns the new revision, created `uid`s and warnings.

## 4. Permissions and review

- **Read only** exposes read tools. **Read and write** adds write tools.
- File operations (open, save, save_copy, export) require write mode, validate
  paths, refuse overwrites unless explicitly requested and never write outside
  the chosen file.
- MCP cannot change its own listener configuration, run shell commands or read
  arbitrary files.
- Every MCP transaction is tagged `source: "mcp"` with the tool name. The
  desktop highlights affected elements, lists AI changes since the last review
  in an **AI changes** panel and lets the user undo them like any other change.
- Decided (Q14): tagging, highlighting and undo ship first.
- Later: *require approval* mode where MCP writes are executed as
  previews and queued as change sets that the user accepts or rejects in the
  desktop.
- Design and generation tools return an explicit `assumptions` list and the
  standards/clauses used; the skills require assistants to state assumptions to
  the user.

## 5. Skills and resources

Engineering guidance is loaded on demand, not embedded in tool descriptions.

- Library layout follows GEstimator: bundled libraries under
  `modern/backend/data/skills/<library>/`, user libraries in the per-user data
  folder; `library.json` manifest; one folder per skill with `SKILL.md` and
  `references/*.md`.
- URIs: `gelectrical://skills/<library>/<skill>[/<path>]`.
- `get_state` lists skills with one-line descriptions; `resources/read` or a
  read tool returns the content.

Planned skills (content to be written with references to the standards in
force; reuse GEstimator's Indian LV distribution and lightning skills where they
apply):

| Skill | Scope |
| --- | --- |
| `gelectrical-modelling` | How GElectrical elements, ports, wires, references and sheets work; modelling conventions for pandapower |
| `lv-distribution-design` | Load estimation, diversity, board schedules, feeder selection (IEC 60364 / local rules) |
| `cable-sizing` | Current-carrying capacity and derating (IEC 60364-5-52), voltage drop, fault withstand |
| `short-circuit` | IEC 60909 assumptions, max/min cases, `lv_tol_percent`, fault impedance |
| `protection-coordination` | Device selection, discrimination, damage/starting curves, disconnection times |
| `earthing-systems` | TN/TT/IT, CPE sizing, disconnection requirements |
| `rules-check-interpretation` | Meaning and remediation of each rules-check message |
| Regional libraries (for example `in`) | National regulations and practice |

## 6. Desktop synchronization

- MCP writes go through services, so the desktop receives `changed` events
  immediately and refreshes affected data.
- Desktop edits based on an older revision are rejected and retried by the user;
  MCP writes with a stale `if_revision` are rejected.
- Switching the active document changes the MCP target and increments an MCP
  project epoch reported by `get_state`.
- Status (running, port, access mode, request count, last tool) is shown in the
  MCP ribbon without logging tokens or project content.

## 7. Testing

- Protocol tests use the SDK client against the in-process server.
- Contract tests snapshot `tools/list` (names, schemas, size budget).
- Editing tests verify atomicity, preview rollback, stale revision rejection,
  undo after MCP batch and desktop `changed` events.
- End-to-end: an MCP script builds a small network, runs analysis and checks
  results against the engine baseline.
