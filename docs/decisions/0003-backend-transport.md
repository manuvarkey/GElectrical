# 0003. Multiplexed JSON Lines transport with events and analysis jobs

- Status: Accepted in direction (owner 2026-11-26); worker-process question and details finalised by M4 measurements
- Date: 2026-11-26
- Related: [backend §7](../architecture/backend.md#7-desktop-json-lines-protocol), [packaging](../architecture/packaging.md)

## Context

GEstimator's desktop transport is JSON Lines over the sidecar's stdin/stdout.
Its Rust bridge holds a mutex for one request at a time, waits up to 120 s for
the matching response and forwards progress events. MCP changes reach the
desktop by polling a change sequence.

GElectrical analyses can run for a long time (time-series power flow, large
networks), and MCP edits should appear in the UI promptly.

## Decision

Adopt GEstimator's JSON Lines envelope and error style, with three changes:

1. **Multiplexing:** several requests may be outstanding; the Rust bridge has a
   reader thread that routes responses to waiting calls by `id`.
2. **Unsolicited events:** the backend emits `changed`, `progress`,
   `job_finished`, `mcp_status` and `log` events without an `id`; Rust forwards
   them as Tauri events.
3. **Analysis jobs:** `analysis.start` returns a job id at once; the job runs on
   a project snapshot; progress and completion are events; cancellation is
   cooperative, or by terminating a worker process if PoC measurements require
   hard cancellation.

## Alternatives considered

- *Local HTTP/WebSocket between frontend and backend*: extra port, auth and CSP
  surface; no benefit over stdio inside one app.
- *Tauri commands implemented in Rust calling Python via PyO3*: complex
  packaging and threading with pandapower/Numba.
- *Single in-flight request (GEstimator as is)*: blocks UI queries during
  analysis.

## Consequences

- Rust bridge is slightly more complex than GEstimator's; it needs tests for
  out-of-order responses and backend crash handling.
- Services must make snapshot copies cheap enough (measure in M4).

## Verification

Protocol tests that issue concurrent requests during a long analysis; crash and
restart tests; Playwright test that the UI stays responsive during analysis.
