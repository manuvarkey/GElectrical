// SPDX-License-Identifier: MIT
import type { EuiRibbonTab } from "../../src/navigation/types";

export const ribbonTabs: EuiRibbonTab[] = [
  {
    id: "home",
    label: "Home",
    groups: [
      {
        id: "file",
        label: "File",
        commands: [
          { id: "new", label: "New sheet", icon: "file", shortcut: "Ctrl+N", tooltip: "Add a drawing sheet" },
          { id: "open", label: "Open", icon: "folder", shortcut: "Ctrl+O" },
          { id: "save", label: "Save", icon: "save", shortcut: "Ctrl+S" },
        ],
      },
      {
        id: "edit",
        label: "Edit",
        commands: [
          { id: "undo", label: "Undo", icon: "undo", shortcut: "Ctrl+Z" },
          { id: "redo", label: "Redo", icon: "redo", shortcut: "Ctrl+Shift+Z", disabled: true },
          { id: "cut", label: "Cut", icon: "cut", shortcut: "Ctrl+X" },
          { id: "copy", label: "Copy", icon: "copy", shortcut: "Ctrl+C" },
          { id: "paste", label: "Paste", icon: "paste", shortcut: "Ctrl+V" },
          { id: "delete", label: "Delete", icon: "trash", shortcut: "Delete", danger: true },
        ],
      },
      {
        id: "view",
        label: "View",
        commands: [
          { id: "grid", label: "Show grid", icon: "grid", pressed: true },
          { id: "zoom-in", label: "Zoom in", icon: "zoom-in", shortcut: "Ctrl++" },
          { id: "zoom-out", label: "Zoom out", icon: "zoom-out", shortcut: "Ctrl+-" },
        ],
      },
    ],
  },
  {
    id: "insert",
    label: "Insert",
    groups: [
      {
        id: "sources",
        label: "Sources",
        commands: [
          { id: "grid-source", label: "Grid supply", icon: "generator" },
          { id: "transformer", label: "Transformer", icon: "transformer" },
        ],
      },
      {
        id: "distribution",
        label: "Distribution",
        commands: [
          { id: "busbar", label: "Busbar", icon: "busbar" },
          { id: "breaker", label: "Circuit breaker", icon: "breaker" },
          { id: "cable", label: "Cable", icon: "cable", shortcut: "Ctrl+W" },
          { id: "load", label: "Load", icon: "load" },
          { id: "ground", label: "Earth", icon: "ground" },
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
          { id: "power-flow", label: "Power flow", icon: "power-flow", tooltip: "Run a load flow on the network" },
          { id: "short-circuit", label: "Short circuit", icon: "fault" },
          { id: "rules", label: "Rules check", icon: "check" },
        ],
      },
    ],
  },
  {
    id: "protection",
    label: "Protection",
    groups: [
      { id: "curves", label: "Curves", commands: [{ id: "coordination", label: "Coordination", icon: "protection" }] },
    ],
  },
  {
    id: "selection",
    label: "Transformer",
    contextual: true,
    groups: [
      { id: "element", label: "Element", commands: [{ id: "properties", label: "Properties", icon: "settings" }] },
    ],
  },
];
