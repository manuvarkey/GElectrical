# AGENTS.md

Guidance for AI coding agents working on GElectrical: an LV/MV electrical
network analysis desktop application with pandapower as the solver backend.

**Current implementation:** GTK3/PyGObject application (`gelectrical/`).
**In progress:** migration to Tauri 2 + Vue 3/TypeScript + Quasar with a
headless Python backend, an MCP server and the EngineeringUI library. Phase 1
(planning) is complete and was reviewed by the owner on 2026-11-26 (decisions in
[risks and decisions](docs/migration/risks-and-decisions.md#2-owner-decisions));
**no migration code exists yet**.
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
pixi run smoke        # end-to-end check on sample_files/**/*.gepro
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
- Node.js/npm workspaces and Rust/Tauri arrive with milestones M5/M6; follow
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
5. Documentation-only changes: check links and `git diff --check`; build Sphinx
   only if user-manual pages changed.

Planned test layers (pytest, Vitest, Storybook, Playwright) are in
[docs/testing.md](docs/testing.md).

## Current layout

```
gelectrical_launcher.py      entry point (logging setup, runs MainApp)
gelectrical/__init__.py      MainApp (Gtk.Application) + MainWindow: UI callbacks,
                             open/save, on_run_analysis pipeline, element registry
gelectrical/misc.py          constants, default settings, field helpers, GTK/Cairo helpers,
                             undoable/group, file version
gelectrical/undo.py          vendored undo library (undo.Stack, @undoable generators)
gelectrical/model/           project, drawing, networkmodel, pandapower, protection,
                             rulescheck, graph
gelectrical/elementmodel/    one module per element family; ElementModel base in element.py;
                             each class has a unique `code`
gelectrical/view/            GTK views/dialogs (drawing canvas, fields, results, messages,
                             protection, database, graphs)
gelectrical/interface/       Glade .glade/.ui files
gelectrical/database/        CSV/JSON equipment libraries
gelectrical/templates/       Jinja2 HTML/CSS report templates (WeasyPrint)
gelectrical/icons/           SVG element icons
source/                      .ods sources for the database CSVs + artwork
docs/                        user manual (Sphinx/MyST) + developer docs (see docs/README.md)
packages/engineering-ui/     planned EngineeringUI package (docs only so far)
sample_files/                sample .gepro projects (used by the smoke test)
tools/                       smoke test, pixi activation scripts
tools/baseline/              regression baseline capture/compare, coverage project generator
tests/                       test_baseline.py, baseline/ (canonical JSON), projects/ (.gepro)
```

The proposed structure is in [ARCHITECTURE.md](ARCHITECTURE.md#proposed-repository-structure).

## Conventions (current code)

- Match the surrounding style: 4-space indents, `log = logging.getLogger(__name__)`
  per module, and log messages formatted as `'Class - method - message'`.
- Element field definitions live in each element class (`self.fields`), with
  results in `res_fields`. A new element type needs: a class with a unique `code`,
  registration wherever existing elements are enumerated (grep an existing
  `code` such as `element_load` to find every touch point), an icon, and
  pandapower mapping in `model/pandapower.py`.
- `.gepro` files are zips with `document.json` plus per-drawing JSON, versioned
  by `misc.PROJECT_FILE_VER`.
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
