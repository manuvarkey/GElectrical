# Development guidelines

Navigation: [documentation index](README.md) · [architecture overview](../ARCHITECTURE.md)
· [testing](testing.md) · [UI guidelines](ui-guidelines.md).

These guidelines apply to the current code and to the modernisation work.
Mandatory rules are summarised in [AGENTS.md](../AGENTS.md); this page explains
how to follow them.

## 1. Before changing code

1. Identify the layer that owns the change ([ARCHITECTURE.md](../ARCHITECTURE.md)).
2. Read the contract for that layer in `docs/architecture/` and, for migration
   work, the milestone in the [implementation plan](migration/implementation-plan.md).
3. Check the [feature inventory](migration/feature-inventory.md) for affected
   user behaviour and the [risk register](migration/risks-and-decisions.md).
4. Work on a feature branch; keep each change focused and reviewable.

## 2. Environment

- Python: `pixi install`; run everything with `pixi run ...`. Add Python
  dependencies with `pixi add` and commit `pixi.toml` and `pixi.lock`. Use
  `pixi add --pypi` only for pure-Python packages missing or outdated on
  conda-forge (pandapower, [ADR 0015](decisions/0015-python-and-pandapower-versions.md)).
  Target Python 3.14 from M1b. Keep legacy pins (`requirements.txt`,
  `setup.py`) in sync while they exist.
- JavaScript (current since M6): Node.js 24 LTS (`.nvmrc`) with npm; `npm ci`
  at the repository root installs all workspaces (`modern`, `packages/*`).
  Dependencies are pinned to exact versions (`.npmrc` `save-exact=true`);
  only peer dependencies use ranges. New dependencies must have a licence that
  `npm run check:licences` accepts (MIT-compatible for EngineeringUI). Commit
  `package-lock.json`. `npm run check` runs all frontend checks.
- Rust (from M5): stable toolchain via rustup; commit `Cargo.lock`.

## 3. Keep changes in their layer

| If you are changing... | Do it in | Never in |
| --- | --- | --- |
| A calculation, field rule, element behaviour, connectivity | Engine (`gelectrical/`) | Services, Vue, Rust, MCP descriptions |
| How a user action changes the project | Service command | Vue components |
| What is displayed and how it is interacted with | Vue / EngineeringUI | Python services (beyond data shape) |
| Process lifecycle, native dialogs | Rust / `modern/src/services/native.ts` | Engine |
| AI tool surface | `modern/backend/mcp/` | Engine, services' internals |
| Reusable visual component | EngineeringUI | `modern/src/components/` (if reused) |

The engine imports no GTK, Tauri, MCP, transport or `modern` code. Services
import no transport. EngineeringUI imports nothing from `modern/` or
`gelectrical/`.

## 4. Engineering behaviour

- Do not change engineering results while refactoring. Run the
  [regression baseline](migration/regression-baseline.md) for any change under
  `gelectrical/`.
- An intended correction needs an ADR, before/after values on sample and
  coverage projects, owner approval and a baseline update in the same PR.
- Keep units explicit in names or field metadata (`_kv`, `_ka`, `_km`, `_mva`).
- Keep element classes the single source of truth for field definitions and
  side effects; generate schemas from them.

## 5. Data and compatibility

- Keep old `.gepro` files loadable; follow the
  [project format policy](architecture/project-format.md#4-compatibility-policy-proposed).
- Element codes and field codes are permanent.
- Never evaluate project, clipboard, database or request text with `eval`,
  `exec` or `pickle`; use `gelectrical.core.expressions` (from M3).
- Open text files with `encoding='utf-8'`.
- Save atomically; never leave a partially written project.

## 6. Commands, undo and revisions (from M4)

- Every mutation is a service command inside a transaction: validate first,
  apply through engine methods, one undo entry, one revision increment, one
  `changed` event.
- Previews roll back completely (state, history, revision, dirty flag).
- Long work (analysis, exports) runs as a job, never on the owner thread.
- Desktop and MCP use the same command; do not add MCP-only write paths.

## 7. Modularity

- Treat ~600 lines per module and ~80 lines per function as review triggers
  (GEstimator rule), not targets. The legacy files `misc.py`, `line.py`,
  `pandapower.py`, `switch.py`, `project.py` and `__init__.py` already exceed
  this; do not add unrelated responsibilities to them.
- Extract a named helper, component or composable before growing a shell file
  (`App.vue`, service routers).
- Remove superseded code in the same change. Do not split files into numbered
  parts or hide state in mixins.

## 8. Code style

- Python: match surrounding style; 4-space indents;
  `log = logging.getLogger(__name__)`; log messages as
  `'Class - method - message'`. New modules: module docstring, docstrings for
  public functions, short step comments for multi-step logic. A formatter
  configuration (Ruff, as in GEstimator) is proposed for new modules only in M1;
  do not reformat legacy files wholesale.
- TypeScript/Vue: strict TypeScript; Prettier (2 spaces, double quotes,
  semicolons, 120 columns, as GEstimator); `<script setup lang="ts">`; scoped
  styles using tokens.
- Rust: `rustfmt`, Clippy with warnings denied; propagate errors with `Result`.
- Comments explain why and constraints; avoid narrating obvious code.

## 9. Provenance and licences

- Code adapted from GEstimator keeps its header and adds
  `Adapted from GEstimator <path> at <commit>`. Inside
  `packages/engineering-ui/` (MIT), adapted GEstimator code is relicensed to
  MIT by the copyright holder and uses the MIT header instead.
- New dependencies of EngineeringUI must be MIT-compatible (MIT, BSD,
  Apache-2.0, ISC).
- Do not copy code from Open Planner Studio or other projects; use them as
  visual references only unless an ADR approves reuse with licence review.
- New dependencies: check licence compatibility with GPL-3.0-or-later and
  record notable ones in the [licence inventory](migration/risks-and-decisions.md#4-licence-inventory-target-stack).

## 10. Packaging manifests

New data files (databases, templates, icons, symbols, skills, Glade files while
they exist) must be added to every packaging manifest in use: currently
`pyinstaller_spec.spec`, `MANIFEST.in`, Flatpak and Snap configs; from M5 the
sidecar build script and Tauri resources.

## 11. Finish a change

1. Run the checks for the changed layers ([testing](testing.md)).
2. Update the contract document if behaviour or ownership changed.
3. Update the feature inventory and append evidence to the
   [validation log](migration/validation.md) for migration work.
4. Describe in the PR what changed, what was verified and what was not.
