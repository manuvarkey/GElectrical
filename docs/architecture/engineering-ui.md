# EngineeringUI

Status: **proposed** (Phase 1). Package rules for contributors are in
[packages/engineering-ui/AGENTS.md](../../packages/engineering-ui/AGENTS.md).
Navigation: [index](../README.md) · [frontend](frontend.md) ·
[UI guidelines](../ui-guidelines.md) · [ADR 0012](../decisions/0012-engineering-ui-package.md).

EngineeringUI is a reusable Vue 3 component library for engineering desktop
applications: GElectrical first, then GEstimator and future applications. It
starts as a local npm workspace package inside this repository and is designed
so it can move to its own repository without changing its public interface.

## 1. Boundaries

EngineeringUI **may**:

- Render typed data received through props and emit typed events.
- Own presentation state (focus, hover, open/closed, local drag preview).
- Provide theme tokens, icons, layout, controls, dialogs, data grid, charts,
  drawing viewport utilities and generic composables.
- Wrap third-party libraries (Quasar, Tabulator, ECharts, maxGraph) behind
  stable component APIs.

EngineeringUI **must not**:

- Import anything from `modern/`, `gelectrical/` or GEstimator.
- Know backend method names, session IDs, revisions or project schemas.
- Call Tauri APIs directly. Native capabilities are injected through
  interfaces (for example a `ClipboardAdapter` or `FileDialogAdapter`).
- Hold global application state or singletons other than theme registration.
- Perform engineering calculations or validation. A unit-aware input formats
  and parses display text; validation messages come from the host.

## 2. Package layout and exports

```text
packages/engineering-ui/
├── package.json            # name "@kavilgroup/engineering-ui", licence MIT
├── src/
│   ├── theme/              # tokens.css, quasar-bridge.css, typography, useTheme()
│   ├── icons/              # EuiIcon + local SVG icon set (24-unit grid)
│   ├── controls/           # EuiNumberInput (units), EuiSelect, EuiAutocomplete, EuiToggle
│   ├── dialogs/            # EuiDialog, EuiConfirm, EuiSettingsPage
│   ├── navigation/         # EuiRibbon, EuiAppMenu, EuiCommandPalette, EuiDocumentRail
│   ├── workspace/          # EuiWorkspace (panels/splitters), EuiStatusBar, EuiNotifications
│   ├── datagrid/           # EuiDataGrid (Tabulator adapter), cell navigation helpers
│   ├── inspectors/         # EuiPropertyInspector (schema-driven), EuiResultList, EuiMessageList
│   ├── charts/             # EuiChart (ECharts adapter), EuiCurveEditor, EuiLogLogPlot
│   ├── drawing/            # viewport (zoom/pan), grid, snapping, selection, SVG symbol sprite
│   ├── composables/        # useShortcuts, useResizeObserver, useFocusTrap, useKeyboardList
│   └── index.ts            # root export: theme + icons + types only
├── .storybook/
├── stories/
├── tests/                  # Vitest component tests
├── README.md, AGENTS.md
```

Subpath exports keep heavy dependencies optional:

| Import path | Peer dependencies |
| --- | --- |
| `@kavilgroup/engineering-ui` | `vue` |
| `@kavilgroup/engineering-ui/theme`, `@kavilgroup/engineering-ui/icons` | `vue` |
| `@kavilgroup/engineering-ui/controls`, `/dialogs`, `/navigation`, `/workspace`, `/inspectors` | `vue`, `quasar` |
| `@kavilgroup/engineering-ui/datagrid` | `vue`, `tabulator-tables` |
| `@kavilgroup/engineering-ui/charts` | `vue`, `echarts` |
| `@kavilgroup/engineering-ui/drawing` | `vue`; `@maxgraph/core` only in its maxGraph adapter subpath |

Peer dependencies are declared as optional where a subpath does not need them.
A host that never imports `charts` never loads ECharts.

## 3. Component API conventions

- Props in, events out. `v-model` only for simple values.
- Typed props with exported TypeScript interfaces (`EuiFieldSchema`,
  `EuiCurveSeries`, `EuiRibbonGroup`, ...).
- No backend-specific naming: an inspector receives `fields: EuiFieldSchema[]`
  and `values`, emits `change(code, rawText | value)` and shows `errors` passed in.
- Keyboard first: every interactive component supports keyboard operation and
  visible focus; documented in its story.
- Styling through tokens (CSS custom properties). Components never hard-code
  colours or sizes; compact density is the default.
- Each component is small and has separate template, script and style blocks.

## 4. Theme and tokens

- `theme/tokens.css` defines semantic tokens: surfaces (frame, panel, field,
  workspace), text, borders, accent (warm amber, Open Planner Studio
  reference), selection, focus ring, semantic states (success, warning, danger,
  info), schematic colours (normal, inactive, selected, warning, grid, overlay),
  chart palette, spacing, radii, font families and sizes.
- Light, dark and system themes switch by attribute on the root element
  (`data-theme`), mapped onto Quasar's `Dark` plugin and `--q-*` brand variables
  by `theme/quasar-bridge.css`.
