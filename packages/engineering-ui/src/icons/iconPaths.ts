// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
// Adapted from GEstimator modern/src/components/AppIcon.vue at e4e4fb295899feda5253ba216613c70c1f256d4e
//
// Locally drawn icons following the OpenAEC B2 visual grammar (reference only,
// no artwork copied): 24-unit grid, round caps/joins, 1.6-unit corner radii,
// open line work, a neutral body and at most one small accent detail.
// Navigation, window and state glyphs stay monochrome. Each entry is [body, accent?].

const rr = (x: number, y: number, w: number, h: number, r = 1.6) =>
  `M${x + r} ${y}H${x + w - r}a${r} ${r} 0 0 1 ${r} ${r}V${y + h - r}a${r} ${r} 0 0 1-${r} ${r}H${x + r}a${r} ${r} 0 0 1-${r}-${r}V${y + r}a${r} ${r} 0 0 1 ${r}-${r}Z`;
const circle = (cx: number, cy: number, r: number) =>
  `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0-${2 * r} 0Z`;
const backSheet = "M16 5V4.6A1.6 1.6 0 0 0 14.4 3H4.6A1.6 1.6 0 0 0 3 4.6v9.8A1.6 1.6 0 0 0 4.6 16H5";
const tray = "M4 15v3.4A1.6 1.6 0 0 0 5.6 20h12.8a1.6 1.6 0 0 0 1.6-1.6V15";
const bolt = "M13 3 6 13.5h5.5L10.5 21 18 10.5h-5.5Z";

