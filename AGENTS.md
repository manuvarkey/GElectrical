# AGENTS.md

Guidance for AI coding agents working on GElectrical: an LV/MV electrical
network analysis desktop application with pandapower as the solver backend.

**Current implementation:** GTK3/PyGObject application (`gelectrical/`).
**In progress:** migration to Tauri 2 + Vue 3/TypeScript + Quasar with a
headless Python backend, an MCP server and the EngineeringUI library. Phase 1
(planning) is complete and was reviewed by the owner on 2026-11-26 (decisions in
[risks and decisions](docs/migration/risks-and-decisions.md#2-owner-decisions)).
Migration code so far: the M1 regression baseline, the M1b environment, the
M2 headless engine (`gelectrical/` importable without GTK; legacy UI in
`gelectrical/gtk/`) and the M6 frontend foundation (`modern/` shell with mock
data, `packages/engineering-ui/`); no application services or Tauri yet.
Do not start a migration milestone unless the user asks for it.

## Read first

1. [ARCHITECTURE.md](ARCHITECTURE.md): current vs proposed layers and structure.
2. [docs/README.md](docs/README.md): documentation index and task map.
3. [docs/development-guidelines.md](docs/development-guidelines.md) and
   [docs/testing.md](docs/testing.md).

| Task | Also read |
| --- | --- |
| Engine: elements, calculations, connectivity, pandapower | [backend](docs/architecture/backend.md), [regression baseline](docs/migration/regression-baseline.md), [audit](docs/migration/existing-application-audit.md) |
| `.gepro` load/save, stored data | [project format](docs/architecture/project-format.md) |
| Services, commands, undo, protocol | [backend](docs/architecture/backend.md), [decisions](docs/decisions/README.md) |
| Vue app | [frontend](docs/architecture/frontend.md), [UI guidelines](docs/ui-guidelines.md) |
| Reusable components | [EngineeringUI](docs/architecture/engineering-ui.md), [packages/engineering-ui/AGENTS.md](packages/engineering-ui/AGENTS.md) |
| Schematic editor, symbols | [schematic editor](docs/architecture/schematic-editor.md) |
| Charts, protection, load profiles | [graphing](docs/architecture/graphing.md) |
| MCP | [MCP](docs/architecture/mcp.md) |
| Packaging, release | [packaging](docs/architecture/packaging.md) |
| Migration milestone work | [implementation plan](docs/migration/implementation-plan.md), [feature inventory](docs/migration/feature-inventory.md), [risks](docs/migration/risks-and-decisions.md) |

## Mandatory rules

1. **Python owns engineering state.** Calculations, validation, connectivity,
   persistence and undo live in Python. Vue renders and collects input; Rust
   owns process lifecycle and transport. Never duplicate engineering logic in
   TypeScript, Rust or MCP tool descriptions.
2. **One writer.** Desktop and MCP use the same service commands on one owner
   thread. No second writable project copy, no MCP-only write path.
3. **Do not change engineering results while refactoring.** Compare before and
   after (smoke test now; [regression baseline](docs/migration/regression-baseline.md)
   once M1 exists). Intended changes need an ADR, before/after values and owner
   approval. Never widen tolerances or regenerate baselines to make a change pass.
4. **Keep old `.gepro` files loadable.** Element codes and field codes are
   permanent. Follow the [compatibility policy](docs/architecture/project-format.md#4-compatibility-policy-proposed).
5. **Headless engine.** New engine code must not import GTK, Tauri, MCP,
   transport or `modern` code (headless Cairo is allowed).
6. **No code execution from data.** Do not add `eval`, `exec` or `pickle` on
   project, database, clipboard or request data; existing uses are scheduled
   for removal ([ADR 0011](docs/decisions/0011-safe-expressions.md)).
7. **EngineeringUI boundary.** `packages/engineering-ui/`
   (`@kavilgroup/engineering-ui`) is **MIT** licensed and never imports
   application code or backend method names. Only MIT-compatible code enters
   it; the rest of the repository is GPL-3.0-or-later.
8. **Mutations are undoable.** Legacy code: `@undoable` generators and
   `with group(self, "...")`. Modern services: one transaction, one undo entry,
   one revision, one change event per command.
9. **Document decisions.** Significant architectural or behavioural decisions
   get an ADR in [docs/decisions/](docs/decisions/README.md). Mark documentation
   as *current* or *proposed*.
10. **Report honestly.** State which checks ran, their results and which were
    not run; record migration evidence in the
    [validation log](docs/migration/validation.md).

## Environment

The Python dev environment is managed by [pixi](https://pixi.sh) from
conda-forge (`pixi.toml` + committed `pixi.lock`). conda-forge ships prebuilt
GTK3, PyGObject, pandapower and WeasyPrint for Windows, Linux and macOS.

```bash
pixi install          # creates .pixi/envs/default (git-ignored)
pixi run start        # launch the GUI
pixi run smoke        # end-to-end check on sample_files/**/*.gepro (GTK window)
pixi run headless x.gepro   # headless open, analyse, export (no GTK, no display)
pixi run -e test test # regression baseline (pytest; needs a display / xvfb-run)
pixi run python ...   # any ad-hoc script inside the env
```

- Always run Python through `pixi run`. The system Python does not have GTK.
- Do **not** use pip or MSYS2 for dependencies. pandapower pins `pandas~=2.3` and
  `numpy<2.5`, and MSYS2 ships newer versions. Several transitive deps
  (cachebox, brotli, zopfli) don't build under MinGW. Add dependencies with
  `pixi add <pkg>` and commit both `pixi.toml` and `pixi.lock`.
- Exception: a **pure-Python** package missing or outdated on conda-forge may be
  added with `pixi add --pypi <pkg>` (locked in `pixi.lock`). Current use:
  pandapower 3.5.6 and WeasyPrint 70.0 (the version of the Windows
  executable) ([ADR 0015](docs/decisions/0015-python-and-pandapower-versions.md),
  [ADR 0016](docs/decisions/0016-weasyprint-windows-executable.md)).
  Compiled packages always come from conda-forge.
- The environment is Python 3.14 with pandapower 3.5.6 and WeasyPrint 70.0
  (milestone M1b). When a PyPI package's dependency is solved by conda-forge,
  mirror the package's version bounds in `[dependencies]` (see `pixi.toml`).
- `requirements.txt` / `setup.py` are legacy pins used by packaging
  (Flatpak/Snap/PyInstaller). Keep them in sync when changing deps, but they are
  not the dev environment. The Flatpak manifest still pins pandapower 2.14.9
  (see the M1b entry in the validation log).
- Activation (`tools/pixi_activate.*`) registers the librsvg gdk-pixbuf loader
  (the SVG icons fail to load without it).
- Node.js (24 LTS, `.nvmrc`) with npm workspaces `modern` and `packages/*`
  (M6). Run `npm ci` at the repository root; dependencies are pinned to exact
  versions (`.npmrc`), so add them with `npm install -w <workspace> <pkg>@<version>`
  and commit `package-lock.json`. Story tests need the Playwright browser once:
  `npx playwright install chromium-headless-shell`.

```bash
npm run dev              # modern/ shell in the browser (mock data), http://127.0.0.1:1420
npm run storybook        # EngineeringUI Storybook, http://localhost:6006
npm run check            # format, boundary, licences, type check, Vitest, builds
```

- Rust/Tauri arrive with milestone M5; follow
  [development guidelines](docs/development-guidelines.md#2-environment) then.

## Verifying changes (current)

1. `pixi run smoke`: builds the main window (mapped but never run), opens each sample
   project, runs diagnostics → power flow → symmetric and line-to-ground short
   circuit → rules check, then exports JSON, the HTML/PDF report and the drawing PDF.
   Use `--keep` to inspect outputs, or pass specific `.gepro` paths. It needs a
   desktop session/display (on Linux CI, use `xvfb-run`).
2. For UI changes, run `pixi run start` and exercise the change by hand.
   `pixi run start path/to/file.gepro` opens a project directly.
3. `xvfb-run -a pixi run -e test test`: regression baseline (M1). Captures
   every project in `sample_files/` and `tests/projects/` with the legacy code
   and compares with `tests/baseline/` using the documented tolerances. Any
   engine change must keep it green; intended result changes follow
   [regression baseline §6](docs/migration/regression-baseline.md#6-intentional-changes).
   Never regenerate `tests/baseline/` to make a change pass.
4. If you change calculations, compare results before and after on
   `sample_files/` and `tests/projects/` and say what moved.
5. Frontend changes (`modern/`, `packages/engineering-ui/`): `npm run check`
   (Prettier, dependency boundary, licences, `vue-tsc`, Vitest unit and
   Storybook story tests with axe in light and dark, library and app builds)
   and `npm run build-storybook`. For visual changes run `npm run dev` or
   `npm run storybook` and check keyboard operation and both themes.
6. Documentation-only changes: check links and `git diff --check`; build Sphinx
   only if user-manual pages changed.

Test layers (current: pytest baseline, Vitest, Storybook story tests;
planned: engine/service pytest, Playwright workflows) are in
[docs/testing.md](docs/testing.md).

## Current layout

```
gelectrical_launcher.py      entry point (logging setup, runs gelectrical.gtk.app.MainApp)
gelectrical/__init__.py      version only (no GTK import)
gelectrical/core/            constants, style (run-time colours/fonts), fields, paths,
                             undoable/group, geometry (replaces cairo.Region), interpolation
gelectrical/elementmodel/    one module per element family; ElementModel base in element.py;
                             each class has a unique `code`; registry.py is the code -> class map
gelectrical/symbols/         symbol geometry/extents, labels (Mako), text backends, Cairo rendering
gelectrical/model/           project (headless, event notifications), drawing, networkmodel,
                             pandapower, protection, rulescheck, graph
gelectrical/analysis/        pipeline.py: diagnostics -> power flow -> short circuit -> results; rules check
gelectrical/persistence/     gepro.py: .gepro read/write
gelectrical/reports/         report HTML/PDF, drawing PDF, JSON exports, tables, graphs (Agg), spreadsheet
gelectrical/undo.py          vendored undo library (undo.Stack)
gelectrical/gtk/             legacy GTK UI (ADR 0014): app.py (MainApp, MainWindow), project.py
                             (GtkProjectModel: views + dialogs), view/, interface/ (Glade),
                             widgets.py, pango_text.py (PangoCairo text backend)
gelectrical/misc.py          legacy re-export shim for gelectrical.gtk only (imports GTK)
gelectrical/database/        CSV/JSON equipment libraries
gelectrical/templates/       Jinja2 HTML/CSS report templates (WeasyPrint)
gelectrical/icons/           SVG element icons
source/                      .ods sources for the database CSVs + artwork
docs/                        user manual (Sphinx/MyST) + developer docs (see docs/README.md)
modern/                      Vue 3 + Quasar app shell (M6: mock data, no backend yet)
packages/engineering-ui/     EngineeringUI (@kavilgroup/engineering-ui, MIT): theme, icons,
                             shell components, inspector; Storybook and Vitest tests
sample_files/                sample .gepro projects (used by the smoke test)
tools/                       smoke test, headless_run.py, pixi activation scripts, npm checks
tools/baseline/              regression baseline capture (legacy GTK or --headless)/compare,
                             coverage project generator
tests/                       test_baseline.py (+ headless), engine/ (unit tests, no GTK),
                             baseline/ (canonical JSON), projects/ (.gepro)
```

The proposed structure is in [ARCHITECTURE.md](ARCHITECTURE.md#proposed-repository-structure).

## Conventions (current code)

- Match the surrounding style: 4-space indents, `log = logging.getLogger(__name__)`
  per module, and log messages formatted as `'Class - method - message'`.
- Element field definitions live in each element class (`self.fields`), with
  results in `res_fields`. A new element type needs: a class with a unique `code`,
  registration in `elementmodel/registry.py` (grep an existing `code` such as
  `element_load` for other touch points), an icon, and pandapower mapping in
  `model/pandapower.py`. Symbol data stays in the class (`schem_model`,
  `text_model`, `update_symbol()`, `symbol_active()`); drawing is in `symbols/`.
- Engine modules (everything outside `gelectrical/gtk/` and `misc.py`) import
  `gelectrical.core.*`, never `misc` or `gi`; `tests/engine` blocks `gi`.
- `.gepro` files are zips with `document.json` plus per-drawing JSON, versioned
  by `core.constants.PROJECT_FILE_VER`; read/write through `persistence/gepro.py`.
- New data files (database, templates, icons, glade) must also be added to the
  packaging manifests: `pyinstaller_spec.spec`, `MANIFEST.in`, and the
  Flatpak/Snap configs if relevant.
- Open text files with `encoding='utf-8'`. Windows users don't run with UTF-8 mode.
- Use pandapower 3.x APIs. Check `model/pandapower.py` for current usage
  before adding calls.
- Code adapted from GEstimator keeps its header plus an
  `Adapted from GEstimator <path> at <commit>` line.

## Git

- Default branch is `master`. Work on a feature branch and keep commits focused.
- Commit, push or open pull requests only when the user asks.
- Don't commit `.pixi/`, `node_modules/`, build outputs, generated reports or
  exported PDFs.
