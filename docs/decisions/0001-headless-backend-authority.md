# 0001. Headless Python backend is the authoritative owner of project state

- Status: Accepted
- Date: 2026-11-26
- Related: [backend](../architecture/backend.md), [ARCHITECTURE.md](../../ARCHITECTURE.md)

## Context

GElectrical's engineering logic (elements, connectivity, pandapower models,
protection curves, rules) is valuable and validated by users, but it is
interleaved with GTK. The modernisation brief requires a separation of
calculations and project management from the GUI, an MCP server sharing the
same operations, and a backend that runs without GTK, Tauri or a display.

## Decision

- The Python backend owns project state, validation, calculations, persistence,
  undo/redo and exports.
- The Vue frontend owns presentation, interaction, temporary edit state and
  visual feedback only. It does not duplicate engineering calculations or
  electrical validation in TypeScript.
- The GUI and MCP invoke the same application services on one owner thread per
  process. There is no second writable project copy.
- The engine is importable and testable without GTK, Tauri, a display or a
  frontend. Headless Cairo is allowed.

## Alternatives considered

- *Port calculations to TypeScript/Rust*: rejected; duplicates validated
  engineering code and pandapower has no equivalent.
- *Keep GTK and add MCP to it*: rejected; does not meet maintainability and UI
  goals, and couples MCP to the GTK main loop.

## Consequences

- An engine refactor (M2) precedes UI work that depends on services.
- Every frontend feature requires a backend query/command; latency matters
  (interactive previews must be cheap or debounced).

## Verification

Headless import and pipeline tests in CI (M2); dependency checks that the
engine imports no UI or transport module.
