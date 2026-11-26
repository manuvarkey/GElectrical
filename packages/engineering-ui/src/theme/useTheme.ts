// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
// Adapted from GEstimator modern/src/appearance.ts at e4e4fb295899feda5253ba216613c70c1f256d4e
//
// Theme registration: the only global state EngineeringUI holds. Persisting the
// preference is the host's job (program settings), so nothing is stored here.

import { readonly, ref, watch, type Ref } from "vue";

export type EuiThemePreference = "light" | "dark" | "system";
export type EuiResolvedTheme = "light" | "dark";

export interface EuiFontSettings {
  /** Interface font family; empty uses the platform font. */
  family?: string;
  /** Interface font size in px (10–30); null or undefined uses 13 px. */
  size?: number | null;
  /** Table font family; empty follows the interface font. */
  tableFamily?: string;
  /** Table font size in px (10–30); null or undefined follows the interface size. */
  tableSize?: number | null;
}

export interface EuiThemeController {
  preference: Readonly<Ref<EuiThemePreference>>;
  resolved: Readonly<Ref<EuiResolvedTheme>>;
  setPreference(value: EuiThemePreference): void;
  /** Switch between light and dark (leaves "system"). */
  toggle(): void;
  setFonts(fonts: EuiFontSettings): void;
}

const preference = ref<EuiThemePreference>("system");
const resolved = ref<EuiResolvedTheme>("light");
let root: HTMLElement | undefined;
let media: MediaQueryList | undefined;
let started = false;

function systemTheme(): EuiResolvedTheme {
  return media?.matches ? "dark" : "light";
}

function apply() {
  resolved.value = preference.value === "system" ? systemTheme() : preference.value;
  if (root) root.dataset.theme = resolved.value;
}

function start(target?: HTMLElement) {
  if (target) root = target;
  if (started || typeof document === "undefined") return;
  started = true;
  root ??= document.documentElement;
  media = typeof matchMedia === "function" ? matchMedia("(prefers-color-scheme: dark)") : undefined;
  media?.addEventListener("change", apply);
  watch(preference, apply, { immediate: true });
}

/** Accepts only control-character-free names up to 120 characters. */
export function normalizeFontFamily(name: unknown): string {
  return typeof name === "string" && !/\p{Cc}/u.test(name) ? name.trim().slice(0, 120) : "";
}

/** Accepts finite sizes from 10 to 30 px; anything else means "default". */
export function normalizeFontSize(px: unknown): number | null {
  return typeof px === "number" && Number.isFinite(px) && px >= 10 && px <= 30 ? px : null;
}

function setFonts(fonts: EuiFontSettings) {
  if (!root) return;
  const style = root.style;
  const family = normalizeFontFamily(fonts.family);
  const size = normalizeFontSize(fonts.size);
  const tableFamily = normalizeFontFamily(fonts.tableFamily);
  const tableSize = normalizeFontSize(fonts.tableSize);
  // Empty values fall back to the defaults in tokens.css.
  style.setProperty("--eui-font-family", family ? `${JSON.stringify(family)}, system-ui, sans-serif` : "");
  style.setProperty("--eui-font-size", size ? `${size}px` : "");
  style.setProperty(
    "--eui-table-font-family",
    tableFamily ? `${JSON.stringify(tableFamily)}, var(--eui-font-family)` : "",
  );
  style.setProperty("--eui-table-font-size", tableSize ? `${tableSize}px` : "");
}

const controller: EuiThemeController = {
  preference: readonly(preference),
  resolved: readonly(resolved),
  setPreference(value) {
    preference.value = value;
  },
  toggle() {
    preference.value = resolved.value === "dark" ? "light" : "dark";
  },
  setFonts,
};

/**
 * Registers the theme on `root` (default: `document.documentElement`) and
 * returns the shared controller. Safe to call from any component.
 */
export function useTheme(options: { root?: HTMLElement; initial?: EuiThemePreference } = {}): EuiThemeController {
  if (options.initial && !started) preference.value = options.initial;
  start(options.root);
  return controller;
}

/**
 * Keeps Quasar's Dark plugin in step with the resolved theme. Pass Quasar's
 * `Dark` object; EngineeringUI does not import Quasar in this subpath.
 */
export function bindQuasarDark(dark: { set(value: boolean): void }): () => void {
  useTheme();
  return watch(resolved, (theme) => dark.set(theme === "dark"), { immediate: true });
}
