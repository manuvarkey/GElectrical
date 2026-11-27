# 0018. Headless engine split: notifications, symbol layers and text backends

- Status: Proposed (implemented in M2; raster limit for Cairo text accepted by
  the owner on 2026-11-27; owner review of the ADR pending)
- Date: 2026-11-27
- Related: [implementation plan M2](../migration/implementation-plan.md#m2--headless-engine-extraction-poc-1),
  [backend §2](../architecture/backend.md#2-engine-package-gelectrical),
  [ADR 0014](0014-legacy-gtk-location.md), [ADR 0001](0001-headless-backend-authority.md)

## Context

M2 makes the engine importable and runnable without GTK while the legacy GTK
application keeps working and its results stay identical. Three couplings
needed a design choice: `ProjectModel` owned GTK views and opened dialogs;
element geometry (extents, some ports) was computed as a side effect of Cairo
rendering with PangoCairo text; module-level defaults were shared (D4, D15).

## Decision

1. **Model notifications.** `gelectrical.model.project.ProjectModel` has no
   views. It takes explicit arguments (`stack`, `program_settings`,
   `element_models`, `listeners`) instead of `program_state` and emits events
   to subscribers (`page_added`, `page_removed`, `page_moved`,
   `page_selected`, `page_marked`, `tabs_changed`, `fields_changed`,
   `diagnostics`, `refresh`). The GTK UI subclasses it as
   `gelectrical.gtk.project.GtkProjectModel`, which subscribes, owns the
   notebook and sheet views and opens the load-profile and protection
   dialogs. `program_state` remains only inside `gelectrical/gtk/`.
2. **Symbol layers.** Elements keep their symbol data (`schem_model`,
   `text_model`, `ports`) and expose `update_symbol()` (the former
   preprocessing of `render_element`), `symbol_active()` (inactive colour)
   and `get_symbol_layers()` (ordered `('schem'|'text', model, colour)`).
   `gelectrical.symbols.geometry` computes extents from the layers without
   drawing; `gelectrical.symbols.render` draws them. `get_dimensions()`
   computes the extents when they are not current, so it no longer depends on
   a prior render.
3. **Text backends.** Text is measured and drawn through
   `gelectrical.symbols.text.TextBackend`. The engine default is the Cairo toy
   API (`CairoTextBackend`, no PyGObject). The GTK application installs
   `gelectrical.gtk.pango_text.PangoTextBackend` (the pre-M2 drawing code) at
   start-up. While rendering, text is measured on the output context as
   before; geometry queries measure on an identity-scaled context.
4. **Pure geometry.** `gelectrical.core.geometry` replaces `cairo.Region`
   (`rect_overlap`, `rect_contains_point`, `region_extents`) with the same
   pixman semantics, including empty rectangles.
5. **No shared mutable defaults.** Each project gets deep copies of the
   default project settings and load profiles (D4); field helpers no longer
   use shared default dictionaries (D15).
6. **Process-wide style.** Colours and fonts changed by the GTK app at start-up
   live in `gelectrical.core.style` and are read at call time;
   `gelectrical.misc` remains a GTK-only re-export shim that forwards reads
   and writes of these values. Per-session style arrives with the services
   (M4).

## Alternatives considered

- *PangoCairo for headless text* (decision rule option 2): matches the legacy
  raster exactly but adds `gi` and Pango to the sidecar. Not needed: Cairo
  metrics match PangoCairo extents within 3 drawing units (limit: one grid
  unit, 16).
- *fontTools metrics or glyph outlines*: platform independent, but text
  becomes paths in the PDF and kerning needs extra work.
- *Composition instead of a GTK subclass*: cleaner separation but every GTK
  call site (`project.drawing_view`, `project.update_tabs()`, …) would change
  during M2; the subclass keeps the retiring UI stable.

## Consequences

- Engine modules must not import `gi`, `gelectrical.gtk` or
  `gelectrical.misc`; `tests/engine` blocks `gi`.
- Headless drawings differ from the legacy raster only in glyph rendering
  (0.12 %–0.61 % of pixels at 150 dpi in all 25 baseline drawings, above
  the 0.1 % baseline limit). With PangoCairo text the headless drawings are
  pixel-identical. The owner chose (2026-11-27) a separate raster limit for
  headless captures with Cairo text: at most **1 %** differing pixels
  (`HEADLESS_CAIRO_TEXT_PIXEL_FRACTION` in `tools/baseline/canonical.py`),
  instead of PangoCairo in the sidecar. The 0.1 % limit for the legacy
  capture and for PangoCairo-text captures is unchanged.
- `osifont` is resolved through the system font configuration for both
  backends (not bundled in the package yet).

## Verification

Legacy regression baseline (GTK window), headless regression baseline
(`capture.py --headless`), engine unit tests, smoke test; results in the
[validation log](../migration/validation.md) (M2 entry).
