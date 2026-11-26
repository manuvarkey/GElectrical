# Validation log

Append-only record of checks that were actually run. Each entry states the
date, branch/commit, what was checked, the result and what was **not** checked.
Navigation: [migration index](README.md) · [testing guide](../testing.md).

## 2026-11-26 — Phase 1 planning (branch `docs/modernisation-phase1-plan`)

- Scope: documentation only. No Python, Rust or TypeScript code changed.
- Evidence gathered by static inspection of `master` at `8b630f6`:
  module imports and GUI coupling, element registry, `.gepro` structure of all
  three sample projects (members, element codes, field sizes), use of `eval()`
  and `pickle`, rules list, database formats.
- Reference repositories inspected locally: GEstimator (`b352ad77`) and
  Open Planner Studio (`ceeeaf382`).
- **Not run:** `pixi run smoke` and any runtime import test. pixi and the
  `.pixi` environment were not available in the planning session, and the
  ignored legacy `pvenv/` contains pandapower 2.14, which does not match the
  pinned 3.x environment. Runtime claims in the audit are therefore based on
  code reading; M1 must confirm them.
- Documentation checks: a local script resolved every relative link and
  heading anchor in the new developer documents (no failures; the only
  unresolved links are pre-existing MyST label references in the user manual,
  which Sphinx resolves). `git diff --check` clean. `docs/conf.py` parses.
  **Sphinx build not run** (Sphinx not installed in the session); the new
  `exclude_patterns` entries should be confirmed on the next Read the Docs build.

## 2026-11-26 — Owner review of Phase 1 decisions

- Owner approved Q1–Q9 and Q11–Q14 as recommended; Q10: EngineeringUI MIT;
  Q15: newest Python with Numba and latest pandapower; R6: use the WeasyPrint
  Windows executable. Follow-up answers: pandapower via pixi PyPI dependency,
  upgrade as M1b after the baseline, one WeasyPrint version everywhere, npm
  name `@kavilgroup/engineering-ui`. Recorded in risks-and-decisions §2 and
  ADRs 0009, 0010, 0012–0016.
- Version facts checked on 2026-11-26 from PyPI, anaconda.org and GitHub APIs:
  pandapower 3.5.6 on PyPI (Python 3.10–3.14), 3.2.1 newest on conda-forge;
  numba 0.68.1 / llvmlite 0.50.0 (Python 3.10–3.15, conda-forge builds to 3.15);
  PyInstaller 6.22.3 conda-forge builds to Python 3.14; pygobject, pycairo,
  shapely, pydantic-core conda-forge builds to 3.15; WeasyPrint 70.0 on PyPI
  with `weasyprint-windows-onedir.zip` release asset, 69.0 on conda-forge;
  osifont README states GPL-3.0 with font exception.
- `pixi.lock` currently pins Python 3.12.16, pandapower 3.2.1, numba 0.68.1,
  WeasyPrint 69.0 (read from the lock file).
- Authorship check for MIT relicensing: all commits touching GEstimator
  `modern/src` have the owner as author (AI co-author trailers only).
- **Not run:** environment solve for Python 3.14 (pixi unavailable in session);
  this is M1b work.
- Owner accepted ADRs 0008 and 0011; accepted 0003, 0004 and 0006 in
  direction, with details finalised by M4, M7 and M8 respectively.

## 2026-11-26 — M1 regression baseline (branch `feat/m1-regression-baseline`)

- Environment: pixi `default`/`test` environments (same solve group; `test`
  adds pytest 9.2.0), Python 3.12.16, pandapower 3.2.1, NumPy 2.2.6,
  SciPy 1.13.1, pandas 2.3.3, Shapely 2.2.0, NetworkX 3.7, Numba 0.68.1,
  WeasyPrint 69.0, GTK 3.24.52; Linux x86_64 under `xvfb-run`. The default
  environment's package set is unchanged (lock diff: pytest and its
  dependencies added; pixi 0.85.0 rewrote `__unix=0=0` as `__unix=0`).
- Engine code: unchanged (`git diff -- gelectrical` empty). The harness only
  calls legacy methods; it isolates XDG directories, theme and locale, and
  restores the module-level defaults aliased by D4 before every window.
