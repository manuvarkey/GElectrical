# Risks, owner decisions and prototype requirements

Status: **living document**. Navigation: [migration index](README.md) ·
[decisions](../decisions/README.md) · [implementation plan](implementation-plan.md).

## 1. Risk register

Likelihood/impact: H, M, L.

| ID | Risk | L | I | Mitigation | Owner milestone |
| --- | --- | --- | --- | --- | --- |
| R1 | Refactor silently changes engineering results | M | H | Capture baseline first (M1); compare after every PR; ADR for intended changes | M1–M15 |
| R2 | Element geometry depends on Pango text extents; headless metrics differ | M | M | Measure extents per element; extents do not affect connectivity; PNG diff for PDF | M2 |
| R3 | Safe evaluator rejects an expression used in user projects | M | M | Inventory all bundled expressions; report unsupported expressions with element and field; never execute | M3 |
| R4 | maxGraph connection model conflicts with coordinate connectivity | M | H | PoC with explicit criteria; custom SVG fallback | M7 |
| R5 | Sidecar size/start time unacceptable (scientific stack, Numba JIT) | M | H | Early PoC; onedir or packed env; lazy imports; background warm-up | M5 |
| R6 | WeasyPrint native libraries fail in packaged Windows builds | L | H | Use the official WeasyPrint Windows executable on Windows ([ADR 0016](../decisions/0016-weasyprint-windows-executable.md)); packaged report test in CI | M5, M14 |
| R7 | Undo granularity differs from the legacy app | M | M | Action-to-command table with labels; undo sequence tests | M4, M10 |
| R8 | Analysis blocks the backend owner thread | M | M | Job runner on snapshot; worker process if needed | M4 |
| R9 | Two front ends (GTK, Tauri) drift during migration | H | M | Engine shared; GTK frozen to bug fixes after M2; retire at M15 | M2–M15 |
| R10 | Field-load order resets values (D8) | L | H | Round-trip artefact in baseline detects it; fix only by ADR | M1 |
| R11 | Quasar styling conflicts with EngineeringUI tokens and compact density | M | L | Bridge stylesheet; Storybook visual checks | M6 |
| R12 | EngineeringUI absorbs GElectrical-specific logic | M | M | Dependency boundary check in CI; review rule | M6+ |
| R13 | MCP writes surprise users | M | M | Off by default; read-only default access; tagging, highlighting, AI-changes panel; optional approval mode | M13 |
| R14 | Licence incompatibility in the distributed bundle | L | H | Licence inventory (below); GPL-3.0-or-later distribution (ADR 0013) | M5, M14 |
| R15 | pandapower API changes (3.x evolution); latest release not on conda-forge | M | M | Pin in pixi lock (PyPI via pixi); M1b upgrade with documented differences; isolate calls in `model/pandapower.py` | M1b, ongoing |
| R18 | Report differences between WeasyPrint executable (Windows) and Python package (other platforms) | L | M | Same pinned version; cross-platform report parity check | M5, M14 |
| R19 | Mixed conda-forge/PyPI resolution conflicts (pandapower pins `numpy<2.5`, `pandas~=2.3`) | M | M | pixi resolves both together; lock on all four platforms in CI | M1b |
| R16 | WebView differences (WebView2 vs WebKitGTK) affect SVG/canvas behaviour | M | M | Playwright on Chromium and WebKit; packaged checks on both OSes | M9, M14 |
| R17 | Scope creep into design features during migration | M | M | Design services are post-M15; roadmap discipline | all |

## 2. Owner decisions

Reviewed by the owner on 2026-11-26. "Accepted" means the recommendation was
approved; rows that depend on a PoC keep the stated decision rule.

