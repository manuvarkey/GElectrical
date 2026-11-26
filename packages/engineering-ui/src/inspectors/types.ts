// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
//
// Field schema for schema-driven inspectors. The shape follows the backend
// FieldSchema contract (snake_case keys) so hosts can pass it unchanged.

export type EuiFieldType = "int" | "float" | "str" | "multiline_str" | "bool" | "font" | "graph" | "data" | "heading";

export interface EuiFieldSchema {
  code: string;
  type: EuiFieldType;
  caption: string;
  unit?: string;
  /** Display precision for numbers. */
  decimal?: number;
  /** Allowed values; renders a selector. */
  selection_list?: string[] | null;
  /** Images per selection entry (not rendered yet). */
  selection_images?: string[] | null;
  /** false hides the field. */
  enabled?: boolean;
  /** false shows the field read-only. */
  editable?: boolean;
  /** Shown while an element is being placed (host concern; ignored here). */
  floating?: boolean;
  tooltip?: string;
  /** Changing this field changes the field structure (host refetches; ignored here). */
  alter_structure?: boolean;
}

export type EuiFieldValue = string | number | boolean | null;

export interface EuiFieldChange {
  code: string;
  /** Committed value: number text as typed for int/float, string, or boolean. */
  value: string | boolean;
  /** Parsed number for int/float when the text is a plain number. */
  number?: number | null;
}
