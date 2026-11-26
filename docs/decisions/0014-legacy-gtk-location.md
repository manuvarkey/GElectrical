# 0014. Legacy GTK UI moves to `gelectrical/gtk/` and retires at parity

- Status: Accepted (owner 2026-11-26)
- Date: 2026-11-26
- Related: [implementation plan M2, M15](../migration/implementation-plan.md), [backend §2](../architecture/backend.md#2-engine-package-gelectrical)

## Context

`gelectrical/__init__.py` holds `MainApp`/`MainWindow` and imports GTK, so any
`gelectrical.*` import loads GTK. The GTK app must keep working during the
migration: it is the user-facing product until parity and the reference for
behaviour checks.

## Decision

- Keep the Python package name `gelectrical` for the engine.
- Move the GTK application (`MainApp`, `MainWindow`, `view/`, `interface/`,
  GTK helpers from `misc.py`) into `gelectrical/gtk/` in M2. `gelectrical_launcher.py`
  imports `gelectrical.gtk.app`. Packaging manifests are updated in the same PR.
- After M2 the GTK UI receives only bug fixes and adaptation to engine moves.
- At M15 the GTK code moves to an `archive/gtk` branch and is removed from
  `master` (GEstimator precedent).

## Alternatives considered

- *New engine package name (`gelectrical_core`)*: avoids moving GTK code but
  breaks imports and packaging, and splits history.
- *Keep GTK code in place with lazy imports in `__init__.py`*: smaller diff but
  leaves GTK modules interleaved with engine modules.

## Consequences

One-time path churn in M2; smoke test and packaging must be updated together.

## Verification

Smoke test and baseline green after the move; headless import test passes.
