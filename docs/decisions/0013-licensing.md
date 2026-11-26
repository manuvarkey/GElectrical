# 0013. Distribute under GPL-3.0-or-later; align headers

- Status: Accepted (owner 2026-11-26)
- Date: 2026-11-26
- Related: [licence inventory](../migration/risks-and-decisions.md#4-licence-inventory-target-stack)

## Context

`LICENSE` contains the GPLv3 text. Python source headers state "GPL version 2
or (at your option) any later version". The target stack includes Apache-2.0
components (ECharts, maxGraph, TypeScript, Playwright at test time), which are
compatible with GPL-3.0 but not with GPL-2.0-only. GEstimator declares
GPL-3.0-or-later in its Tauri bundle metadata.

## Decision

- The distributed modern application is licensed **GPL-3.0-or-later**, as the
  current "or later" headers permit.
- New files use a GPL-3.0-or-later header (or SPDX
  `GPL-3.0-or-later`); existing headers are updated by the copyright holder.
- Bundles declare `GPL-3.0-or-later` and ship third-party licence notices
  (generated from npm, Cargo and pixi metadata).

## Alternatives considered

Keep mixed statements: ambiguous for distributors and packagers.

## Consequences

Contributors' code is accepted under GPL-3.0-or-later, except
`packages/engineering-ui/`, which is MIT ([ADR 0012](0012-engineering-ui-package.md)).
An MIT package inside the GPL application is compatible.

## Verification

Licence check job in CI listing all bundled dependency licences; release
checklist item.
