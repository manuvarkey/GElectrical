# 0017. Frontend workspace resolution, EngineeringUI build and toolchain pins

- Status: Proposed (implemented in M6; awaiting owner approval with the M6 PR)
- Date: 2026-11-26
- Related: [ADR 0002](0002-frontend-stack.md), [ADR 0012](0012-engineering-ui-package.md), [EngineeringUI](../architecture/engineering-ui.md), [frontend](../architecture/frontend.md), [validation log](../migration/validation.md)

## Context

M6 sets up the npm workspaces (`modern/`, `packages/engineering-ui/`). Four
choices were needed that the Phase 1 documents leave open:

1. How `modern/` consumes EngineeringUI during development without a library
   build after every change, while the package still builds and publishes
   standalone.
2. Which EngineeringUI subpaths depend on Quasar.
3. How the Quasar Vite plugin interacts with the library build.
4. Toolchain versions: TypeScript 7.0 (native compiler) is the latest release,
   but `vue-tsc` 3.3 needs the TypeScript JavaScript API.

## Decision

- **`source` export condition.** Each EngineeringUI export lists a `source`
  condition pointing at `src/`, then `types` and `import` pointing at `dist/`.
  `modern/vite.config.ts` adds `source` to `resolve.conditions` and
  `modern/tsconfig.json` to `customConditions`. Development and tests use the
  sources; consumers without the condition (and an extracted package) use
  `dist/`. No path aliases into the package.
- **Quasar only where it adds value.** `controls`, `dialogs` and `inspectors`
  use Quasar (`QInput`, `QSelect`, `QDialog`, `QCard`, `QBtn`). The root entry,
  `theme`, `icons`, `composables`, `navigation` and `workspace` are
  toolkit-independent (Vue only), so Quasar stays an optional peer dependency.
  Boolean fields use a native check box, and `EuiDialog` handles Enter and
  Escape itself by `KeyboardEvent.key` (Quasar's check box and Escape handling
  read the deprecated `keyCode`).
- **No Quasar plugin in the library build.** `@quasar/vite-plugin` rewrites
  `import { QBtn } from "quasar"` into deep `quasar/src/...` paths. The
  package's Vite config enables it only under Vitest; Storybook adds it in
  `viteFinal`. The library output imports Quasar by its public entry.
  `modern/` uses the plugin as ADR 0002 requires.
- **Toolchain pins.** TypeScript **6.0.3** (last JavaScript-based release)
  until `vue-tsc` supports TypeScript 7. All npm dependencies are pinned to
  exact versions (`.npmrc` `save-exact=true`); peer ranges stay ranges.
  Playwright is pinned to 1.65.0 through a root `overrides` entry so the
  Storybook Vitest provider and the package use one browser revision.
- **Global stylesheet.** Hosts import `@kavilgroup/engineering-ui/style.css`
  (tokens, Quasar bridge, base rules) after Quasar's CSS; component styles ship
  in the same file in `dist/`.

## Alternatives considered

- *Vite/TypeScript path aliases to `packages/engineering-ui/src`*: couples the
  app to the package layout and hides missing exports until extraction.
- *Always build the library before running the app*: slower feedback; the
  `source` condition gives the same result without a build step.
- *Quasar for every component (QCheckbox, QDialog Escape)*: keyboard handling
  depends on `keyCode`, which synthetic events in tests do not set; native and
  `key`-based handling is simpler and testable.
- *TypeScript 7.0*: `vue-tsc` fails to load it.

## Consequences

- `npm run dev -w gelectrical-modern` works on a fresh checkout without
  building the package; `npm run build -w @kavilgroup/engineering-ui` produces
  `dist/` with type declarations for publication.
- The dependency-boundary check (`tools/check_boundaries.mjs`) also verifies
  that the root, `theme`, `icons` and `composables` entries never reach Quasar.
- Revisit the TypeScript pin when `vue-tsc` supports TypeScript 7.

## Verification

`npm run check` (Prettier, boundary, licences, tool tests, `vue-tsc`, Vitest
unit and Storybook story tests with axe, library and app builds) and
`npm run build-storybook`; results in the [validation log](../migration/validation.md).
