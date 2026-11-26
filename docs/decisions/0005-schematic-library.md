# 0005. Schematic rendering library: maxGraph vs custom SVG

- Status: Proposed — decision rule accepted by the owner 2026-11-26; outcome recorded at the end of M7
- Date: 2026-11-26
- Related: [schematic editor §4](../architecture/schematic-editor.md#4-requirements-and-evaluation), [ADR 0004](0004-canonical-schematic-model.md)

## Context

The brief prefers maxGraph, subject to a prototype showing compatibility with
GElectrical's requirements. Alternatives are SVG.js or a custom SVG
implementation. GElectrical drawings are modest in size (tens to hundreds of
elements per sheet today) but must support precise coordinates, coordinate-based
junctions, adjustable busbars, title blocks and analysis overlays.

## Decision (pending)

Build both prototypes against the same fixtures and commands in M7. Choose
maxGraph if it passes every *must* criterion (connectivity, coordinate and
symbol fidelity, licence/maintenance) and is not worse on interaction
completeness, performance and code clarity; otherwise choose custom SVG with
EngineeringUI drawing utilities (SVG.js optional).

## Alternatives considered

maxGraph (`@maxgraph/core`, Apache-2.0); custom Vue SVG; SVG.js (MIT); Konva or
canvas-based libraries (rejected: canvas loses SVG symbol editability and crisp
vector output at fractional scaling).

## Consequences

Until the decision, only read-only rendering and the symbol pipeline may be
built on top of either candidate.

## Verification

Filled selection-criteria table with measurements, attached to this record.
