# EngineeringUI rules for coding agents

These rules apply to everything under `packages/engineering-ui/`. They add to
the repository [AGENTS.md](../../AGENTS.md). Read
[docs/architecture/engineering-ui.md](../../docs/architecture/engineering-ui.md)
and [docs/ui-guidelines.md](../../docs/ui-guidelines.md) before changing code.

## Boundaries (mandatory)

- Never import from `modern/`, `gelectrical/`, GEstimator or any application
  package. The CI boundary check must stay green.
- No backend method names, session IDs, revisions or project schemas in
  component APIs. Use neutral names (`fields`, `values`, `series`, `items`).
- No direct Tauri calls. Accept adapters (for example `ClipboardAdapter`) as
  props or provide/inject keys.
- No global mutable state except theme registration.
- No engineering calculations or validation. Inputs parse and format display
  text; the host supplies validation messages.
- Add an abstraction only when an application feature needs it now.

## Structure

- Put each component in the matching folder (`theme`, `icons`, `controls`,
  `dialogs`, `navigation`, `workspace`, `datagrid`, `inspectors`, `charts`,
  `drawing`, `composables`) and export it from that folder's `index.ts` subpath.
- Heavy libraries (Quasar, Tabulator, ECharts, maxGraph) are optional peer
  dependencies imported only inside their subpath.
- Keep components small, with separate `<template>`, `<script setup lang="ts">`
  and scoped `<style>` blocks. Prefix public components with `Eui`.
- Export TypeScript interfaces for every public prop and event payload.

## Styling and accessibility

- Use tokens from `theme/tokens.css`; no literal colours or ad-hoc sizes.
- Compact density by default; light, dark and system themes.
- Keyboard operation and visible focus for every interactive component;
  accessible names for icon-only controls.

## Stories and tests (required for every public component)

- Storybook stories: default, light and dark, disabled/read-only, validation
  error, narrow and wide, large dataset where relevant, keyboard interaction
  (play function), engineering units where relevant.
- Vitest tests for behaviour (events, keyboard, edge cases).
- Storybook a11y checks without serious violations.

## Provenance

EngineeringUI is **MIT** licensed. When adapting code from GEstimator (same
copyright holder, relicensed to MIT on adaptation), use the MIT header, add
`Adapted from GEstimator <path> at <commit>`, and add a row to the provenance
table in [README.md](README.md). Never copy GPL/LGPL code or code by other
authors into this package. New dependencies must be MIT-compatible
(MIT, BSD, Apache-2.0, ISC).
