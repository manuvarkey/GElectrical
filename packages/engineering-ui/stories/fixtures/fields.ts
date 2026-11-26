// SPDX-License-Identifier: MIT
// Mock field schema in the backend FieldSchema shape (an electrical load).
import type { EuiFieldSchema, EuiFieldValue } from "../../src/inspectors/types";

export const loadFields: EuiFieldSchema[] = [
  { code: "general", type: "heading", caption: "General" },
  { code: "ref", type: "str", caption: "Reference", tooltip: "Unique reference shown on the drawing" },
  { code: "name", type: "str", caption: "Name" },
  { code: "notes", type: "multiline_str", caption: "Notes" },
  { code: "rating", type: "heading", caption: "Rating" },
  { code: "sn_kva", type: "float", caption: "Rated power", unit: "kVA", decimal: 2 },
  { code: "cos_phi", type: "float", caption: "PF", decimal: 3, tooltip: "Power factor" },
  { code: "scaling", type: "float", caption: "DF", decimal: 2, tooltip: "Demand factor" },
  { code: "phases", type: "int", caption: "Phases" },
  { code: "type", type: "str", caption: "Connection type", selection_list: ["wye", "delta"] },
  { code: "mode", type: "bool", caption: "Inductive" },
  { code: "in_service", type: "bool", caption: "In service" },
  { code: "load_profile", type: "graph", caption: "Load profile", editable: true },
  { code: "uid", type: "str", caption: "Internal id", editable: false },
  { code: "hidden", type: "str", caption: "Hidden field", enabled: false },
];

export const loadValues: Record<string, EuiFieldValue> = {
  ref: "L1",
  name: "Workshop lighting",
  notes: "",
  sn_kva: 12.5,
  cos_phi: 0.8,
  scaling: 1,
  phases: 3,
  type: "wye",
  mode: true,
  in_service: true,
  load_profile: "load_prof_1",
  uid: "e3b0c442",
  hidden: "x",
};

/** A long schema for scrolling and filtering checks. */
export const manyFields: EuiFieldSchema[] = Array.from({ length: 120 }, (_, index) => ({
  code: `f${index}`,
  type: index % 10 === 0 ? "heading" : "float",
  caption: index % 10 === 0 ? `Group ${index / 10 + 1}` : `Parameter ${index}`,
  unit: index % 3 === 0 ? "A" : "V",
  decimal: 2,
}));

export const manyValues: Record<string, EuiFieldValue> = Object.fromEntries(
  manyFields.map((field, index) => [field.code, index * 1.5]),
);
