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
