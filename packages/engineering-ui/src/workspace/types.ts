// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
import type { EuiIconName } from "../icons/iconPaths";

export type EuiTone = "neutral" | "info" | "success" | "warning" | "danger";

export interface EuiStatusItem {
  id: string;
  text: string;
  /** Tooltip with more detail. */
  title?: string;
  icon?: EuiIconName;
  tone?: EuiTone;
  /** Items default to the start (left) side. */
  align?: "start" | "end";
}

export interface EuiNotification {
  id: string;
  tone: Exclude<EuiTone, "neutral">;
  title: string;
  text?: string;
  /** Optional actions shown as buttons; reported by id. */
  actions?: { id: string; label: string }[];
}

/** Sizes of the collapsible side panels in px; 0 or less hides nothing (use the visibility props). */
export interface EuiWorkspaceSizes {
  left: number;
  right: number;
  bottom: number;
}