- Projects: 3 samples, 8 coverage projects and 6 edge projects (17) built by
  `tools/baseline/build_projects.py`. Drawings of the coverage projects were
  reviewed as rendered PNGs (not in the interactive GTK app).
- `xvfb-run -a pixi run -e test test`: **38 passed** (fresh capture, 3 min 42 s).
- Determinism: captures with `PYTHONHASHSEED=0` and `=1` are **byte-identical**
  (`diff -r` empty, including PNG drawings); `compare.py`: 17/17 identical.
- Comparator sensitivity: a `vm_pu` change of 5e-9 passes, 2e-8 fails
  (tolerance 1e-8).
- `pixi run -e test smoke` under `xvfb-run`: 3/3 passed.
- D8 round trip: values change on load for older files —
  `sample.gepro` 97 changed / 144 added / 69 removed fields,
  `kerala_inspectorate_sample.gepro` 4 / 26 / 2, `voltage_test.gepro`
  0 / 45 / 1. Files saved by the current code: 0 changes. Save → load
  reproduces the loaded canonical model exactly for all 17 projects.
- New defects recorded in the audit: D16 (undo of deleting element 0 moves
  it to the end), D17 (pandapower 3.2.1 failures for impedance, xward,
  trafo3w LG SC and 3-phase PF with generator), D18 (report export
  `KeyError` for static generators / missing load profiles). D7 and D8
  confirmed. Audit corrected: `element_async_motor` is not registered
  (32 registry codes); the smoke test window is shown (`show_all()`).
- Feature inventory: not changed (no row status is affected by M1 evidence).
- **Not run:** the GitHub Actions workflow `quality.yml` (no push in this
  session; first hosted run pending), Windows smoke test, macOS, Sphinx
  build (no user-manual pages changed), interactive review of the coverage
  projects in the GTK app. PNG comparison in CI will be skipped if the runner
  resolves different fonts (`osifont` is installed locally).

## 2026-11-26 — M1 first CI run (PR manuvarkey/GElectrical#27)

- Run 45856511403 at `dfe63cf`: Windows smoke **passed**; Linux smoke
  **passed**; Linux regression baseline **failed** in 11 of 17 projects, only
  in `undo.json`. Cause: undo snapshots used a bit-exact SHA-256 of the
  storage model and stored float values without tolerance; protection curve
  points differ by ~1e-14 between the runner and the capture machine. All
  other artefacts matched within the documented tolerances. Drawing PNGs
  were skipped as designed (runner resolves DejaVu fonts, baseline osifont /
  Noto Sans Mono).
- Fix (harness only): tolerance-aware undo snapshot summaries, difference
  paths without values, float-free structure descriptions in `d8.json`,
  line-number-free tracebacks in `status.json`. Re-captured: only
  `undo.json` (17), `status.json` (27) and `sample__sample/d8.json`
  changed; no numerical artefact changed. Local `xvfb-run -a pixi run -e
  test test`: 38 passed.
- Hosted re-run 45859730391 at `7c10cfb`: Linux smoke + regression baseline
  **passed** (5 min 14 s; drawing PNG comparison skipped, fonts differ),
  Windows smoke **passed** (2 min 20 s).

## 2026-11-26 — M1b Python 3.14 and pandapower 3.5.6 (branch `feat/m1b-python-pandapower-upgrade`)

Status: **difference report awaiting owner approval. Baseline not regenerated.**

- Environment change (`pixi.toml`, `pixi.lock`): Python 3.12.16 → 3.14.10,
  pandapower 3.2.1 (conda-forge) → 3.5.6 (PyPI via `[pypi-dependencies]`),
  WeasyPrint 69.0 (conda-forge) → 70.0 (PyPI, the release that ships
  `weasyprint-windows-onedir.zip`), NumPy 2.2.6 → 2.4.6, SciPy 1.13.1 →
  1.18.1. Unchanged: pandas 2.3.3, Numba 0.68.1, Shapely 2.2.0, NetworkX 3.7,
  matplotlib 3.11.2, GTK 3.24.52, PyGObject 3.58.1. Only pandapower and
  WeasyPrint come from PyPI; their dependencies (including Pango and the
  compiled Python packages) come from conda-forge, with pandapower's
  `numpy<2.5`, `pandas~=2.3` and other bounds mirrored in `pixi.toml` so the
  conda solve stays compatible. `pixi lock` solved win-64, linux-64, osx-64
  and osx-arm64 (both environments). Lock SHA-256 starts `a8c1eda3dd45d1c4`.
