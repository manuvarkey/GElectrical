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
