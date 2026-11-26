# 0006. Apache ECharts for interactive graphs; Matplotlib kept for reports

- Status: Accepted in direction (owner 2026-11-26); details finalised by the M8 PoC
- Date: 2026-11-26
- Related: [graphing](../architecture/graphing.md)

## Context

Interactive graphs (load profile editor, protection coordination, result
graphs) use Matplotlib embedded in GTK. Reports embed Matplotlib SVG images.

## Decision

- Interactive graphs use Apache ECharts (Apache-2.0) through EngineeringUI
  `charts/` wrappers. Curve evaluation and validation stay in Python.
- Report graphs keep Matplotlib with the `Agg` backend (moved out of the GTK
  module) until ECharts SVG output is shown to be equivalent for reports.

## Alternatives considered

- *Plotly.js* (MIT): strong log-axis support but heavier bundle and less
  flexible custom drawing for bands.
- *uPlot* (MIT): fast for time series but limited log-log banding and editing.
- *Custom D3/SVG*: maximum control, more code.

## Consequences

Two chart technologies coexist temporarily (ECharts in UI, Matplotlib in
reports). Styling roles must map to both from the same tokens.

## Verification

M8 capability table: log-log axes, polygon bands with hatching, draggable
points, large series, SVG export, themes.
