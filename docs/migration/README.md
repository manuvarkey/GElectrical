# Migration to Tauri + Vue + headless Python

Navigation: [documentation index](../README.md) · [architecture overview](../../ARCHITECTURE.md)
· [roadmap](../roadmap.md).

GElectrical is migrating from a GTK3/PyGObject desktop application to a Tauri 2
desktop shell with a Vue 3 + TypeScript frontend, a reusable EngineeringUI
library and a headless Python engineering backend shared by the GUI and an MCP
server. Phase 1 (planning) is complete and was reviewed by the owner on
2026-11-26 ([decisions](risks-and-decisions.md#2-owner-decisions)); no
functional migration has started.

## Documents

| Document | Purpose | Kind |
| --- | --- | --- |
| [Existing application audit](existing-application-audit.md) | How the GTK application works today, GUI coupling map, defects | Current implementation |
| [Feature inventory](feature-inventory.md) | Every user-visible feature with parity status | Current + tracking |
| [Implementation plan](implementation-plan.md) | Milestones M0–M16 (plus M1b) with scope, dependencies, acceptance criteria | Approved plan |
| [Regression baseline](regression-baseline.md) | Numerical oracle, artefacts, tolerances | Proposed (M1) |
| [Risks and decisions](risks-and-decisions.md) | Risk register, open owner decisions, PoC requirements, licence inventory | Living |
| [Validation log](validation.md) | Dated evidence of checks actually run | Append-only |

Architecture contracts for the target system are in
[docs/architecture/](../architecture/) and decisions in
[docs/decisions/](../decisions/README.md).

## Phase 1 summary

**Existing architecture and constraints.** The engine (elements, network
topology, pandapower models, protection curves, rules check) is sound but is
interleaved with GTK: every module imports GTK through `gelectrical/__init__.py`
and `misc.py`; element geometry is computed while drawing with Cairo/Pango;
`ProjectModel` owns GTK views; connectivity is defined by coincident port
coordinates; identity is positional; curve and rule semantics are Python
expression strings evaluated with `eval()`. There is no test suite beyond a
smoke test.

**Target architecture.** A headless `gelectrical` engine package; application
services with commands, transactions, snapshot undo, revisions and change
events in `modern/backend/`; a multiplexed JSON Lines protocol to a Tauri Rust
bridge; a Vue/Quasar frontend in `modern/src/` built on EngineeringUI
(`packages/engineering-ui/`); an MCP server built with the official Python SDK
calling the same services; existing report and PDF pipelines retained.

**Sequencing.** Capture a regression baseline from the legacy code first (M1),
upgrade to Python 3.14 and the latest pandapower with a measured difference
report (M1b), extract the headless engine (M2), then build services, packaging and frontend
proofs of concept in parallel before feature migration (M9–M13), distribution
(M14) and GTK retirement (M15).

## Rules for migration work

1. Read the [implementation plan](implementation-plan.md) entry for the
   milestone before starting; stay within its scope.
2. Run the baseline comparison for every change that touches `gelectrical/`.
3. Update the feature inventory status only with evidence recorded in the
   [validation log](validation.md).
4. Record new risks and decisions here and in an ADR when they affect
   architecture, compatibility or engineering results.
5. Historical documents keep their dates; superseded statements are marked,
   not rewritten.