| ID | Question | Decision | Record |
| --- | --- | --- | --- |
| Q1 | Undo implementation in services | Snapshot transactions | [ADR 0009](../decisions/0009-undo-transactions.md) Accepted |
| Q2 | Headless text metrics | Measure in M2; prefer Cairo/fontTools metrics without `gi` in the sidecar; use PangoCairo only if extents cannot match | [backend](../architecture/backend.md#headless-text-metrics) |
| Q3 | Sidecar format | PyInstaller onedir; packed conda environment as fallback | [ADR 0010](../decisions/0010-python-environment-and-sidecar.md) Accepted |
| Q4 | Schematic library | Decide by M7 selection criteria | [ADR 0005](../decisions/0005-schematic-library.md) (process accepted) |
| Q5 | Display nodes after analysis | Results overlay; not inserted into the document (feature E09 `Changed`, approved) | [backend](../architecture/backend.md#6-analysis-jobs) |
| Q6 | Multi-element drag move and "keep connections" | Parity first; enhancements after M15 or behind an option | [schematic editor](../architecture/schematic-editor.md#5-editing-behaviour-notes) |
| Q7 | Printing | Export PDF and open in the OS viewer (feature F02 `Changed`, approved) | [frontend](../architecture/frontend.md#7-native-integration) |
| Q8 | Curve definitions in project files | Keep embedded in element fields | [project format](../architecture/project-format.md) |
| Q9 | Licence statement | Align headers to GPL-3.0-or-later | [ADR 0013](../decisions/0013-licensing.md) Accepted |
| Q10 | EngineeringUI licence | **MIT** | [ADR 0012](../decisions/0012-engineering-ui-package.md) |
| Q11 | macOS distribution | Unsigned CI builds first; signing decided later | [packaging](../architecture/packaging.md#7-channels) |
| Q12 | Bundled schematic font | Bundle osifont (GPL-3.0 with font exception, redistribution and PDF embedding allowed) | [packaging](../architecture/packaging.md#4-native-and-runtime-dependencies) |
| Q13 | Legacy GTK retirement | `archive/gtk` branch at M15 | [ADR 0014](../decisions/0014-legacy-gtk-location.md) Accepted |
| Q14 | MCP approval mode | Tagging + highlight + undo first; staged approval later | [MCP](../architecture/mcp.md#4-permissions-and-review) |
| Q15 | Python version | **Python 3.14** (newest supported by both Numba and pandapower); latest pandapower | [ADR 0015](../decisions/0015-python-and-pandapower-versions.md) |
| Q16 | pandapower source (latest 3.5.6 is PyPI only; conda-forge has 3.2.1) | pixi `[pypi-dependencies]` for pandapower; compiled deps stay on conda-forge | [ADR 0015](../decisions/0015-python-and-pandapower-versions.md) |
| Q17 | Upgrade timing | New milestone M1b: after the baseline on the current environment, before the M2 refactor | [plan](implementation-plan.md#m1b--python-and-pandapower-upgrade) |
| Q18 | WeasyPrint on Windows | Official Windows onedir executable in packaged Windows builds; Python package elsewhere; one pinned version everywhere | [ADR 0016](../decisions/0016-weasyprint-windows-executable.md) |
| Q19 | EngineeringUI npm name | `@kavilgroup/engineering-ui` | [ADR 0012](../decisions/0012-engineering-ui-package.md) |

No owner decisions are open. New questions are added here with an ID.

## 3. Prototype requirements

| PoC | Milestone | Must demonstrate | Exit evidence |
| --- | --- | --- | --- |
| 1. Headless backend | M2 | Engine import without GTK; full pipeline and exports headless; baseline equality | CI job without display; baseline report |
| 2. Python sidecar packaging | M5 | Packaged backend on Windows and Linux runs analysis and reports; lifecycle cleanup | Measurement table; clean-machine notes |
| 3. EngineeringUI + Quasar | M6 | Token theme over Quasar, light/dark/system, compact density, shell components | Storybook build; screenshots |
| 4. Storybook | M6 | Stories with a11y and interaction tests running locally and in CI | CI log |
| 5. Schematic editing | M7 | Criteria table in the schematic editor document | ADR 0005 |
| 6. ECharts protection and load profiles | M8 | Capability table in the graphing document | ADR 0006 update |

## 4. Licence inventory (target stack)

Licences as published by the projects; re-verify versions when adding
dependencies (`npm ls --all --json` and `pixi list` in CI with a licence check).

| Component | Licence | GPL-3.0 compatible |
| --- | --- | --- |
| Tauri 2, Rust crates (`tauri`, plugins) | MIT / Apache-2.0 | Yes |
| Vue 3, Vite, Quasar 2 | MIT | Yes |
| TypeScript | Apache-2.0 | Yes |
| Storybook and addons | MIT | Yes |
| axe-core (Storybook a11y addon, development only) | MPL-2.0 | Yes (not distributed) |
| lightningcss (Vite CSS, development only) | MPL-2.0 | Yes (not distributed) |
| Tabulator | MIT | Yes |
| Apache ECharts | Apache-2.0 | Yes (GPL-3.0, not GPL-2.0-only) |
| maxGraph | Apache-2.0 | Yes |
| SVG.js | MIT | Yes |
| Vitest | MIT | Yes |
| Playwright | Apache-2.0 | Yes |
| MCP Python SDK (`mcp`) | MIT | Yes |
| uvicorn, starlette, anyio, httpx | BSD-3-Clause / MIT | Yes |
| pydantic | MIT | Yes |
| pandapower | BSD-3-Clause | Yes |
| NumPy, SciPy, pandas, NetworkX, Shapely, Numba, llvmlite | BSD-style | Yes |
| GEOS | LGPL-2.1 | Yes (dynamic linking) |
| Matplotlib | Matplotlib licence (PSF-style) | Yes |
| Jinja2 | BSD-3-Clause | Yes |
| Mako (until removed) | MIT | Yes |
| WeasyPrint | BSD-3-Clause | Yes |
| Pango, HarfBuzz, fontconfig, cairo | LGPL-2.1+/MIT/MPL-1.1 (cairo dual) | Yes |
| Pycairo | LGPL-2.1 / MPL-1.1 | Yes |
| openpyxl | MIT | Yes |
| PyInstaller | GPL-2.0-or-later with bootloader exception | Yes (exception allows any licence for bundled app) |
| pixi | BSD-3-Clause | Yes (tool) |
| osifont | GPL-3.0 with font exception | Yes (font exception allows PDF embedding) |
| WeasyPrint Windows executable | BSD-3-Clause plus bundled LGPL libraries | Yes (ship notices) |
| EngineeringUI (this repository) | MIT | Yes |
| Open Planner Studio | LGPL-3.0-or-later (reference only, no code copied) | n/a |
| GEstimator | GPL-3.0-or-later, same copyright holder | Yes |
| Penpot (optional tool), Inkscape (tool) | MPL-2.0, GPL | Tools only, not distributed |

The distributed application combines Apache-2.0 components with GPL code;
therefore the combined work is distributed under **GPL-3.0-or-later**, which
the current "GPL-2.0-or-later" headers permit ([ADR 0013](../decisions/0013-licensing.md)).
