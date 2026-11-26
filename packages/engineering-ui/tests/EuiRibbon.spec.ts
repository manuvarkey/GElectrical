// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import EuiRibbon from "../src/navigation/EuiRibbon.vue";
import type { EuiRibbonTab } from "../src/navigation/types";
import { mountEui } from "./helpers";

const tabs: EuiRibbonTab[] = [
  {
    id: "home",
    label: "Home",
    groups: [
      {
        id: "file",
        label: "File",
        commands: [
          { id: "save", label: "Save", icon: "save", shortcut: "Ctrl+S" },
          { id: "undo", label: "Undo", icon: "undo", disabled: true },
          { id: "grid", label: "Grid", icon: "grid", pressed: true },
        ],
      },
    ],
  },
  {
    id: "analysis",
    label: "Analysis",
    groups: [{ id: "run", label: "Run", commands: [{ id: "pf", label: "Power flow", icon: "power-flow" }] }],
  },
];

describe("EuiRibbon", () => {
  it("switches tabs with arrow keys and keeps one tab stop", async () => {
    const wrapper = mountEui(EuiRibbon, { props: { tabs, modelValue: "home" } });
    const tabButtons = wrapper.findAll('[role="tab"]');
    expect(tabButtons.map((tab) => tab.attributes("tabindex"))).toEqual(["0", "-1"]);
    await tabButtons[0]!.trigger("keydown", { key: "ArrowRight" });
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual(["analysis"]);
    await wrapper.setProps({ modelValue: "analysis" });
    expect(wrapper.find('[role="tabpanel"]').text()).toContain("Power flow");
  });

  it("emits enabled commands only and exposes toggle and shortcut state", async () => {
    const wrapper = mountEui(EuiRibbon, { props: { tabs, modelValue: "home" } });
    const save = wrapper.get('[data-command="save"]');
    expect(save.attributes("aria-keyshortcuts")).toBe("Control+S");
    expect(save.attributes("title")).toBe("Save (Ctrl+S)");
    expect(wrapper.get('[data-command="grid"]').attributes("aria-pressed")).toBe("true");
    await save.trigger("click");
    await wrapper.get('[data-command="undo"]').trigger("click");
    expect(wrapper.emitted("command")).toEqual([["save"]]);
  });

  it("moves focus between enabled commands, skipping disabled ones", async () => {
    const wrapper = mountEui(EuiRibbon, { props: { tabs, modelValue: "home" } });
    const save = wrapper.get<HTMLButtonElement>('[data-command="save"]');
    save.element.focus();
    await save.trigger("keydown", { key: "ArrowRight" });
    expect(document.activeElement?.getAttribute("data-command")).toBe("grid");
    await nextTick();
    expect(wrapper.get('[data-command="grid"]').attributes("tabindex")).toBe("0");
  });

  it("disables every command while busy", () => {
    const wrapper = mountEui(EuiRibbon, { props: { tabs, modelValue: "home", busy: true } });
    expect(wrapper.findAll(".eui-ribbon__command").every((button) => button.attributes("disabled") !== undefined)).toBe(
      true,
    );
  });
});
