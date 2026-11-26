# EngineeringUI

Reusable Vue 3 components for engineering desktop applications.

Status: **current** for the M6 foundation (theme, icons, shell components,
dialog, number input, property inspector). Data grid, charts and drawing
utilities are **planned** (M7, M8, M11). The design is in
[docs/architecture/engineering-ui.md](../../docs/architecture/engineering-ui.md);
contributor rules are in [AGENTS.md](AGENTS.md).

## Purpose

EngineeringUI provides a consistent, accessible, compact desktop interface for
GElectrical first, and later for GEstimator and other engineering tools:
theme tokens, icons, application shell pieces (ribbon, document rail,
workspace panels, status bar), dialogs, unit-aware inputs, a schema-driven
property inspector, and later a data grid, engineering charts and drawing
viewport utilities.

It is independent of any application backend: components take typed props and
emit events. Native capabilities (clipboard, file dialogs) are injected by the
host application.

## Entry points

| Import | Contents | Peer dependencies |
| --- | --- | --- |
| `@kavilgroup/engineering-ui` | Theme registration, `EuiIcon`, shared types | `vue` |
| `@kavilgroup/engineering-ui/theme` | `useTheme()`, `bindQuasarDark()`, font settings | `vue` |
| `@kavilgroup/engineering-ui/icons` | `EuiIcon` and the icon set (`iconNames`) | `vue` |
| `@kavilgroup/engineering-ui/composables` | Roving-focus keyboard helpers | none |
| `@kavilgroup/engineering-ui/navigation` | `EuiRibbon`, `EuiDocumentRail` | `vue` |
| `@kavilgroup/engineering-ui/workspace` | `EuiWorkspace`, `EuiStatusBar`, `EuiNotifications`, `createNotificationQueue()` | `vue` |
| `@kavilgroup/engineering-ui/controls` | `EuiNumberInput`, number formatting helpers | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/dialogs` | `EuiDialog` | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/inspectors` | `EuiPropertyInspector` (schema-driven) | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/style.css` | Tokens, Quasar bridge, base and component styles | — |

Planned: `datagrid` (Tabulator), `charts` (ECharts), `drawing`, `EuiAppMenu`,
`EuiCommandPalette`, `EuiSelect`.

Hosts load Quasar's CSS, then `style.css`, install Quasar, and register the
theme:

```ts
import { Dark, Quasar } from "quasar";
import "quasar/src/css/index.sass"; // with @quasar/vite-plugin
import "@kavilgroup/engineering-ui/style.css";
import { bindQuasarDark, useTheme } from "@kavilgroup/engineering-ui/theme";

useTheme({ initial: "system" });
bindQuasarDark(Dark);
app.use(Quasar, { plugins: { Dark } });
```

Inside this repository the exports carry a `source` condition, so `modern/`
uses the sources without a library build ([ADR 0017](../../docs/decisions/0017-frontend-workspace-build.md)).

## Development

```bash
npm ci                                              # at the repository root (npm workspaces)
npx playwright install chromium-headless-shell      # once, for the Storybook story tests
npm run storybook -w @kavilgroup/engineering-ui     # component development and docs (port 6006)
npm run test -w @kavilgroup/engineering-ui          # Vitest: unit tests and story tests with axe
npm run build -w @kavilgroup/engineering-ui         # library build with type declarations (dist/)
npm run build-storybook -w @kavilgroup/engineering-ui
node tools/check_boundaries.mjs                     # from the repository root
```

`npm test` runs two Vitest projects: `unit` (happy-dom, `tests/`) and
`storybook` (every story in Chromium through Playwright, play functions and
axe checks; any violation fails).

## Provenance

GEstimator code is relicensed from GPL-3.0-or-later to MIT by its copyright
holder when adapted; adapted files carry the MIT header plus an
`Adapted from GEstimator <path> at <commit>` line. All rows below use GEstimator
commit `e4e4fb295899feda5253ba216613c70c1f256d4e`.

| EngineeringUI file | GEstimator source | Licence |
| --- | --- | --- |
| `src/icons/iconPaths.ts`, `src/icons/EuiIcon.vue` | `modern/src/components/AppIcon.vue` | GPL-3.0-or-later → MIT |
| `src/theme/tokens.css` | `modern/src/theme.css` | GPL-3.0-or-later → MIT |
| `src/theme/useTheme.ts` | `modern/src/appearance.ts` | GPL-3.0-or-later → MIT |
| `src/navigation/EuiRibbon.vue`, `src/navigation/ribbonFit.ts` | `modern/src/components/RibbonToolbar.vue`, ribbon rules in `modern/src/style.css` | GPL-3.0-or-later → MIT |
| `src/navigation/EuiDocumentRail.vue` | `modern/src/components/DocumentRail.vue`, rail rules in `modern/src/style.css` | GPL-3.0-or-later → MIT |
| `src/navigation/documentTiles.ts` | `modern/src/documents.ts` (`documentCode`, `documentColour`) | GPL-3.0-or-later → MIT |
| `src/workspace/notifications.ts` | `modern/src/statusNotice.ts` | GPL-3.0-or-later → MIT |
| `src/dialogs/EuiDialog.vue` | `modern/src/components/PersistentDialog.vue` | GPL-3.0-or-later → MIT |

The electrical glyphs in `iconPaths.ts` and all other files are new.
Open Planner Studio is a visual reference only; no code or artwork is copied.
Code from other authors or GPL/LGPL projects must not be added, because it
cannot be relicensed under MIT.

## Dependencies and licences

Runtime peers: Vue 3.5 (MIT), Quasar 2.36 (MIT, optional). Development tools
(Vite, Vitest, Storybook, Playwright, TypeScript, vue-tsc, happy-dom,
@vue/test-utils) are MIT or Apache-2.0; axe-core (through the Storybook a11y
addon) and lightningcss (through Vite) are MPL-2.0 and used only in
development. `npm run check:licences` at the repository root checks every
installed package.

## Licence

MIT ([LICENSE](LICENSE); decided 2026-11-26,
[ADR 0012](../../docs/decisions/0012-engineering-ui-package.md)).
GElectrical as a whole remains GPL-3.0-or-later; an MIT package inside a GPL
application is compatible.
