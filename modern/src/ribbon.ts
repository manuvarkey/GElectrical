// SPDX-License-Identifier: GPL-3.0-or-later
// Ribbon definition for the shell. Command ids map to handlers in useShell.
import type { EuiRibbonTab } from "@kavilgroup/engineering-ui";

export interface RibbonState {
  showLeft: boolean;
  showRight: boolean;
  showBottom: boolean;
  dark: boolean;
}

export function ribbonTabs(state: RibbonState): EuiRibbonTab[] {
  return [
    {
      id: "home",
      label: "Home",
      groups: [
        {
          id: "file",
          label: "File",
          commands: [
            { id: "new-sheet", label: "New sheet", icon: "file", shortcut: "Ctrl+N" },
            { id: "save", label: "Save", icon: "save", shortcut: "Ctrl+S" },
          ],
        },
        {
          id: "edit",
          label: "Edit",
          commands: [
            { id: "undo", label: "Undo", icon: "undo", shortcut: "Ctrl+Z" },
            { id: "redo", label: "Redo", icon: "redo", shortcut: "Ctrl+Shift+Z", disabled: true },
            { id: "copy", label: "Copy", icon: "copy", shortcut: "Ctrl+C" },
            { id: "paste", label: "Paste", icon: "paste", shortcut: "Ctrl+V" },
            { id: "delete", label: "Delete", icon: "trash", shortcut: "Delete", danger: true },
          ],
        },
      ],
    },
    {
      id: "insert",
      label: "Insert",
      groups: [
        {
          id: "elements",
          label: "Elements",
          commands: [
            { id: "insert-transformer", label: "Transformer", icon: "transformer" },
            { id: "insert-busbar", label: "Busbar", icon: "busbar" },
            { id: "insert-breaker", label: "Breaker", icon: "breaker" },
            { id: "insert-load", label: "Load", icon: "load" },
            { id: "wire", label: "Wire", icon: "cable", shortcut: "Ctrl+W" },
          ],
        },
      ],
    },
    {
      id: "analysis",
      label: "Analysis",
      groups: [
        {
          id: "run",
          label: "Run",
          commands: [
            { id: "power-flow", label: "Power flow", icon: "power-flow", tooltip: "Run a power flow (mock)" },
            { id: "short-circuit", label: "Short circuit", icon: "fault", tooltip: "Run a short circuit (mock)" },
            { id: "rules-check", label: "Rules check", icon: "check" },
          ],
        },
      ],
    },
    {
      id: "protection",
      label: "Protection",
      groups: [
        {
          id: "curves",
          label: "Curves",
          commands: [{ id: "coordination", label: "Coordination", icon: "protection" }],
        },
      ],
    },
    {
      id: "view",
      label: "View",
      groups: [
        {
          id: "panels",
          label: "Panels",
          commands: [
            { id: "toggle-left", label: "Components", icon: "panel-left", pressed: state.showLeft },
            { id: "toggle-right", label: "Inspector", icon: "panel", pressed: state.showRight },
            { id: "toggle-bottom", label: "Messages", icon: "panel-bottom", pressed: state.showBottom },
          ],
        },
        {
          id: "appearance",
          label: "Appearance",
          commands: [
            { id: "toggle-theme", label: state.dark ? "Light theme" : "Dark theme", icon: state.dark ? "sun" : "moon" },
            { id: "settings", label: "Settings", icon: "settings" },
          ],
        },
      ],
    },
  ];
}
