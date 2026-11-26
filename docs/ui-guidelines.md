# UI guidelines

Status: **proposed** rules for the modern desktop interface (Phase 1).
Navigation: [documentation index](README.md) · [frontend](architecture/frontend.md)
· [EngineeringUI](architecture/engineering-ui.md).

GElectrical should look and behave like a professional engineering desktop
application, not a web dashboard. Visual and interaction references:
GEstimator's modern workspace and Open Planner Studio (OpenAEC tokens and
two-tone icon grammar, used as references only).

## 1. Ownership

- Engineering rules, validation and calculations live in Python. Components
  render backend results and collect input.
- Semantic tokens live in EngineeringUI `theme/tokens.css`; components use
  tokens, never literal colours or ad-hoc sizes.
- Shared behaviour lives in EngineeringUI components or app composables; do not
  copy a component to change one detail.
- User-facing text describes GElectrical behaviour only; never mention the GTK
  application or implementation references in labels or messages.

## 2. Layout

- Custom title bar; context-sensitive **ribbon** with tabs Home, Insert,
  Analysis, Protection, View and contextual tabs (for example MCP or a selected
  element type). Short captions, icons and explanatory tooltips; measured
  overflow (GEstimator `RibbonToolbar` behaviour).
- **Document rail** at the left edge for open projects (two-letter tiles, dirty
  marker, flyout with name and path, add tile).
- **Left panel**: searchable component palette (grouped like today, advanced
  elements hidden unless enabled), sheet navigator, database browser.
- **Centre**: sheet tabs above the schematic canvas; zoom controls and
  coordinates in the status bar.
- **Right inspector**: Properties, Results and Messages tabs; context-sensitive
  to selection.
- **Bottom panel** (collapsible): messages, diagnostics, rules check, analysis log.
- All panels collapse and resize; layout state is remembered per user.
- Start page when no project is open: New, Open, recent projects, recovery
  checkpoints.

## 3. Density, typography and themes

- Compact desktop control sizes (Quasar `dense` everywhere, 24–28 px rows).
- System fonts for interface and tables by default, independently configurable
  (program settings), as in GEstimator. The schematic uses the bundled
  schematic font so screen and PDF match.
- Light, dark and system themes; light and dark equally usable. Schematic
  colours come from tokens (normal, inactive, selected, warning, grid, overlay)
  and the PDF always uses print colours.
- Warm amber accent for selection and focus emphasis; semantic green (apply),
  red (destructive), amber (warning), blue (info) with text labels so meaning
  never depends on colour alone.

## 4. Icons

- All icons go through `EuiIcon` from a local SVG set on a 24-unit grid with
  round caps/joins, open line work and at most one accent detail (GEstimator /
  OpenAEC B2 grammar, drawn locally, not copied).
- Element palette icons reuse the existing `gelectrical/icons/*.svg`, restyled
  for both themes.

## 5. Interaction rules

- **Keyboard:** every command has a keyboard path; existing shortcuts are kept
  (`Ctrl+N` new sheet, `Ctrl+X/C/V`, `Ctrl+Z`, `Ctrl+Shift+Z`, `Ctrl+W` wire,
  `Ctrl+G` assembly, `Ctrl+A`, `Escape`, `Delete`, `R`, `C` while inserting,
  `Ctrl++/-` zoom, `Ctrl+S` save). A command palette lists all commands.
- **Selection:** click selects; Shift toggles; drag on empty canvas box-selects;
  Escape cancels the current mode, then clears selection.
- **Modes:** insert and wire modes are visible in the status bar with a hint
  ("Click to place · R rotate · C cycle port · Esc cancel").
- **Edits:** committed on Enter or focus loss; Escape reverts the field. Invalid
  input stays in the field with the backend's message; it is never silently
  replaced.
- **Numbers:** unit shown beside the field; arithmetic entry allowed where it
  is today; values displayed with the field's `decimal` precision; raw value
  preserved for editing.
- **Multiple selection:** shared fields editable; differing values shown as
  "multiple values" placeholder.
- **Dialogs** for bounded tasks only (settings, analysis options, renumber,
  link references, database item selection); Enter applies, Escape cancels;
  focus trapped and restored.
- **Notifications:** transient results in the status bar; errors stay visible
  until resolved; analysis progress in the status bar and bottom panel.
- **Results overlays** on the schematic are toggleable layers (node voltages,
  fault levels, loading colours, rule violations) and never edit the document.
- **AI changes** from MCP are highlighted and listed for review.

## 6. Accessibility

- Visible focus on every interactive element; logical tab order.
- Accessible names for icon-only buttons and canvas elements (element name and
  reference).
- Contrast at least WCAG AA for text and 3:1 for icons and focus indicators.
- Storybook a11y checks must pass for EngineeringUI components.

## 7. Before completing a UI change

Build the frontend, run Vitest and the affected Playwright workflows, check
keyboard operation, disabled/busy states, narrow layouts and both themes, and
record native WebView checks that still need a packaged build.