- Legacy pins (D11): `requirements.txt` regenerated from the dependency
  closure of the new environment (pandapower 3.5.6, WeasyPrint 70.0; pycairo
  and PyGObject stay system-provided as before); `setup.py` pins
  `pandapower==3.5.6`, `weasyprint==70.0` and `python_requires>=3.14,<3.15`.
- Numba: `pandapower.auxiliary._check_if_numba_is_installed()` is `True`,
  `net._options["numba"]` is `True` after `runpp` and `runpp_3ph`, no Numba
  fallback warning, and the JIT dispatchers `makeYbus_numba.gen_Ybus` and
  `create_jacobian_numba.create_J2` hold compiled signatures after a run.

### Compatibility fixes (no change of engineering intent)

| Change | Cause | Evidence |
| --- | --- | --- |
| `elementmodel/transformer.py`: pass `mag0_percent = field × 100` | pandapower 3.4.0 "`mag0_percent` is treated as a percent instead of ratio"; 3.2.1 used the value as the ratio Zm0/Z0. The GElectrical field is the ratio (`Zm0/Z0`, default 10) | Same pandapower net (dumped with 3.2.1) solved with 3.5.6 changed `res_bus_3ph` by up to 7e-5 pu; the only differing matrix entry was the zero-sequence magnetising shunt of the Dyn transformer (`BR_G_ASYM`/`BR_B_ASYM`). After the fix every `res_*_3ph` table and every 3-phase result field equals the baseline within tolerance |
| `elementmodel/generator.py` (`StaticGenerator`) and the diversity balancing sgen in `model/pandapower.py`: pass `type='wye'` | `create_sgen` default `type` changed from `'wye'` to `None`; 3-phase power flow ignores sgens whose type is neither wye nor delta | `cov_static_generation` 3-phase voltages moved by 5.8e-7 pu; equal to baseline after the fix |
| `model/pandapower.py`: `bus.vn_kv.at[i] = …` → `bus.at[i, 'vn_kv'] = …` (4 lines) | Chained assignment. Works on pandas 2.3 but emits `ChainedAssignmentError` (96 warnings in the M1 baseline) and stops working under pandas 3 copy-on-write. Python 3.14 no longer shows the warning | `pp_input.json` bus tables unchanged; warning gone |

### Difference report (final capture vs M1 baseline)

`baseline-capture --out <scratch>` then `compare.py`, with diff limits lifted:
6,760 differences in 17/17 projects. Every difference is in one of the rows
below. Unchanged in all 17 projects: `model.json`, `roundtrip.json`,
`topology.json`, `curves.json`, `d8.json`, `diagnostics.json`, `renumber.json`,
`undo.json`, `drawing_*.png` (compared, fonts match), balanced power flow
(all `pf_bal`, `pfdiv_bal`, `ts_bal` result tables), all `res_*_3ph` tables,
maximum short-circuit values, rules-check results (except the new
`cov_generation` 3-phase runs) and every result field other than those below.

