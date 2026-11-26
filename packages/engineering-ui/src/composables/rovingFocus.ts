// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
//
// Keyboard helpers for composite widgets with one tab stop (toolbars, tab
// strips, rails). The caller owns the DOM; these helpers only pick indices.

export type EuiOrientation = "horizontal" | "vertical";

/**
 * Returns the index to focus for a navigation key, or -1 when the key is not
 * a navigation key. Wraps at both ends; Home and End jump to the ends.
 */
export function nextRovingIndex(key: string, index: number, count: number, orientation: EuiOrientation): number {
  if (count <= 0) return -1;
  const forward = orientation === "horizontal" ? "ArrowRight" : "ArrowDown";
  const backward = orientation === "horizontal" ? "ArrowLeft" : "ArrowUp";
  if (key === forward) return (index + 1) % count;
  if (key === backward) return (index - 1 + count) % count;
  if (key === "Home") return 0;
  if (key === "End") return count - 1;
  return -1;
}

/**
 * Moves focus among `items` for a navigation key. Returns the focused index,
 * or -1 if the event was not handled (the caller then lets it propagate).
 */
export function moveRovingFocus(
  event: KeyboardEvent,
  items: readonly HTMLElement[],
  orientation: EuiOrientation,
): number {
  const current = items.findIndex((item) => item === event.target || item.contains(event.target as Node));
  const next = nextRovingIndex(event.key, Math.max(0, current), items.length, orientation);
  if (next < 0) return -1;
  event.preventDefault();
  items[next]?.focus();
  return next;
}
