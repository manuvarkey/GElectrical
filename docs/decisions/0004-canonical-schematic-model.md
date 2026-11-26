# 0004. Canonical schematic data and coordinate connectivity stay in Python

- Status: Accepted in direction (owner 2026-11-26); details finalised by the M7 PoC
- Date: 2026-11-26
- Related: [schematic editor](../architecture/schematic-editor.md), [project format](../architecture/project-format.md)

## Context

Connectivity today is defined by coincident port coordinates on a sheet and by
equal reference strings across sheets. Diagram libraries such as maxGraph
model connectivity as edges attached to terminal cells. Changing the canonical
model would change project semantics and the file format.

## Decision

- The backend document (elements, wires as polylines, positions, orientation,
  sheets, fields) is canonical. Frontend libraries hold disposable view models.
- Connectivity rules remain coordinate coincidence plus reference joins. The
  backend computes nets and returns derived data (junctions, connectivity
  deltas) for display.
- Edits are commands with integer drawing-unit coordinates, snapped and
  validated in Python.
- Symbol geometry comes from declarative definitions shared by the frontend
  renderer and the Cairo PDF renderer; labels are computed in Python.

## Alternatives considered

- *Explicit connection records as canonical*: cleaner graph semantics and easier
  library mapping, but requires a file-format migration and risks changing
  topology of existing projects. Could be revisited after parity with a
  migration that is proven topology-preserving on all projects.

## Consequences

- The frontend adapter must suppress library-side connection semantics where
  they conflict.
- Topology equivalence tests stay simple (same algorithm, same inputs).

## Verification

M7 PoC criterion 1 (connectivity fidelity) and the topology artefact of the
regression baseline.
