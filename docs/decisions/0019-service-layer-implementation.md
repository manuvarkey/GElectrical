# 0019. Service layer implementation: snapshot documents, legacy labels, analysis copies

- Status: Proposed (implemented in M4); points 4 and 7 approved by the owner 2026-11-27 (with the change to point 4 below)
- Date: 2026-11-27
- Related: [backend §3–8](../architecture/backend.md#3-domain-identity),
  [backend protocol](../architecture/backend-protocol.md),
  [ADR 0003](0003-backend-transport.md), [ADR 0008](0008-project-format-compatibility.md),
  [ADR 0009](0009-undo-transactions.md)

## Context

Milestone M4 adds application services and the desktop JSON Lines backend
(`modern/backend/`). ADR 0009 chose snapshot transactions and left open
whether to snapshot touched parts or the whole document ("measure in M4").
The legacy undo labels are produced by `@undoable` generators spread over
`ProjectModel` and `DrawingModel`; analysis inserts node display elements
into the document (D7) and writes results into element `res_fields`.
Element identity is positional.

## Decision

1. **Whole-document snapshots with structural sharing.** A snapshot holds
   the project fields (full dictionaries), load profiles and, per sheet, the
   sheet fields and `(uid, element model)` pairs, JSON-normalised. Each
   command captures the "after" snapshot; "before" is the previous committed
   snapshot (no capture at command start). Unchanged parts reuse the previous
   snapshot's objects, so history memory grows with changed elements only.
   Restore keeps element objects whose model is unchanged and rebuilds the
   others with `DrawingModel.new_element_from_model` (the file-loading path).
   Restore reproduces stored fields exactly (no renumbering of sheet numbers
   or assembly children codes).
2. **Labels from the engine.** Service sessions give `ProjectModel` a
   `RecordingStack` instead of `undo.Stack`. Engine `@undoable` calls and
   `group()` blocks append their actions; the stack keeps the description of
   each top-level action and discards the action. A command whose engine
   calls record exactly one top-level action uses that label (the legacy
   text); otherwise the command's declared label. Undo itself never runs the
   legacy inverse generators.
3. **Identity in the service layer.** `uid` attributes are assigned to
   sheets and stored elements after each command (`ensure_uids`; copies made
   with `deepcopy` keep their uid, duplicates get a new one) and written as
   additive keys on save (`uid`, `children_uids`, `app`). Engine
   `get_model()` is unchanged, so engine copies (paste, floating models) never
   duplicate identifiers.
4. **Analysis on detached copies.** `analysis.start` hands the committed
   snapshot to a single job thread, which builds a fresh `ProjectModel` from
   it and runs `gelectrical.analysis.run_analysis` unchanged. Results (typed
   per element uid, node overlay keyed by `N[uid:port|...]`, messages with
   uids) and the analysed copy are stored in the session with their revision
   and flagged stale after edits. The live document never receives node
   display elements or result fields (E09 *Changed*). Exports run on the
   same job thread against the analysed copy or a snapshot copy. Analysis
   settings passed to `analysis.start` are saved into the project's
   Simulation settings first, like the legacy dialog (owner decision
   2026-11-27), as one undoable command `Update analysis settings` when they
   change. Clearing results is not a document change and has no undo entry
   (approved).
5. **In-thread jobs, no worker process yet.** Measured analysis times
   (≤ 8 s per baseline project including time series) and cooperative
   cancellation between stages are sufficient for M4; the worker-process
   question of ADR 0003 stays open for M5/M9 measurements on packaged builds.
6. **Atomic saves are opt-in in the engine.** `write_gepro(..., atomic=True,
   backup=True, app=...)` is used by the services; the legacy GTK save keeps
   its in-place write until the GTK app retires (no behaviour change there).
7. **Move in place.** `drawing.move` moves elements without changing list
   order or identity and is one history entry (the legacy drag deletes and
   re-inserts at the end: two entries). Rotation of placed elements and wire
   editing are new commands. Commands that change nothing record no entry.

## Alternatives considered

- *Per-part snapshots of touched elements only*: smaller captures, but every
  command would have to declare what it touches (derived updates such as
  `reg_refs_sheets`, renumbering or sheet copies touch many elements);
  measured whole-document capture is cheap enough (below).
- *Restating labels in the service layer*: duplicates legacy texts (including
  their quirks such as the double space in `Modify '...' field  of ...`) and
  drifts; recording them from the engine keeps one source.
- *`uid` inside `ElementModel.get_model()`*: copies made through the storage
  model (paste, floating models, `get_element_copy`) would duplicate ids.
- *Analysis in the live document (legacy)*: mutates the document (node
  elements, undo entries) and blocks edits during long runs.

## Consequences

- Command cost is proportional to document size. Measured on Windows 11
  (`tools/measure_services.py`, median of 5):

  | Project | Elements | JSON | Capture | One-field command | Undo | Delete | Undo delete |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | `sample.gepro` | 27 | 113 KB | 6.0 ms | 6.9 ms | 7.6 ms | 6.6 ms | 7.8 ms |
  | `cov_multisheet.gepro` | 34 | 76 KB | 4.8 ms | 5.5 ms | 5.9 ms | 5.5 ms | 5.9 ms |
  | synthetic | 2000 | 998 KB | 65 ms | 66 ms | 66 ms | 66 ms | 65 ms |

  With structural sharing, 50 one-field commands on the synthetic project
  add 7.5 MB of traced memory (about 150 KB per entry, 30 MB for a full
  200-entry history).
- Queries that compute symbol extents may rewrite `ports` as tuples in live
  elements (as the GTK view does when drawing); the stored JSON and the
  change detection are unaffected.
- The legacy undo stack is not used by services; legacy defects in inverse
  generators (undo of deleting element 0 re-appends it at the end) do not
  occur in services.

## Verification

`tests/services/`: legacy-action vs command table (21 cases: label, one
entry, same resulting document, undo, redo), atomicity with an injected
failure, preview, stale revision, bounded history, session isolation,
uid persistence, atomic save and backup, analysis of all 17 baseline
projects compared with `tests/baseline/*/pf_bal` (unchanged tolerances),
protocol tests against a spawned backend, JSON Schema conformance. Evidence
in the [validation log](../migration/validation.md) M4 entry.