- Interface and table fonts follow the platform default unless overridden by
  settings, as in GEstimator.

## 5. Candidate components from GEstimator

GEstimator (GPL-3.0-or-later, same copyright holder) is the main source. Its
PrimeVue usage is light (25 files, mostly `Dialog`, plus `Menu`, `Popover`,
`AutoComplete`, `FocusTrap`), so porting to Quasar is moderate. Most work is
removing GEstimator-specific state and command names.

| GEstimator source | EngineeringUI target | Assessment |
| --- | --- | --- |
| `RibbonToolbar.vue` | `navigation/EuiRibbon` | Reuse structure (groups, measured overflow, tooltips); remove app commands; port to Quasar buttons |
| `DocumentRail.vue` | `navigation/EuiDocumentRail` | Reuse; tiles, dirty dot, flyout; generic tab model |
| `ApplicationMenu.vue`, `KeyboardShortcutsDialog.vue` | `navigation/EuiAppMenu`, `dialogs/EuiShortcutsDialog` | Reuse layout; data-driven entries |
| `AppIcon.vue` + local SVG paths | `icons/EuiIcon` | Reuse mechanism and drawing grammar; add electrical glyphs |
| `theme.css`, `style.css`, `appearance.ts` | `theme/` | Reuse token naming and themes; split app-specific rules out |
| `statusNotice.ts` | `workspace/EuiNotifications` + composable | Reuse; bridge to Quasar Notify or keep custom |
| `PersistentDialog.vue` | `dialogs/EuiDialog` | Adapt to `QDialog` |
| `ThemedDropdowns.vue`, `ThemedAutocomplete.vue` | `controls/EuiSelect`, `EuiAutocomplete` | Evaluate against `QSelect`; keep GEstimator keyboard behaviour |
| `DataTable.vue`, `cellNavigation.ts`, `tableSelection.ts`, `tableTextEditor.ts`, `virtualRows.ts` | `datagrid/` | Reuse Tabulator integration and navigation helpers; remove schedule-specific logic |
| `WorkbookSheetGrid.vue` | `datagrid/EuiSheetPreview` | Reuse for spreadsheet import preview |
| `ProgramSettings.vue`, `MCPSettings.vue`, `MCPRibbon.vue`, `mcp.ts` | `dialogs/EuiSettingsPage`, `workspace/EuiServiceStatus` | Reuse generic layout and status display; MCP specifics stay in the app |
| `numberFormatting.ts`, `middleEllipsis.ts`, `typeAhead.ts`, `liveSearch.ts` | `composables/` | Reuse generic helpers |
| `backend.ts`, `useWorkspace*.ts`, `ProjectViews.vue` | not in EngineeringUI | Application-specific; inform `modern/src/services` only |

Open Planner Studio (LGPL-3.0-or-later, React) is a **visual reference only**.
Its tokens and two-tone icon grammar inform the theme; no code or B2 artwork
(LGPL-3.0-only) is copied.

## 6. Provenance

- EngineeringUI is MIT licensed. GEstimator code is relicensed to MIT by its
  copyright holder when adapted: adapted files use the MIT header and add
  `Adapted from GEstimator <path> at <commit>`.
- Only code whose copyright holder agrees to MIT may enter the package; no
  GPL/LGPL code from other projects.
- `packages/engineering-ui/README.md` keeps a provenance table.
- Third-party code is used only through package dependencies with recorded
  licences; no vendored copies without an ADR.

## 7. Storybook

- `@storybook/vue3-vite`, with `@storybook/addon-a11y` and the Vitest addon for
  running stories as browser tests (Playwright provider). All local; no
  Chromatic or hosted service.
- Each component has stories for: default use, light and dark theme, disabled
  and read-only, validation errors, narrow and wide containers, large datasets
  (grids, charts), keyboard interaction (play functions) and engineering
  units where relevant.
- Storybook MCP integration for AI-assisted component discovery is evaluated as
  an optional development aid only (milestone M6); it must not become a build
  or runtime dependency.

## 8. Extraction strategy

The package is extractable when:

1. It builds, tests and runs Storybook from its own directory with only its
   declared dependencies (`npm run build -w @kavilgroup/engineering-ui`).
2. A dependency check confirms no imports from outside `packages/engineering-ui/`.
3. Public API is limited to the documented subpath exports, with types emitted
   (`vite build` library mode + `vue-tsc --declaration`).
4. Licence and provenance records are complete.

Extraction steps: move the folder with history (`git filter-repo`), publish
as `@kavilgroup/engineering-ui`, replace the workspace dependency with a versioned
dependency, and keep a changelog with semantic versioning. Until then, it is
versioned with GElectrical and marked `private: true`.

The package name is `@kavilgroup/engineering-ui` from the start, so extraction
needs no import renames. The licence is **MIT** (decided 2026-11-26) to
encourage reuse; GElectrical and GEstimator remain GPL-3.0-or-later.