| # | Artefacts | Old → new | Cause |
| --- | --- | --- | --- |
| 1 | Minimum short-circuit values: `ikss_ka_3ph_min`, `ikss_ka_1ph_min`, `zk_ohm_min`, `zk_ohm_1ph_min` (`results.json`, `node_results.json`, 5 lines of `report.txt` per affected project), `sc.json` (`res_bus_sc` of the `min` case: `ikss_ka`, `ip_ka`, `skss_mw`, `rk_ohm`, `xk_ohm`, `rk0_ohm`, `xk0_ohm`) | See table below; −0.1 % to −3.0 % in projects with a transformer | pandapower 3.5.6 applies the IEC 60909-0:2016 transformer correction factor K_T only in the `max` case (§6.3.3); 3.2.1 also applied it in the `min` case. Verified: with the 3.2.1 behaviour patched back into the installed pandapower (temporarily, then restored and checked byte-identical), all of these differences vanished except row 2 |
| 2 | Same fields, `edge__unusual_values` only (`lv_tol_percent = 10`) | 3-phase min −5.26 % (e.g. 4.2633 → 4.0389 kA); 1-phase min +0.02 % | pandapower now uses c_min = 0.90 for low-voltage networks with 10 % tolerance (IEC 60909-0:2016 Table 1); 3.2.1 used 0.95. The 1-phase minimum is computed by GElectrical with its own c factor, so only the K_T change applies; K_T > 1 for c_max = 1.1, so removing it lowers the impedance |
| 3 | `cov_generation` `pf_3ph`, `pfdiv_3ph`, `ts_3ph` | Previously `KeyError: 'res_gen_3ph'` (D17); now the chain completes, but power flow emits `MatrixRankWarning: Matrix is exactly singular` and every 3-phase bus, generator and grid result is `NaN` | pandapower 3.5.0 "gen for 3ph load flow" fix. The network has a generator and the grid on the same bus (pandapower diagnostic warns). New files: `pf.json`, `results.json`, `node_results.json`, `rules.json`, `sc.json` in those three modes. **Owner decision needed:** the legacy app now shows `NaN` results instead of failing |
| 4 | `pf.json` `res_bus`, `res_line`, `res_trafo`, `res_ext_grid`, `res_load`, `res_sgen` in 3-phase modes (1,599 values) | 3.2.1 left placeholder values after `runpp_3ph` (`vm_pu` 1.0, line flows 0); 3.5.6 fills them from the 3-phase solution | pandapower result extraction. Not used by GElectrical in 3-phase mode (it reads `res_*_3ph`); no result field changed |
| 5 | `pp_input.json`, `pf.json` `inputs_after_run`: `asymmetric_load`, `asymmetric_sgen` | New columns `sn_a_mva`, `sn_b_mva`, `sn_c_mva` (NaN) | pandapower 3.3.0 per-phase rating columns; not set by GElectrical, not used in calculation |
| 6 | `pf.json` `inputs_after_run/trafo/*/mag0_percent` (3-phase modes) | 10 → 1000 | Compatibility fix above (same physical value) |
| 7 | `status.json` `warnings` (111 files) | Diagnostic log lines now come from `pandapower.diagnostic.diagnostic_helpers` at WARNING level (720 lines; was 12 from `pandapower.diagnostic`); `ChainedAssignmentError` warnings gone; `cov_generation` 3-phase: `MatrixRankWarning`, extra `RuntimeWarning` | pandapower 3.3 diagnostic restructuring; chained-assignment fix above; row 3 |

Minimum short-circuit changes in `pf_bal` node results (largest change per
project and field; projects not listed have no change):

| Project | Field | Nodes | Largest: old → new (kA) | Range |
| --- | --- | --- | --- | --- |
| `cov_multisheet` | 3-phase min | 12 | 7.1518 → 6.9582 (−2.71 %) | −2.71 … −0.20 % |
| `cov_multisheet` | 1-phase min | 12 | 0.02275 → 0.02275 (−0.001 %) | ≈ 0 % |
| `cov_radial_lv` | 3-phase min | 13 | 12.7805 → 12.4117 (−2.89 %) | −2.89 … −0.09 % |
| `cov_radial_lv` | 1-phase min | 13 | 13.5024 → 13.1054 (−2.94 %) | −2.94 … −0.10 % |
| `edge__unusual_values` | 3-phase min | 5 | 0.2447 → 0.2318 (−5.26 %) | −5.26 … −5.24 % |
| `edge__unusual_values` | 1-phase min | 5 | 4.5299 → 4.5309 (+0.02 %) | 0 … +0.02 % |
| `sample__kerala_inspectorate_sample` | 3-phase min | 3 | 9.9016 → 9.6122 (−2.92 %) | −2.92 … −1.18 % |
| `sample__kerala_inspectorate_sample` | 1-phase min | 3 | 10.0807 → 9.7808 (−2.98 %) | −2.98 … −0.08 % |
| `sample__sample` | 3-phase min | 11 | 15.8733 → 15.4964 (−2.37 %) | −2.37 … −0.12 % |
| `sample__sample` | 1-phase min | 11 | 16.8138 → 16.3910 (−2.51 %) | −2.51 … −0.01 % |

