// SPDX-License-Identifier: GPL-3.0-or-later
// Shell view state and mock command handling for M6. In M9 commands go to
// the Python backend through services/; this composable keeps only view state.
import { computed, ref } from "vue";
import { createNotificationQueue } from "@kavilgroup/engineering-ui/workspace";
import { useTheme } from "@kavilgroup/engineering-ui/theme";
import type { EuiFieldChange, EuiFieldValue, EuiStatusItem } from "@kavilgroup/engineering-ui";
import { mockDocuments, mockLoadValues } from "../mock/project";
import { ribbonTabs } from "../ribbon";

export function useShell() {
  const theme = useTheme();
  const documents = ref(mockDocuments.map((item) => ({ ...item })));
  const activeDocument = ref(documents.value[0]?.id ?? "");
  const activeTab = ref("home");
  const panels = ref({ showLeft: true, showRight: true, showBottom: true });
  const sizes = ref({ left: 220, right: 300, bottom: 140 });
  const values = ref<Record<string, EuiFieldValue | undefined>>({ ...mockLoadValues });
  const errors = ref<Record<string, string>>({});
  const notice = ref("");
  const busy = ref("");
  const settingsOpen = ref(false);
  const notifications = createNotificationQueue();
  let untitled = 1;

  const tabs = computed(() => ribbonTabs({ ...panels.value, dark: theme.resolved.value === "dark" }));
  const statusItems = computed<EuiStatusItem[]>(() => [
    { id: "selection", text: "1 element selected: L1" },
    { id: "coords", text: "X 120  Y 340", align: "end" },
    { id: "zoom", text: "100 %", align: "end" },
    ...(documents.value.find((item) => item.id === activeDocument.value)?.dirty
      ? [
          {
            id: "dirty",
            text: "Unsaved changes",
            align: "end" as const,
            tone: "warning" as const,
            icon: "warning" as const,
          },
        ]
      : []),
  ]);

  function markDirty() {
    documents.value = documents.value.map((item) =>
      item.id === activeDocument.value ? { ...item, dirty: true } : item,
    );
  }

  function runMock(label: string, title: string) {
    busy.value = label;
    setTimeout(() => {
      busy.value = "";
      notifications.notify({ tone: "success", title, text: "Mock result: no backend in M6." });
    }, 600);
  }

  function command(id: string) {
    switch (id) {
      case "toggle-left":
        panels.value.showLeft = !panels.value.showLeft;
        break;
      case "toggle-right":
        panels.value.showRight = !panels.value.showRight;
        break;
      case "toggle-bottom":
        panels.value.showBottom = !panels.value.showBottom;
        break;
      case "toggle-theme":
        theme.toggle();
        break;
      case "settings":
        settingsOpen.value = true;
        break;
      case "power-flow":
        runMock("Running power flow…", "Power flow finished");
        break;
      case "short-circuit":
        runMock("Running short circuit…", "Short circuit finished");
        break;
      case "save":
        documents.value = documents.value.map((item) =>
          item.id === activeDocument.value ? { ...item, dirty: false } : item,
        );
        notice.value = "Saved (mock)";
        break;
      default:
        notice.value = `Command "${id}" is not connected in the M6 shell`;
    }
  }

  /** Mock stand-in for the backend: accepts plain numbers and text; real validation comes from Python. */
  function changeField(change: EuiFieldChange) {
    const next = { ...errors.value };
    delete next[change.code];
    if (typeof change.value === "string" && change.number === null) {
      next[change.code] = "Expressions need the backend (not available in the M6 mock)";
      errors.value = next;
      return;
    }
    errors.value = next;
    values.value = { ...values.value, [change.code]: change.number ?? change.value };
    markDirty();
    notice.value = `Changed ${change.code}`;
  }

  function addDocument() {
    const id = `doc-new-${untitled++}`;
    documents.value = [...documents.value, { id, title: "" }];
    activeDocument.value = id;
  }

  function closeDocument(id: string) {
    const index = documents.value.findIndex((item) => item.id === id);
    documents.value = documents.value.filter((item) => item.id !== id);
    if (activeDocument.value === id) activeDocument.value = documents.value[Math.max(0, index - 1)]?.id ?? "";
  }

  return {
    theme,
    documents,
    activeDocument,
    activeTab,
    panels,
    sizes,
    values,
    errors,
    notice,
    busy,
    settingsOpen,
    notifications,
    tabs,
    statusItems,
    command,
    changeField,
    addDocument,
    closeDocument,
  };
}
