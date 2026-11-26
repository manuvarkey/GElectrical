# 0009. Snapshot-based command transactions for undo/redo

- Status: Accepted (owner 2026-11-26)
- Date: 2026-11-26
- Related: [backend §5](../architecture/backend.md#5-application-services-modernbackendservices)

## Context

The legacy undo system (`undo.py`, `misc.undoable`, `misc.group`) records
generator-based inverse operations spread across models and views. Services
need atomic commands, preview with rollback, MCP batches with one undo entry and
robust failure recovery. GEstimator uses SQL transactions plus snapshots.

## Decision

Implement service transactions that capture serialized "before" and "after"
states of the touched parts of the document (element models with `uid`, sheet
fields, project settings, load profiles). Undo restores "before", redo restores
"after". A failed or preview transaction restores "before" and records nothing.
One user action or one MCP batch is one entry, with a label matching the legacy
description for the same action.

## Alternatives considered

- *Reuse generator inverse operations*: preserves existing code, but inverse
  logic is incomplete for some derived state, hard to make atomic on failure and
  awkward for previews and batches.
- *Whole-document snapshots per command*: simplest; acceptable fallback if
  projects stay small (current samples are below 200 KB serialized). Measure in M4.

## Consequences

Element `set_model`/`get_model` must round-trip exactly (including derived field
state after recalculation); the baseline round-trip artefact protects this.

## Verification

Undo sequence tests against legacy labels and states; atomicity tests with
injected failures; performance measurement on a large synthetic project.