The same changes appear in every analysis mode of these projects (short
circuit does not depend on the power-flow mode).

### Checks run

- `xvfb-run -a pixi run smoke`: 3/3 passed (Python 3.14, WeasyPrint 70.0 PDF
  export included).
- Full baseline capture: 17/17 projects captured; report PDF generated in
  the same projects as the baseline (D18 failures unchanged).
- `GELECTRICAL_BASELINE_CAPTURE=<final capture> pixi run -e test test`:
  21 passed, 17 failed (every project differs from the M1 baseline as listed
  above; expected until the approved re-baseline).
- Bisection used a scratch copy of the M1 environment (`pixi install --frozen`
  from the `master` lock): the same pandapower JSON net solved with 3.2.1 and
  3.5.6, and the sequence admittance matrices compared.
- `git diff --check` clean.

### Not run / open

- Windows and macOS: lock solved, but smoke test not run (Windows CI job runs
  on push). Hosted CI not run (no push).
- Interactive GTK session on Python 3.14 (`pixi run start`) not exercised by
  hand; only the windows built by the smoke test and the capture.
- Flatpak manifest (`com.kavilgroup.gelectrical.json`) still builds
  pandapower 2.14.9 and WeasyPrint 62.3 on the GNOME 46 runtime (Python 3.11),
  and Snap (core22, Python 3.10) installs `requirements.txt`, which now needs
  Python ≥ 3.11 (NumPy 2.4). With the `mag0_percent` fix a pandapower < 3.4
  build would model the zero-sequence magnetising impedance 100 times too
  large. These packages need updating before their next release (M14).
- Next step after approval: regenerate `tests/baseline/` with an
  `environment.json` that references this entry (implementation plan M1b
  step 4).

## 2026-11-26 — M1b re-baseline (branch `feat/m1b-python-pandapower-upgrade`)

- Owner approved the M1b difference report above ("Approve, re-baseline").
  The handling of `NaN` 3-phase results for `cov_generation` (row 3) was not
  decided; the baseline records the current behaviour.
- `tools/baseline/capture.py` gained `--reason`, stored as `baseline_reason`
  in `environment.json`. Command:
  `xvfb-run -a pixi run -e test baseline-capture --reason "M1b: … see docs/migration/validation.md (2026-11-26 M1b entry)"`.
- New `tests/baseline/`: 17/17 projects; 356 files modified, 15 added (the
  `cov_generation` 3-phase result files). Identical to the capture analysed
  in the difference report (`diff -rq`: only `environment.json` differs, by
  `baseline_reason`).
- `xvfb-run -a pixi run -e test test`: **38 passed** (fresh capture, 4 min 5 s).
- `xvfb-run -a pixi run smoke`: 3/3 passed (run before the re-baseline;
  engine code unchanged since).
- **Not run:** Windows/macOS smoke, hosted CI (no push).

## 2026-11-26 — M6 frontend foundation (branch `feat/m6-frontend-foundation`)

Status: **implemented with mock data; acceptance criteria met locally**
(owner review pending; hosted CI not run).

- npm workspaces at the root (`modern`, `packages/*`), Node 24.21.0, npm
  11.19.0. Exact pins (`.npmrc` `save-exact=true`): Vue 3.5.46, Quasar 2.36.0,
  `@quasar/vite-plugin` 2.0.2, Vite 8.4.0, `@vitejs/plugin-vue` 6.0.11,
  TypeScript 6.0.3, vue-tsc 3.3.14, Vitest 5.1.2 (`@vitest/browser`,
  `@vitest/browser-playwright`), Playwright 1.65.0 (root `overrides`),
  Storybook 10.6.9 (`@storybook/vue3-vite`, `addon-a11y`, `addon-vitest`,
  `addon-docs`), `@vue/test-utils` 2.6.0, happy-dom 21.0.4, Prettier 3.10.1,
  `@types/node` 24.19.4. TypeScript 7.0.2 is newer but `vue-tsc` needs the
  JavaScript compiler API ([ADR 0017](../decisions/0017-frontend-workspace-build.md)).
