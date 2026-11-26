# 0002. Tauri 2 + Vue 3 + TypeScript + Vite + Quasar frontend

- Status: Accepted (stack selected by the owner in the Phase 1 brief)
- Date: 2026-11-26
- Related: [frontend](../architecture/frontend.md), [EngineeringUI](../architecture/engineering-ui.md)

## Context

The brief selects Tauri 2, Vue 3, TypeScript, Vite, Quasar, npm workspaces,
Storybook, Tabulator, ECharts and (subject to PoC) maxGraph. GEstimator, the
reference application, uses the same shell and framework but **PrimeVue**
instead of Quasar.

## Decision

Use the selected stack. Quasar 2 is integrated with `@quasar/vite-plugin`
(no Quasar CLI) so the Vite configuration stays close to GEstimator's. Quasar
provides layout, menus, dialogs, inputs, tree, splitter, notifications and dark
mode. EngineeringUI tokens are bridged onto Quasar CSS variables.

## Alternatives considered

- *PrimeVue (GEstimator parity)*: would allow direct component reuse, but the
  owner selected Quasar. GEstimator's PrimeVue use is light (mainly dialogs,
  menus and autocomplete), so porting cost is moderate.
- *No component toolkit*: more custom code for standard controls.

## Consequences

- Components adapted from GEstimator are ported to Quasar or written
  toolkit-independent (EngineeringUI core subpaths do not depend on Quasar).
- If GEstimator later adopts EngineeringUI, it either adds Quasar for the
  subpaths that need it or EngineeringUI offers toolkit-independent variants.
  This is tracked as an open question for extraction.

## Verification

M6 PoC: theme bridge, compact density, keyboard behaviour and accessibility in
Storybook.
