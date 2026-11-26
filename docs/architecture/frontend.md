# Frontend architecture

Status: **current** for the M6 foundation (npm workspaces, Vite + Vue +
strict TypeScript + Quasar, mock-data shell in `modern/`); **proposed** for
everything that needs the backend (sessions, services, Tauri). Navigation: [index](../README.md) ·
[architecture overview](../../ARCHITECTURE.md) · [EngineeringUI](engineering-ui.md)
· [UI guidelines](../ui-guidelines.md) · [backend](backend.md).

The frontend is a Vue 3 + TypeScript application built with Vite and hosted by
Tauri 2. It renders authoritative backend state, collects input and provides
visual feedback. It never calculates or validates engineering values.

## 1. Stack

| Concern | Choice | Notes |
| --- | --- | --- |
| Framework | Vue 3 (Composition API, `<script setup>`) | Small single-purpose components |
| Language | TypeScript (strict) | `any` only inside documented third-party adapters |
| Build | Vite + `@vitejs/plugin-vue` | Dev server for browser tests |
| Component toolkit | Quasar 2 via `@quasar/vite-plugin` (no Quasar CLI) | Layout, menus, dialogs, inputs, tree, splitter, notify, dark mode |
| Shared UI | `@kavilgroup/engineering-ui` workspace package | See [EngineeringUI](engineering-ui.md) |
| Tables | Tabulator (through EngineeringUI `datagrid`) | Database browser, schedules, results tables |
| Charts | Apache ECharts (through EngineeringUI `charts`) | Protection coordination, load profiles, result graphs |
| Schematic | maxGraph or custom SVG (decided by PoC) | See [schematic editor](schematic-editor.md) |
| Native | `@tauri-apps/api`, plugins dialog, clipboard-manager, single-instance, opener | File I/O happens in Python |
| State | Composables with `reactive`/`ref`; no global store library initially | Add Pinia only with an ADR if composables become insufficient |

GEstimator uses PrimeVue; GElectrical uses Quasar as selected for this
project. Components adapted from GEstimator are ported to Quasar primitives or
to toolkit-independent EngineeringUI components ([ADR 0002](../decisions/0002-frontend-stack.md)).

Current commands (M6, repository root): `npm ci`, `npm run dev` (shell on
`http://127.0.0.1:1420` with mock data), `npm run check` (format, boundary,
licences, type check, Vitest, builds), `npm run storybook`.

## 2. Directory layout (`modern/src/`)

```text
modern/src/
├── main.ts                 # createApp, Quasar plugin, EngineeringUI theme, router-less shell
├── App.vue                 # shell composition only (ribbon, rail, panels, status bar)
├── views/                  # workspace views: SchematicView, DatabaseView, ProtectionView,
│                           # LoadProfileView, AnalysisView, ReportView, StartView
├── components/             # GElectrical-specific components (ribbons, dialogs, inspectors)
├── composables/            # useSession, useDocuments, useSelection, useCommands,
│                           # useAnalysisJob, useBackendEvents, useShortcuts
├── services/
│   ├── backend.ts          # typed JSON Lines client over Tauri invoke + events
│   ├── commands.ts         # command wrappers: revision, preview, error mapping
│   └── native.ts           # Tauri dialogs, clipboard, file-open queue
├── types/                  # generated DTO types + hand-written view types
└── assets/                 # app icons, symbol sprites (generated)
```

M6 has `main.ts`, `App.vue`, `ribbon.ts`, `components/` (palette, schematic
placeholder, messages, settings dialog), `composables/useShell.ts` (view
state and mock commands) and `mock/` (mock documents and a load field schema
in the backend FieldSchema shape). `services/` arrives with M9.

Rules:

- `App.vue` composes; it does not own workflows. Extract a composable or
  component before adding a concern to the shell (GEstimator lesson: its
  `App.vue` grew past 1,000 lines).
