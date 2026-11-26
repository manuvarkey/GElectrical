# Graphing and curve editors

Status: **proposed** (Phase 1). Navigation: [index](../README.md) ·
[frontend](frontend.md) · [EngineeringUI](engineering-ui.md) ·
[ADR 0006](../decisions/0006-charts.md).

## 1. Current implementation

| Use | Implementation |
| --- | --- |
| Load profile editor | `GraphViewDialog` + `GraphView` (Matplotlib `FigureCanvas` GTK3Agg); click to add/remove points; 24 hourly values; database import |
| Inline graph previews in properties | `GraphView` in `FieldView` (setting *show graphs*) |
| Protection coordination | `ProtectionViewDialog`: log-log time-current plot with hatched device bands, damage/starting curves, disconnection-time line, node fault-current markers |
| Time-series result graphs | Results pane graphs from aggregated time-series data |
| Report graphs | `GraphImage` → SVG embedded in report HTML |

Curve data comes from Python: `GraphModel` lists, `ProtectionModel.evaluate_curves`
(NumPy arrays, Shapely polygons) and pandapower result tables.

## 2. Target

Interactive graphs move to **Apache ECharts** (Apache-2.0) wrapped by
EngineeringUI `charts/` components. Report graphs keep Matplotlib (with the
`Agg` backend, moved out of the GTK module) until ECharts SVG output is shown to
match report requirements.

Python remains responsible for:

- Evaluating protection, damage and starting curves (including the safe
  expression evaluator), band polygons and scaling to a voltage base.
- Validating load profile edits (value ranges, 24 points, monotonic time).
- Producing result series and statistics.

The frontend receives arrays of `[x, y]` in engineering units and renders them.

## 3. Capability check

| Requirement | ECharts approach | Verify in M8 |
| --- | --- | --- |
| Linear and log axes | `xAxis/yAxis.type = 'log'`, `logBase: 10` | Decade ticks and minor ticks |
| Log-log protection plots | Two log axes, current (A) vs time (s) | Range 0.01–3600 s, 1 A–100 kA (current `GRAPH_PROT_*` limits) |
| Multiple curves | Multiple `line` series | 20+ devices |
| Shaded tolerance bands | `custom` series drawing polygons via `api.coord` (works on log axes); hatch with `decal` patterns | Band between upper and lower curves, matching current hatching meaning |
| Operating regions/limits | `markLine`, `markArea` | Disconnection-time line, fault-current markers (max/min) |
| Legends and tooltips | Built in; formatter with engineering units | Legend toggling per device |
| Zoom and pan | `dataZoom` (inside + slider) | Log-axis zoom behaviour |
| Draggable control points | `graphic` elements with `ondrag` + `convertFromPixel` | Load profile points (snap to hour, clamp range); setting handles optional later |
| Load-profile editing | Step/line series + draggable points; table entry alternative | Keyboard editing via linked data grid |
| Engineering units and labels | Axis `formatter` using shared formatting helper (k, M prefixes) | 1 k, 10 k, 100 k labels on current axis |
| Large time series | `sampling: 'lttb'`, `large: true`, progressive rendering | 8,760 points × 10 series |
| SVG/vector export | `renderer: 'svg'` + `getDataURL({type: 'svg'})` or SSR | Compare with report needs |
| Light/dark themes | Theme objects built from EngineeringUI tokens | Token-driven, no hard-coded colours |
| Responsive resizing | `ResizeObserver` → `chart.resize()` in the wrapper | Panel resizing |

## 4. EngineeringUI chart components

| Component | Purpose | Key props / events |
| --- | --- | --- |
| `EuiChart` | Thin ECharts wrapper: init, theme, resize, dispose, SVG export | `option`, `renderer`; `ready`, `click` |
| `EuiLogLogPlot` | Time-current plot | `series: EuiCurveSeries[]`, `bands: EuiBand[]`, `markers`, `limits`, axis ranges; `select(seriesId)` |
| `EuiCurveEditor` | Editable point series (load profiles, custom curves) | `points`, `xDomain`, `yDomain`, `snap`; `change(points)` (host validates through backend) |
| `EuiSeriesChart` | Result time series and bar charts | `series`, `units` |

Types (`EuiCurveSeries`, `EuiBand`, `EuiMarker`) contain only presentation data
(id, label, points, style role). Style roles map to theme tokens
(`device`, `damage`, `starting`, `limit`, `fault-max`, `fault-min`).

## 5. Interaction flow (protection coordination)

1. User selects devices, cables, transformers, motors and nodes; opens the
   Protection view.
2. Frontend requests `protection.coordination(uids, mode)`; Python returns
   curves, bands, markers, limits and editable parameter schemas.
3. Parameter edits call `protection.set_parameters` (preview while dragging a
   slider or typing; commit on change). Python returns re-evaluated curves.
4. Export of settings to a spreadsheet stays a Python export.

## 6. Proof of concept scope (M8)

1. Export fixtures from the engine: coordination datasets for the sample
   projects and load profiles.
2. Build `EuiLogLogPlot` and `EuiCurveEditor` stories with these fixtures in
   light/dark themes.
3. Verify every row in section 3; record screenshots and measurements.
4. Compare an ECharts SVG export with the Matplotlib report graph for one
   coordination case and decide whether report graphs can switch later.
