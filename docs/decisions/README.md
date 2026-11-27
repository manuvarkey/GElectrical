# Architecture decision records

Navigation: [documentation index](../README.md) · [risks and owner decisions](../migration/risks-and-decisions.md).

Each significant decision has one record. Records are numbered, never
renumbered and never deleted. A changed decision gets a new record that
supersedes the old one; the old record's status is updated to point to it.

Statuses: **Proposed** (recommended, awaiting owner approval or PoC evidence),
**Accepted in direction** (approach approved; details may change with PoC
evidence, recorded in the same ADR), **Accepted**, **Superseded by NNNN**, **Rejected**.

| No. | Decision | Status |
| --- | --- | --- |
| [0001](0001-headless-backend-authority.md) | Headless Python backend is the authoritative owner of project state | Accepted |
| [0002](0002-frontend-stack.md) | Tauri 2 + Vue 3 + TypeScript + Vite + Quasar frontend | Accepted |
| [0003](0003-backend-transport.md) | Multiplexed JSON Lines transport with events and analysis jobs | Accepted in direction (M4 details) |
| [0004](0004-canonical-schematic-model.md) | Canonical schematic data and coordinate connectivity stay in Python | Accepted in direction (M7 details) |
| [0005](0005-schematic-library.md) | Schematic rendering library: maxGraph vs custom SVG | Proposed (decision rule accepted; outcome after M7) |
| [0006](0006-charts.md) | Apache ECharts for interactive graphs; Matplotlib kept for reports | Accepted in direction (M8 details) |
| [0007](0007-mcp-server.md) | MCP server with the official Python SDK, in-process, local HTTP | Accepted |
| [0008](0008-project-format-compatibility.md) | `.gepro` compatibility policy and stable identifiers | Accepted |
| [0009](0009-undo-transactions.md) | Snapshot-based command transactions for undo/redo | Accepted |
| [0010](0010-python-environment-and-sidecar.md) | pixi environment and PyInstaller onedir sidecar | Accepted (measurements in M5) |
| [0011](0011-safe-expressions.md) | Safe expression evaluation replaces `eval`, Mako and pickle | Accepted |
| [0012](0012-engineering-ui-package.md) | EngineeringUI package `@kavilgroup/engineering-ui`, MIT, subpath exports | Accepted |
| [0013](0013-licensing.md) | Distribute under GPL-3.0-or-later; align headers | Accepted |
| [0014](0014-legacy-gtk-location.md) | Legacy GTK UI moves to `gelectrical/gtk/` and retires at parity | Accepted |
| [0015](0015-python-and-pandapower-versions.md) | Python 3.14 with Numba; latest pandapower from PyPI through pixi | Accepted |
| [0016](0016-weasyprint-windows-executable.md) | WeasyPrint executable on Windows; one pinned version everywhere | Accepted |
| [0017](0017-frontend-workspace-build.md) | Frontend workspace resolution, EngineeringUI build and toolchain pins | Proposed (implemented in M6) |
| [0018](0018-headless-engine-split.md) | Headless engine split: model notifications, symbol layers, text backends | Proposed (implemented in M2) |
| [0019](0019-service-layer-implementation.md) | Service layer: snapshot documents with sharing, legacy labels, analysis on copies | Proposed (implemented in M4) |

## Template

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN | Rejected
- Date: YYYY-MM-DD
- Related: links

## Context
## Decision
## Alternatives considered
## Consequences
## Verification
```
