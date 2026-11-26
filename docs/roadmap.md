# Roadmap

Navigation: [documentation index](README.md) · [implementation plan](migration/implementation-plan.md)
· [design services](architecture/design-services.md).

This page lists remaining work and its status. A roadmap item is not an API
contract and does not authorize implementation outside its milestone.

## Modernisation (in order)

| Milestone | Summary | Status |
| --- | --- | --- |
| M0 | Planning and architecture documents | Done; reviewed by the owner 2026-11-26 |
| M1 | Regression baseline and test scaffold on the legacy code | Not started |
| M1b | Python 3.14 + latest pandapower upgrade with difference report | Not started |
| M2 | Headless engine extraction (PoC 1) | Not started |
| M3 | Safe expressions and security hardening | Not started |
| M4 | Application services and JSON Lines backend | Not started |
| M5 | Sidecar packaging PoC (PoC 2) | Not started |
| M6 | Frontend foundation, EngineeringUI, Quasar, Storybook (PoC 3, 4) | Not started |
| M7 | Schematic editor PoC and library decision (PoC 5) | Not started |
| M8 | ECharts protection and load-profile PoC (PoC 6) | Not started |
| M9 | Desktop vertical slice | Not started |
| M10 | Schematic editing parity | Not started |
| M11 | Properties, databases, load profiles, protection editors | Not started |
| M12 | Analysis, results, messages, rules check, reports | Not started |
| M13 | MCP server and initial skills | Not started |
| M14 | Distribution (Windows, Linux, Flatpak, Snap, optional macOS) | Not started |
| M15 | Parity sign-off and GTK retirement | Not started |

## After parity (not to be implemented during migration)

- Design services framework and pilot module (cable sizing check).
- Load estimation and demand calculation; distribution board and circuit schedules.
- Breaker, transformer and generator selection/sizing.
- Protection coordination assistance.
- Earthing system design.
- Automatic schematic generation from structured descriptions (also via MCP).
- Design alternatives and comparison; bill of quantities improvements.
- Compliance checking against selectable standards libraries.
- Editor enhancements: multi-element move with connection keeping, mirroring,
  automatic orthogonal routing.
- Replace Matplotlib report graphs with ECharts SVG if parity is shown.
- Explicit connection records in the file format (only with a proven
  topology-preserving migration).
- EngineeringUI extraction to its own repository.

## Known defects to schedule

See [audit §12](migration/existing-application-audit.md#12-defects-and-weaknesses).
D1–D3 and D10 are scheduled in M3; D4, D14 and D15 in M2; D5 and D6 in M4;
D7 in M9; D11–D13 in M2/M5. D8 and D9 are assessed with baseline evidence
before any fix.