- Components under `components/` may import EngineeringUI; EngineeringUI never
  imports from `modern/`.
- Backend method names appear only in `services/` and composables, never in
  EngineeringUI.

## 3. Data ownership

| Kind | Owner | Examples |
| --- | --- | --- |
| Authoritative state | Python, cached per session and revision | Elements, fields, field state, results, messages, settings |
| View state | Vue composables (per document) | Selection, zoom/pan, active sheet, panel sizes, expanded nodes |
| Transient edit state | Component | Drag preview, rubber band, typed but uncommitted value |
| Preferences | Python program settings (persisted); `localStorage` only for cosmetic UI memory | Theme, fonts, recent files |

The cache is replaced from backend responses. Optimistic display is allowed
only for transient feedback (for example, an element following the pointer);
the committed position always comes from the backend response.

## 4. Backend client

- `backend.request(method, params, {session})` sends one JSON Lines request
  through the Tauri command `backend_request` and resolves when the matching
  response arrives. Multiple requests may be in flight.
- `useBackendEvents` subscribes to Tauri events (`backend-changed`,
  `backend-progress`, `backend-job`) and dispatches them to sessions.
- Commands send `if_revision` from the cache. `STALE_REVISION` triggers a
  refresh and keeps the user's typed value in the editor for retry.
- DTO types are generated from backend JSON Schemas (proposed tool:
  `json-schema-to-typescript`, MIT) to avoid hand-maintained duplicates.

## 5. Documents and sessions

- Each open project is a backend session shown in the document rail
  (GEstimator's `DocumentRail` pattern). The active document's workspace is
  mounted; others keep their backend state and remembered view state.
- New/Open/Close/window close pass through one unsaved-work guard.
- OS file-open and drag-and-drop requests are queued and drained through the
  same guard (GEstimator `projectOpening.ts` pattern).
- MCP acts on the active session; MCP changes arrive as `changed` events with
  `source: "mcp"` and are highlighted (see [MCP](mcp.md)).

## 6. Workspace composition

```text
┌ Title bar (custom, Tauri decorations off) ─────────────────────────────┐
│ Ribbon: Home | Insert | Analysis | Protection | View | MCP (contextual)│
├──┬───────────────┬──────────────────────────────────────┬──────────────┤
│R │ Left panel     │ Sheet tabs                           │ Inspector    │
│a │ Palette /      │ Schematic canvas                     │ Properties | │
│i │ Navigator /    │ (overlays: results, selection,       │ Results |    │
│l │ Database       │  diagnostics markers)                │ Messages     │
│  ├───────────────┴──────────────────────────────────────┴──────────────┤
│  │ Bottom panel (collapsible): Messages, Analysis log, Rules check       │
├──┴──────────────────────────────────────────────────────────────────────┤
│ Status bar: selection, coordinates, zoom, revision/dirty, job, MCP      │
└─────────────────────────────────────────────────────────────────────────┘
```

Panels are collapsible and resizable (Quasar `QSplitter`/drawers or the
EngineeringUI workspace layout); sizes are view state.

## 7. Native integration

- File dialogs return paths; Python opens, saves and exports files.
- Clipboard: copy/paste uses a versioned JSON payload produced and validated by
  Python (no pickle). The frontend only transports the text.
- Printing: export a PDF via Python and hand it to the OS viewer (approved
  2026-11-26; feature F02 `Changed`).
- Fonts: system fonts for the interface; the schematic font is bundled and
  loaded as a web font for SVG rendering and as a file for Cairo PDF output.

## 8. Testing

- Vitest for composables and components (`modern/src/**/*.spec.ts`).
- Playwright for workflows in a browser against the **real Python backend**
  through a test bridge that replaces only the Tauri transport (GEstimator
  `workspaceHarness.ts` pattern).
- Native Tauri behaviour (file association, single instance, sidecar
  lifecycle) is checked separately on packaged builds. See the
  [testing guide](../testing.md).
