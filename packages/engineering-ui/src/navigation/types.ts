// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
import type { EuiIconName } from "../icons/iconPaths";

export interface EuiRibbonCommand {
  id: string;
  /** Short caption under the icon; also the accessible name. */
  label: string;
  icon: EuiIconName;
  /** Explanatory tooltip. */
  tooltip?: string;
  /** Display form of the shortcut, for example "Ctrl+S". */
  shortcut?: string;
  disabled?: boolean;
  /** Present for toggle commands; reflects the on/off state. */
  pressed?: boolean;
  /** Destructive command (danger colour, with its label kept). */
  danger?: boolean;
  /** Never collapse to an icon-only button when space runs out. */
  keepLabel?: boolean;
}

export interface EuiRibbonGroup {
  id: string;
  label: string;
  commands: EuiRibbonCommand[];
}

export interface EuiRibbonTab {
  id: string;
  label: string;
  groups: EuiRibbonGroup[];
  /** Contextual tab (for example a selected element type); shown with an accent. */
  contextual?: boolean;
}

export interface EuiDocumentItem {
  id: string;
  title: string;
  /** File path shown in the flyout; omitted for unsaved documents. */
  path?: string;
  dirty?: boolean;
  /** Tile colour index 1–8; derived from the id when omitted. */
  colour?: number;
}
