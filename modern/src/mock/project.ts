// SPDX-License-Identifier: GPL-3.0-or-later
// Mock data for the M6 shell. Replaced by backend sessions in M9; nothing here
// is engineering logic.
import type { EuiDocumentItem, EuiFieldSchema, EuiFieldValue, EuiIconName } from "@kavilgroup/engineering-ui";

export const mockDocuments: EuiDocumentItem[] = [
  { id: "doc-1", title: "Main substation", path: "~/projects/main-substation.gepro" },
  { id: "doc-2", title: "Factory feeder", path: "~/projects/factory-feeder.gepro", dirty: true },
];

export interface PaletteItem {
  code: string;
  name: string;
  icon: EuiIconName;
}

export const mockPalette: { group: string; items: PaletteItem[] }[] = [
  {
    group: "Sources",
    items: [
      { code: "element_grid", name: "Grid supply", icon: "generator" },
      { code: "element_transformer", name: "Transformer", icon: "transformer" },
    ],
  },
  {
    group: "Distribution",
    items: [
      { code: "element_busbar", name: "Busbar", icon: "busbar" },
      { code: "element_switch", name: "Circuit breaker", icon: "breaker" },
      { code: "element_line", name: "Cable", icon: "cable" },
    ],
  },
  {
    group: "Loads",
    items: [
      { code: "element_load", name: "Load", icon: "load" },
      { code: "element_reference", name: "Earth", icon: "ground" },
    ],
  },
];

/** Field schema of a load in the backend FieldSchema shape (fixture for M6). */
export const mockLoadFields: EuiFieldSchema[] = [
  { code: "general", type: "heading", caption: "General" },
  { code: "ref", type: "str", caption: "Reference" },
  { code: "name", type: "str", caption: "Name" },
  { code: "rating", type: "heading", caption: "Rating" },
  { code: "sn_kva", type: "float", caption: "Rated power", unit: "kVA", decimal: 2 },
  { code: "cos_phi", type: "float", caption: "PF", decimal: 3, tooltip: "Power factor" },
  { code: "scaling", type: "float", caption: "DF", decimal: 2, tooltip: "Demand factor" },
  { code: "mode", type: "bool", caption: "Inductive ?" },
  { code: "in_service", type: "bool", caption: "In Service ?" },
  { code: "load_profile", type: "graph", caption: "Load Profile" },
];

export const mockLoadValues: Record<string, EuiFieldValue> = {
  ref: "L1",
  name: "Workshop lighting",
  sn_kva: 12.5,
  cos_phi: 0.8,
  scaling: 1,
  mode: true,
  in_service: true,
  load_profile: "load_prof_1",
};

export const mockMessages = [
  { severity: "warning", title: "Voltage drop above limit", text: "L1: 5.6 % (limit 5 %)" },
  { severity: "info", title: "Power flow converged", text: "4 iterations" },
] as const;
