// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
//
// Display formatting and plain-number parsing for numeric inputs. No
// engineering validation happens here: anything that is not a plain number
// (for example arithmetic such as "2*1.5") is passed to the host as text.

const plainNumber = /^[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?$/i;

/** Formats `value` with `decimal` places; empty for null/undefined/non-finite. */
export function formatNumber(value: number | null | undefined, decimal?: number): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "";
  if (decimal === undefined || decimal < 0) return String(value);
  return value.toFixed(Math.min(20, Math.floor(decimal)));
}

/** Raw editing text: the full-precision value, unrounded. */
export function rawNumberText(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value) ? "" : String(value);
}

/** Parses a plain decimal number (dot separator, optional exponent); null otherwise. */
export function parsePlainNumber(text: string): number | null {
  const trimmed = text.trim();
  if (!plainNumber.test(trimmed)) return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : null;
}
