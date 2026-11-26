# Testing and verification

Navigation: [documentation index](README.md) · [regression baseline](migration/regression-baseline.md)
· [validation log](migration/validation.md).

Status: section 1 is **current**; sections 2–6 are **proposed** and are created
by the milestones noted (the regression baseline layer and `quality.yml` exist
since M1).

## 1. Current checks

| Check | Command | Notes |
| --- | --- | --- |
| Smoke test | `pixi run smoke` (`--keep` to inspect outputs; pass `.gepro` paths to limit) | Opens each sample, runs diagnostics, PF, both SC, rules check, exports JSON/report/drawing. Needs a display (`xvfb-run` on Linux) |
| Regression baseline | `xvfb-run -a pixi run -e test test` | Captures every sample and coverage project with the legacy code and compares with `tests/baseline/` ([regression baseline](migration/regression-baseline.md#7-implementation-current-m1)); about 4 minutes |
| CI | `.github/workflows/quality.yml` | Linux: smoke + baseline under `xvfb-run`; Windows: smoke |
| Manual UI | `pixi run start [file.gepro]` | Exercise the change by hand |
| Calculation changes | Compare before/after on `sample_files/` | State what moved and why |

## 2. Test layers (proposed)

| Layer | Tool | Location | Created in |
| --- | --- | --- | --- |
| Regression baseline | pytest | `tests/test_baseline.py`, `tests/baseline/` | M1 |
| Engine unit tests | pytest | `tests/engine/` | M2 |
| Expression evaluator and security | pytest | `tests/engine/test_expressions.py`, `tests/security/` | M3 |
| Services (commands, undo, revisions, jobs, sessions) | pytest | `tests/services/` | M4 |
| Protocol (spawned backend) | pytest | `tests/protocol/` | M4 |
| MCP (SDK client) | pytest | `tests/mcp/` | M13 |
| Frontend units/components | Vitest | `modern/src/**/*.spec.ts`, `packages/engineering-ui/tests/` | M6 |
| Component stories, a11y, interactions | Storybook + Vitest addon | `packages/engineering-ui/stories/` | M6 |
| Browser workflows against the real backend | Playwright | `modern/e2e/` | M9 |
| Drawing/report visual parity | pytest + raster diff | `tests/visual/` | M2, M12 |
| Packaged application | scripted checks on clean machines | `tools/packaged_smoke.*` | M5, M14 |

## 3. What to run for a change

| Change | Required checks |
| --- | --- |
| Engine (`gelectrical/`) | Engine unit tests, regression baseline, smoke test while GTK exists |
| Services / protocol | Service and protocol tests, baseline subset through services |
| MCP | MCP tests, service tests |
| EngineeringUI | Vitest, Storybook build and test run, boundary check |
| App frontend | Type check, Vitest, affected Playwright workflows |
| Rust shell | `cargo fmt --check`, `cargo clippy -- -D warnings`, `cargo test`, protocol tests with sidecar |
| Packaging | Packaged smoke on the affected OS |
| Docs only | Link check, `git diff --check`; Sphinx build if user manual pages change |

## 4. Required test topics

- Sample project loading and save/load round trips (canonical equality).
- Network topology equivalence (node sets, references, upstream/downstream).
- Power flow, time-series, short-circuit, voltage drop results within tolerance.
- Protection and damage curves (evaluated points and polygons).
- Rules check outcomes.
- Element property validation and derived field state for every registered element.
- Undo/redo sequences with legacy labels and granularity.
- Report and drawing generation (content and visual parity).
- Backward compatibility (legacy files, modern-saved files in legacy loader).
- MCP operations, permissions, previews, batch atomicity and desktop synchronization.
- Frontend interactions (keyboard, selection, editing, dialogs, themes).
- Cross-platform packaging and process cleanup.

Numerical tolerances are defined once in the
[regression baseline](migration/regression-baseline.md#3-tolerances).

## 5. Principles

- Test against real backend operations where practical; mock only the native
  transport (Tauri) in browser tests (GEstimator `workspaceHarness.ts` pattern).
- Never weaken a check, widen a tolerance or regenerate a baseline to make a
  change pass; explain differences instead.
- Native Tauri features (file association, single instance, installers,
  sidecar lifecycle) are tested separately from browser tests and recorded as
  manual or packaged checks.
- Use local open-source tools only (no hosted visual-diff service).

## 6. CI (proposed)

- `quality.yml` on pull requests: pixi install; pytest (all Python layers);
  smoke test under `xvfb-run` while GTK exists; `npm ci`; type check; Vitest;
  Storybook test run; Playwright (Chromium and WebKit) against the real backend;
  Rust checks; dependency boundary and licence checks; static check forbidding
  `eval`/`exec`/`pickle.loads` in engine and backend code.
- `release.yml` on tags: per-OS sidecar and Tauri bundles, packaged smoke where
  runners allow, artefact upload.
- Record results of local and hosted runs in the [validation log](migration/validation.md).