export const iconPaths = {
  blank: [""],
  // Navigation, window and state glyphs: monochrome.
  forward: ["M4 12h15 M13 6l6 6-6 6"],
  back: ["M20 12H5 M11 6l-6 6 6 6"],
  up: ["m6 14.5 6-6 6 6"],
  down: ["m6 9.5 6 6 6-6"],
  chevron: ["m9 5.5 6.5 6.5L9 18.5"],
  collapse: ["m8 9 4-4 4 4 M8 15l4 4 4-4"],
  expand: ["m8 5 4 4 4-4 M8 19l4-4 4 4"],
  close: ["m6 6 12 12 M6 18 18 6"],
  check: ["m5 12.5 4.5 4.5L19 7"],
  dots: ["M5 12h.01 M12 12h.01 M19 12h.01"],
  minimize: ["M5 17h14"],
  maximize: [rr(5, 5, 14, 14)],
  plus: ["M12 5v14 M5 12h14"],
  minus: ["M5 12h14"],
  play: ["M8 5.3v13.4a.8.8 0 0 0 1.2.7l10.6-6.7a.8.8 0 0 0 0-1.4L9.2 4.6A.8.8 0 0 0 8 5.3Z"],
  stop: [rr(5, 5, 14, 14)],
  undo: ["M4 9h11.5a4.5 4.5 0 0 1 0 9H10 M8 5 4 9l4 4"],
  redo: ["M20 9H8.5a4.5 4.5 0 0 0 0 9H14 M16 5l4 4-4 4"],
  sun: [
    circle(12, 12, 4) +
      " M12 2.5v2 M12 19.5v2 M2.5 12h2 M19.5 12h2 M5.3 5.3l1.4 1.4 M17.3 17.3l1.4 1.4 M5.3 18.7l1.4-1.4 M17.3 6.7l1.4-1.4",
  ],
  moon: ["M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z"],
  filter: ["M4.6 4h14.8a.6.6 0 0 1 .5 1L14 12.5v6l-4 2v-8L4.1 5a.6.6 0 0 1 .5-1Z"],
  pointer: ["M5 3.5 18.5 11l-6 1.5-3 5.5Z"],
  // Two-tone action icons: neutral body, small accent detail.
  file: [
    "M14 3H6.6A1.6 1.6 0 0 0 5 4.6v14.8A1.6 1.6 0 0 0 6.6 21h10.8a1.6 1.6 0 0 0 1.6-1.6V8Z M14 3v3.4A1.6 1.6 0 0 0 15.6 8H19",
    "M9 13h6 M9 17h4",
  ],
  folder: [
    "M3 18.4V5.6A1.6 1.6 0 0 1 4.6 4h3.8a1.6 1.6 0 0 1 1.3.7l1.1 1.6a1.6 1.6 0 0 0 1.3.7h5.3A1.6 1.6 0 0 1 19 8.6V11 M3 18.4A1.6 1.6 0 0 0 4.6 20H16.9a1.6 1.6 0 0 0 1.5-1.1l2.4-6.6a1 1 0 0 0-.9-1.3H7.4a1.6 1.6 0 0 0-1.5 1.1L3 18.4",
  ],
  save: [
    "M4.6 3h10.7a1.6 1.6 0 0 1 1.1.5l4.1 4.1a1.6 1.6 0 0 1 .5 1.1v10.7a1.6 1.6 0 0 1-1.6 1.6H4.6A1.6 1.6 0 0 1 3 19.4V4.6A1.6 1.6 0 0 1 4.6 3Z M7.5 3v3.9a.6.6 0 0 0 .6.6h6.4",
    "M7.5 21v-5.4a.6.6 0 0 1 .6-.6h7.8a.6.6 0 0 1 .6.6V21",
  ],
  database: ["M4 6a8 3 0 1 0 16 0a8 3 0 1 0-16 0 M4 6v12a8 3 0 0 0 16 0V6", "M4 12a8 3 0 0 0 16 0"],
  grid: [rr(3, 3, 18, 18) + " M3 15h18 M9 9v12", "M3 9h18"],
  search: [circle(10.5, 10.5, 6.5), "m15.5 15.5 4.5 4.5"],
  "zoom-in": [circle(10.5, 10.5, 6.5) + " M10.5 8v5 M8 10.5h5", "m15.5 15.5 4.5 4.5"],
  "zoom-out": [circle(10.5, 10.5, 6.5) + " M8 10.5h5", "m15.5 15.5 4.5 4.5"],
  copy: [rr(8, 8, 13, 13), backSheet],
  cut: [circle(6.5, 17.5, 2.5) + circle(17.5, 17.5, 2.5) + "M8.3 15.7 16 4 M15.7 15.7 8 4", "M12 11.2v.01"],
  paste: [
    "M8 5H6.6A1.6 1.6 0 0 0 5 6.6v12.8A1.6 1.6 0 0 0 6.6 21h10.8a1.6 1.6 0 0 0 1.6-1.6V6.6A1.6 1.6 0 0 0 17.4 5H16 M9 12h6 M9 16h4",
    rr(8, 3, 8, 4, 1),
  ],
  trash: [
    "M4 6h16 M9 6V4.6A1.6 1.6 0 0 1 10.6 3h2.8A1.6 1.6 0 0 1 15 4.6V6 M6 6l.9 13.5A1.6 1.6 0 0 0 8.5 21h7a1.6 1.6 0 0 0 1.6-1.5L18 6",
    "M10 10.5v6 M14 10.5v6",
  ],
  panel: [rr(3, 4, 18, 16), "M15 4v16"],
  "panel-left": [rr(3, 4, 18, 16), "M9 4v16"],
  "panel-bottom": [rr(3, 4, 18, 16), "M3 14h18"],
  sheet: [rr(3, 5, 18, 14), "M3 9h18"],
  help: [circle(12, 12, 9) + " M9.5 9.5a2.5 2.5 0 0 1 5 0c0 1.7-2.5 2-2.5 4", circle(12, 17, 0.5)],
  settings: ["M4 7h16 M4 17h16", "M9 4.5v5 M15 14.5v5"],
  edit: ["M4 20h4l11.3-11.3a1.6 1.6 0 0 0 0-2.3l-1.7-1.7a1.6 1.6 0 0 0-2.3 0L4 16v4Z", "m13.5 6.5 4 4"],
  refresh: ["M19 12a7 7 0 0 0-12.2-4.7L5 9 M5 12a7 7 0 0 0 12.2 4.7L19 15", "M5 4.5V9h4.5 M19 19.5V15h-4.5"],
  chart: ["M3 3v16.4A1.6 1.6 0 0 0 4.6 21H21", "M8 17v-5 M13 17V6 M18 17v-3"],
  link: ["M10.5 7.5l1.8-1.8a4 4 0 0 1 5.7 5.7l-1.8 1.8 M13.5 16.5l-1.8 1.8a4 4 0 0 1-5.7-5.7l1.8-1.8", "m9.5 14.5 5-5"],
  import: [tray + " M12 4v10.5", "m7.5 10.5 4.5 4.5 4.5-4.5"],
  export: [tray + " M12 4.5V15", "M7.5 8.5 12 4l4.5 4.5"],
  calculate: [
    rr(5, 3, 14, 18) + " M8.5 12h.01 M12 12h.01 M15.5 12h.01 M8.5 15.5h.01 M12 15.5h.01 M15.5 15.5h.01",
    "M8.5 7h7",
  ],
  rows: ["M4 5h16 M4 19h16", "M4 10h16 M4 14h16"],
  palette: [rr(3, 3, 7.5, 7.5) + rr(13.5, 3, 7.5, 7.5) + rr(3, 13.5, 7.5, 7.5), rr(13.5, 13.5, 7.5, 7.5)],
  // State glyphs with a text label wherever they convey meaning.
  info: [circle(12, 12, 9) + " M12 11v5", "M12 7.8h.01"],
  warning: [
    "M10.3 4.3 2.8 17.4A2 2 0 0 0 4.5 20.4h15a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z",
    "M12 9.5v4 M12 17h.01",
  ],
  error: [circle(12, 12, 9), "m9 9 6 6 M15 9l-6 6"],
  success: [circle(12, 12, 9), "m8 12.5 2.8 2.8L16.2 9.5"],
  // Electrical glyphs (GElectrical additions).
  busbar: ["M7 8v10 M12 8v10 M17 8v10", "M3 8h18"],
  transformer: [circle(12, 8, 4.5) + " M12 1.5v2 M12 20.5v2", circle(12, 16, 4.5)],
  breaker: ["M12 3v5 M12 16v5 M12 16 16.5 8.5", "m10.5 6.5 3 3 M13.5 6.5l-3 3"],
  load: ["M12 3v9", "M7.5 12h9L12 20Z"],
  generator: [circle(12, 12, 8), "M8 12c1.3-2.7 2.7-2.7 4 0s2.7 2.7 4 0"],
  cable: ["M4 18c4 0 4-12 8-12s4 12 8 12", "M4 18h.01 M20 18h.01"],
  ground: ["M12 3v9 M5 12h14 M8 15.5h8", "M10.5 19h3"],
  "power-flow": [bolt],
  fault: [bolt, "M19 3.5v3.5 M19 10v.01"],
  protection: ["M12 3 5 6v5.5c0 4.3 3 8 7 9.5 4-1.5 7-5.2 7-9.5V6Z", "m9 12 2 2 4-4"],
} as const satisfies Record<string, readonly [string, string?]>;

export type EuiIconName = keyof typeof iconPaths;
export const iconNames = Object.keys(iconPaths) as EuiIconName[];
