# 0012. EngineeringUI as an internal npm workspace package with subpath exports

- Status: Accepted (licence and name decided by the owner 2026-11-26)
- Date: 2026-11-26
- Related: [EngineeringUI](../architecture/engineering-ui.md), [package AGENTS.md](../../packages/engineering-ui/AGENTS.md)

## Context

GElectrical, GEstimator and future engineering applications need the same
desktop-style components (ribbon, rail, inspectors, grids, charts, drawing
viewport). Separate repositories and packages too early slow development.

## Decision

- One package `packages/engineering-ui/`, npm name `@kavilgroup/engineering-ui`,
  licence **MIT**, in an npm workspace at the repository root, `private: true`
  until extraction, with modular subpath exports (`theme`, `icons`,
  `controls`, `dialogs`, `navigation`, `workspace`, `datagrid`, `inspectors`,
  `charts`, `drawing`, `composables`).
- Third-party libraries are optional peer dependencies per subpath.
- No imports from GElectrical or GEstimator code; enforced by a CI boundary check.
- Storybook is the development and documentation environment.
- Abstractions are added only when a GElectrical feature needs them.

## Alternatives considered

- *Many small packages from the start*: versioning overhead before APIs settle.
- *Components inside `modern/src/`*: blocks reuse and invites coupling.

## Consequences

Extraction later needs only a history-preserving move and publication; the
name and MIT licence are already final. Only MIT-compatible code may enter the
package: GEstimator code is relicensed by its copyright holder on adaptation,
and GPL/LGPL code from other projects is excluded. All peer dependencies (Vue,
Quasar, Tabulator, ECharts, maxGraph) are MIT or Apache-2.0.

## Verification

Standalone build/test/Storybook from the package directory; boundary check.