- `packages/engineering-ui` (`@kavilgroup/engineering-ui` 0.1.0, MIT, private):
  tokens and Quasar bridge (light/dark/system via `data-theme` and Quasar
  `Dark`), `EuiIcon` (64 glyphs including `blank`, 10 electrical), `EuiRibbon`,
  `EuiDocumentRail`, `EuiWorkspace` (keyboard splitters), `EuiStatusBar`,
  `EuiNotifications` (+ `createNotificationQueue`), `EuiDialog` (QDialog),
  `EuiNumberInput` (QInput, unit, display precision, raw editing, host
  errors), `EuiPropertyInspector` (FieldSchema shape of backend §8: `int`,
  `float`, `str`, `multiline_str`, `bool`, `graph`/`data`/`font`, `heading`,
  `selection_list`, `enabled`, `editable`, mixed values, filter).
- GEstimator code adapted at `e4e4fb295899feda5253ba216613c70c1f256d4e`
  (AppIcon, theme.css, appearance.ts, RibbonToolbar, DocumentRail,
  documents.ts helpers, statusNotice.ts, PersistentDialog, ribbon/rail rules of
  style.css), PrimeVue replaced by Quasar or plain elements; MIT header and
  provenance line in each file, rows in the package README. The adapted files
  were unmodified in the GEstimator working tree at that commit.
- `modern/`: Vite + Vue 3 + strict TypeScript + Quasar via
  `@quasar/vite-plugin`; shell (ribbon, rail, palette, schematic placeholder,
  inspector, messages, status bar, notifications, settings dialog) with mock
  data only; no backend calls.
- Tooling: Prettier (root config, workspaces only), `vue-tsc`,
  `tools/check_boundaries.mjs` (+ tests), `tools/check_licences.mjs` (+ tests),
  CI job `frontend` in `quality.yml`. ESLint (optional in the plan) not added.

### Checks run (local, Linux)

- `npm run check`: Prettier clean; boundary check passed (63 files);
  licence check passed; tool tests 5/5; `vue-tsc` clean in both workspaces;
  EngineeringUI Vitest **121 passed** (unit project 60 tests in 12 files;
  storybook project 61 stories in 10 files, Chromium headless through
  Playwright); `modern` Vitest 3 passed; library build and app build passed.
- `npm run build-storybook`: passed (61 stories, 10 docs pages).
- Accessibility: `parameters.a11y.test = "error"` fails a story on **any**
  axe violation (stricter than "no serious violations"); all 61 stories pass,
  including the Dark variants (a play function asserts the dark tokens are
  applied before axe runs). Issues found and fixed during M6: rail tiles
  (`label-content-name-mismatch`), notification `role="alert"` on `li`
  (`list`, `aria-allowed-role`). axe 4.14 on the running shell: 0 violations
  in light and dark after moving splitters into panel landmarks and adding a
  header landmark and `h1`.
- Keyboard (play functions): ribbon tabs (arrows, Home/End, automatic
  activation), ribbon toolbar (roving focus, disabled commands skipped,
  Enter), document rail (arrows, Enter, Delete, End, add tile with Space),
  workspace splitters (arrows, Shift, Home), number input (Enter commits,
  Escape reverts, expressions passed as text), inspector (Tab order, Enter,
  Escape, Space on check box, edit button), dialog (focus moves in, Enter
  applies, Escape cancels). Real keyboard in the in-app Chromium: Escape
  closes the settings dialog and focus returns to the Settings command.
- Themes: light and dark checked by hand in the shell (screenshots in the
  session) and by the Dark stories; `system` follows `prefers-color-scheme`
  (unit test with a mocked media query).
- Standalone package: `npm run build -w @kavilgroup/engineering-ui` builds
  `dist/` (ES modules per subpath, `engineering-ui.css`, declarations under
  `dist/types`); every `exports` target exists; the output imports Quasar only
  from `quasar` and only in `controls`, `dialogs`, `inspectors`.
