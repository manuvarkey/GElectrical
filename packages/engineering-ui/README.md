# EngineeringUI

Reusable Vue 3 components for engineering desktop applications.

Status: **planned** (milestone M6). This folder currently contains only
documentation. The design is in
[docs/architecture/engineering-ui.md](../../docs/architecture/engineering-ui.md);
contributor rules are in [AGENTS.md](AGENTS.md).

## Purpose

EngineeringUI provides a consistent, accessible, compact desktop interface for
GElectrical first, and later for GEstimator and other engineering tools:
theme tokens, icons, application shell pieces (ribbon, document rail,
workspace panels, status bar), dialogs, unit-aware inputs, a schema-driven
property inspector, a Tabulator data grid, ECharts-based engineering charts and
curve editors, and drawing viewport utilities.

It is independent of any application backend: components take typed props and
emit events. Native capabilities (clipboard, file dialogs) are injected by the
host application.

## Planned entry points

| Import | Contents | Peer dependencies |
| --- | --- | --- |
| `@kavilgroup/engineering-ui` | Theme registration, icon component, shared types | `vue` |
| `@kavilgroup/engineering-ui/theme` | Tokens, Quasar bridge, `useTheme()` | `vue` |
| `@kavilgroup/engineering-ui/icons` | `EuiIcon` and icon set | `vue` |
| `@kavilgroup/engineering-ui/controls` | Unit-aware number input, select, autocomplete, toggles | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/dialogs` | Dialog, confirm, settings page | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/navigation` | Ribbon, application menu, command palette, document rail | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/workspace` | Panel layout, status bar, notifications | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/inspectors` | Property inspector, result list, message list | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/datagrid` | Data grid and cell navigation | `vue`, `tabulator-tables` |
| `@kavilgroup/engineering-ui/charts` | Chart wrapper, log-log plot, curve editor, series chart | `vue`, `echarts` |
| `@kavilgroup/engineering-ui/drawing` | Viewport, grid, snapping, selection, symbol sprites | `vue` (maxGraph adapter optional) |

## Development (once M6 lands)

```bash
npm ci                                   # at the repository root (npm workspaces)
npm run storybook -w @kavilgroup/engineering-ui      # component development and docs
npm run test -w @kavilgroup/engineering-ui           # Vitest component tests
npm run build -w @kavilgroup/engineering-ui          # library build with type declarations
```

## Provenance

Components adapted from other projects are listed here with source path and
commit. GEstimator code is relicensed from GPL-3.0-or-later to MIT by its
copyright holder when adapted; adapted files carry the MIT header plus an
`Adapted from GEstimator <path> at <commit>` line.

| Component | Source | Commit | Licence |
| --- | --- | --- | --- |
| *(none yet)* | | | |

GEstimator (same copyright holder) is the main source of adapted components.
Open Planner Studio is a visual reference only; no code or artwork is copied.
Code from other authors or GPL/LGPL projects must not be added, because it
cannot be relicensed under MIT.

## Licence

MIT (decided 2026-11-26, [ADR 0012](../../docs/decisions/0012-engineering-ui-package.md)).
The package will carry its own `LICENSE` file. GElectrical as a whole remains
GPL-3.0-or-later; an MIT package inside a GPL application is compatible.
