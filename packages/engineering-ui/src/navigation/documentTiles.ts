// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
// Adapted from GEstimator modern/src/documents.ts at e4e4fb295899feda5253ba216613c70c1f256d4e

/** Two-letter tile code: first letters of the first two words, or the first two letters. */
export function documentCode(title: string): string {
  const words = title
    .replace(/\.[a-z0-9]{1,6}$/i, "")
    .trim()
    .split(/[\s\-_.]+/)
    .filter(Boolean);
  if (!words.length) return "–";
  if (words.length === 1) return words[0]!.slice(0, 2).toUpperCase();
  return (words[0]![0]! + words[1]![0]!).toUpperCase();
}

/** Stable colour index 1–8 from a seed string. */
export function documentColourIndex(seed: string): number {
  let hash = 0;
  for (let index = 0; index < seed.length; index++) hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  return (hash % 8) + 1;
}