- Licences (`npm run check:licences`, 356 installed packages): runtime
  closure (Vue, Quasar and Vue's compiler dependencies) MIT, ISC,
  BSD-2-Clause, BSD-3-Clause, Apache-2.0; development-only MPL-2.0
  (axe-core, lightningcss), BlueOak-1.0.0, 0BSD, (MIT OR CC0-1.0); no
  unknown or GPL/LGPL licences.
- Storybook MCP for Vue (optional): evaluated from the `@storybook/addon-mcp`
  10.6.9 package (MIT). It supports `vue3`; documentation tools need the
  experimental docgen server on `@storybook/vue3-vite`. Not adopted; outcome
  recorded in [EngineeringUI §7](../architecture/engineering-ui.md#7-storybook).
  The addon was not run.
- `npm audit`: 5 moderate findings, all in `js-beautify` → `editorconfig`,
  `glob`, `minimatch`, pulled in by `@vue/test-utils` 2.6.0 (development
  only). The suggested fix downgrades `@vue/test-utils` to 2.4.11; not
  applied.

### Not run / open

- Tauri dev window (plan deliverable): not created; `src-tauri` arrives with
  the M5 sidecar PoC and the M9 vertical slice. The shell runs in the browser
  only.
- Hosted CI (no push); Windows and macOS; WebKit and Firefox story runs.
- Visual regression screenshots (no tool chosen yet).
- `selection_images` in the inspector are accepted but not rendered.
- The Storybook test run needs the Playwright browser once
  (`npx playwright install chromium-headless-shell`); locally the cached
  revision for Playwright 1.65.0 was used.

## 2026-11-27 — M2 headless engine extraction (branch `feat/m2-milestone`)

Status: **implemented; acceptance met except one owner decision** (raster
limit for headless drawings with Cairo text, below). Owner review pending.

- Environment: unchanged from M1b (Python 3.14.10, pandapower 3.5.6,
  WeasyPrint 70.0, GTK 3.24.52; `pixi.lock` not modified, only tasks added to
  `pixi.toml`). Linux x86_64; `osifont` installed system-wide.
- Structure ([ADR 0014](../decisions/0014-legacy-gtk-location.md),
  [ADR 0018](../decisions/0018-headless-engine-split.md)): `MainApp`/`MainWindow`,
  `view/`, `interface/` moved to `gelectrical/gtk/`; `misc.py` split into
  `core/` (constants, style, fields, paths, undoable, geometry, interpolation),
  `symbols/`, `reports/` and `gtk/widgets.py`, with `misc.py` kept as a
  GTK-only re-export; `elementmodel/registry.py` (D14); element rendering moved
  to `symbols/` behind `update_symbol()`/`symbol_active()`/`get_symbol_layers()`;
  `cairo.Region` replaced by `core/geometry.py`; headless `ProjectModel` with
  event notifications and `GtkProjectModel` (views, dialogs) in the GTK UI;
  `analysis/pipeline.py`, `persistence/gepro.py`, `reports/export.py`,
  `reports/graph.py` (Matplotlib without GUI backend); D4 and D15 fixed;
  `tools/headless_run.py` (`pixi run headless`).
- Engine code that computes results (`model/pandapower.py`, `networkmodel.py`
  logic, `protection.py`, `rulescheck.py`, element power models and field side
  effects) is unchanged apart from imports.

### Acceptance criteria

| Criterion | Result |
| --- | --- |
| `python -c "import sys; sys.modules['gi'] = None; import gelectrical.model.project, gelectrical.analysis.pipeline, gelectrical.persistence.gepro, gelectrical.reports"` | **Passes** (`tests/engine/test_headless_import.py`; a second test checks that no `gi`, `gelectrical.gtk` or `gelectrical.misc` module is loaded by the engine) |
| Headless pipeline on all baseline projects matches the baseline within tolerance | **Passes** for every JSON and text artefact of all 17 projects (model, round trip, D8, curves, topology, pandapower inputs, diagnostics, all 6 analysis modes, results, node results, rules, renumbering, undo, report text) with the documented tolerances. `capture.py --headless`, PyGObject blocked, no display. Expected difference handled without widening tolerances: one `PyGTKDeprecationWarning` (emitted by `Gtk.Label` in the GTK tab code) is absent from the headless `status.json` files |
| Drawing PDF visual diff within threshold | **Open (owner decision).** Headless drawings with PangoCairo text (`GELECTRICAL_TEXT_BACKEND=pango`, no GTK): **25/25 rasters pixel-identical** (0.0000 %) to the baseline, so geometry and stroke rendering are unchanged. With the headless default (Cairo toy text API) the rasters differ by **0.12–0.61 %** of pixels (all 25 above the 0.1 % limit) because glyph rendering differs (kerning, synthetic bold). No raster limit was widened; `tests/test_headless_baseline.py` reports the difference as a warning and checks rasters only for Pango-text captures. Owner to choose: accept a separate raster limit for Cairo text, or use PangoCairo in the sidecar (decision rule option 2) |
| Report generated | **Yes**: headless `report.html`/`report.pdf` in every project where the legacy capture produced one (D18 failures unchanged); `report.txt` identical |
| Legacy GTK app passes the smoke test and a manual check list | Smoke **3/3**. Check list scripted under `xvfb-run` against the real `MainWindow` (open, new tab, notebook switching, undo/redo of tabs, remove/reorder sheets, tab labels, palette insert with rotation, click selection, port hit test, field edit and undo, analysis, rules check into the messages view, diagnostic selection marking, save and reopen, drawing export, renumber and undo, protection coordination warning): **24/24**. Not exercised interactively by hand |

### Text metrics decision (backend.md, step 4)

Cairo toy API extents vs PangoCairo extents on all 249 elements of the 17
baseline projects: largest difference **3 drawing units** (limit one grid
unit = 16) → option 1 (no `gi` in the sidecar) satisfies the decision rule
(`tests/test_symbols_extents.py`).

During the work the legacy capture found two regressions, both fixed before
the final runs: `sample__sample/drawing_1.png` differed by 0.126 % because
symbol extents were first measured at identity scale (assembly frames and
reference lines follow text width; rendering now measures on the output
context as before), and the motor symbols inherited the label update of
`Load` (`Motor3ph`/`Motor1ph` now keep their own text). After the fixes every
legacy raster is pixel-identical.

### Checks run (local, Linux)

- `xvfb-run -a pixi run -e test test` (final code): **111 passed** in
  6 min 33 s: legacy baseline 38 (fresh GTK capture; all 25 drawing rasters
  0.000000 % different), headless baseline 18 (rasters reported, not checked:
  0.12–0.61 %), engine unit tests 55 (`tests/engine`, `gi` blocked:
  fields, registry vs the baseline's 31 registered codes, geometry vs
  `cairo.Region` on 20 000 random cases, symbols, persistence round trip on
  3 samples and 8 coverage projects, pipeline, exports, headless import;
  `tests/test_symbols_extents.py`).
- Pure geometry fuzz against `cairo.Region`: 100 000 random cases (including
  empty and negative rectangles), 0 mismatches.
- Full headless capture with PangoCairo text: rasters 25/25 at 0.0000 %; all
  other artefacts as above.
- `xvfb-run -a pixi run smoke`: **3/3** (after every step and on the final code).
- `pixi run headless sample_files/sample.gepro`: analysis completed (time
  series, 3-phase from the file settings), 1 diagnostic warning, rules check
  9 warnings / 12 info, `network.json`, `report.html`, `report.pdf`,
  `drawing.pdf` written; no display.
- `git diff --check` clean.

### Not run / open

- Owner decision on headless raster limit (above).
- Interactive GTK session by hand (`pixi run start`); Windows/macOS; hosted CI
  (workflow extended: headless run without display, headless baseline in the
  Linux test job, engine tests and headless run on Windows).
- Sphinx build (no user-manual pages changed).
- Packaging builds (PyInstaller/Flatpak/Snap) with the new package layout:
  manifests updated (`setup.py` uses `find_packages`, Glade path), not built.
- `osifont` is still not bundled with the package (both text backends use the
  system font configuration).
