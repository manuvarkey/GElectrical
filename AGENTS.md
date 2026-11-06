# AGENTS.md

Guidance for AI coding agents working on GElectrical: a GTK3/PyGObject desktop
app for LV/MV electrical network analysis, with pandapower as the solver backend.

## Environment

The dev environment is managed by [pixi](https://pixi.sh) from conda-forge
(`pixi.toml` + committed `pixi.lock`). conda-forge ships prebuilt GTK3,
PyGObject, pandapower and weasyprint for Windows, Linux and macOS.

```bash
pixi install          # creates .pixi/envs/default (git-ignored)
pixi run start        # launch the GUI
pixi run smoke        # end-to-end check on sample_files/**/*.gepro
pixi run python ...   # any ad-hoc script inside the env
```

- Always run Python through `pixi run`. The system Python does not have GTK.
- Do **not** use pip or MSYS2 for dependencies. pandapower pins `pandas~=2.3` and
  `numpy<2.5`, and MSYS2 ships newer versions. Several transitive deps
  (cachebox, brotli, zopfli) don't build under MinGW. Add dependencies with
  `pixi add <pkg>` and commit both `pixi.toml` and `pixi.lock`.
- `requirements.txt` / `setup.py` are legacy pins used by packaging
  (Flatpak/Snap/PyInstaller). Keep them in sync when changing deps, but they are
  not the dev environment.
- Activation (`tools/pixi_activate.*`) registers the librsvg gdk-pixbuf loader
  (the SVG icons fail to load without it).

## Verifying changes

There is no unit test suite. Use these checks:

1. `pixi run smoke`: builds the main window (not shown), opens each sample
   project, runs diagnostics → power flow → symmetric and line-to-ground short
   circuit → rules check, then exports JSON, the HTML/PDF report and the drawing PDF.
   Use `--keep` to inspect outputs, or pass specific `.gepro` paths. It needs a
   desktop session/display (on Linux CI, use `xvfb-run`).
2. For UI changes, run `pixi run start` and exercise the change by hand.
   `pixi run start path/to/file.gepro` opens a project directly.
3. If you change calculations, compare results before and after on
   `sample_files/` and say what moved. Results are engineering outputs that users
   rely on.

## Layout

```
gelectrical_launcher.py      entry point (logging setup, runs MainApp)
gelectrical/__init__.py      MainApp (Gtk.Application) + MainWindow: UI callbacks,
                             open/save, on_run_analysis pipeline
gelectrical/misc.py          constants, default project/program settings, helpers
                             (abs_path, open_library, undoable/group), file version
gelectrical/undo.py          vendored undo library (undo.Stack, @undoable generators)
gelectrical/model/
  project.py                 ProjectModel: drawings, settings, analysis orchestration,
                             report/drawing/JSON export
  drawing.py                 DrawingModel: elements on one schematic page
  networkmodel.py            schematic → graph of nodes/elements
  pandapower.py              PandaPowerModel: builds pp nets (powerflow/LF/GF),
                             runs PF, timeseries, SC; maps results back
  rulescheck.py              electrical rules check (IEC/local guidelines)
  protection.py, graph.py    protection curves, load-profile/graph models
gelectrical/elementmodel/    one module per element family (load, line, switch,
                             transformer, grid, busbar, ...); ElementModel base in
                             element.py; each class has a unique `code`
gelectrical/view/            GTK views/dialogs (drawing canvas, fields, results,
                             messages, protection, database)
gelectrical/interface/       Glade .glade/.ui files for windows and dialogs
gelectrical/database/        CSV/JSON equipment libraries (cables, CBs, fuses, ...)
gelectrical/templates/       Jinja2 HTML/CSS report templates (rendered by weasyprint)
gelectrical/icons/           SVG element icons
source/                      .ods sources for the database CSVs + artwork
docs/                        Sphinx/MyST user docs (Read the Docs)
sample_files/                sample .gepro projects (used by the smoke test)
```

## Conventions

- Match the surrounding style: 4-space indents, `log = logging.getLogger(__name__)`
  per module, and log messages formatted as `'Class - method - message'`.
- State-changing model operations are `@undoable` generators: apply the change,
  `yield "Description"`, then do the inverse call. Use `with group(self, "...")`
  to batch them. New mutations must be undoable.
- Element field definitions live in each element class (`self.fields`), with
  results in `res_fields`. A new element type needs: a class with a unique `code`,
  registration wherever existing elements are enumerated (grep an existing
  `code` such as `element_load` to find every touch point), an icon, and
  pandapower mapping in `model/pandapower.py`.
- `.gepro` files are zips with `document.json` plus per-drawing JSON, versioned
  by `misc.PROJECT_FILE_VER`. Keep old project files loadable. Don't change
  the serialized schema without a migration path.
- New data files (database, templates, icons, glade) must also be added to the
  packaging manifests: `pyinstaller_spec.spec`, `MANIFEST.in`, and the
  Flatpak/Snap configs if relevant.
- Open text files with `encoding='utf-8'`. Windows users don't run with UTF-8 mode.
- Use pandapower 3.x APIs. A recent commit adapted the diagnostics to the newer
  pandapower version, so check `model/pandapower.py` for the current usage
  before adding calls.

## Git

- Default branch is `master`. Work on a feature branch and keep commits focused.
- Don't commit `.pixi/`, generated reports or exported PDFs.
