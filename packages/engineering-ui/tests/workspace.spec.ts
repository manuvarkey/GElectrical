// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import EuiWorkspace from "../src/workspace/EuiWorkspace.vue";
import EuiStatusBar from "../src/workspace/EuiStatusBar.vue";
import EuiNotifications from "../src/workspace/EuiNotifications.vue";
import { mountEui } from "./helpers";

describe("EuiWorkspace", () => {
  it("resizes panels from the keyboard within limits", async () => {
    const wrapper = mountEui(EuiWorkspace, {
      props: { sizes: { left: 240, right: 300, bottom: 180 }, showBottom: true },
      slots: { left: "<p>Palette</p>", default: "<p>Canvas</p>", right: "<p>Inspector</p>", bottom: "<p>Log</p>" },
    });
    const separators = wrapper.findAll('[role="separator"]');
    expect(separators).toHaveLength(3);
    expect(separators[0]!.attributes("aria-valuenow")).toBe("240");
    await separators[0]!.trigger("keydown", { key: "ArrowRight" });
    await separators[1]!.trigger("keydown", { key: "ArrowRight", shiftKey: true });
    await separators[2]!.trigger("keydown", { key: "End" });
    const updates = wrapper.emitted("update:sizes") as [{ left: number; right: number; bottom: number }][];
    expect(updates[0]![0].left).toBe(256);
    expect(updates[1]![0].right).toBe(236);
    expect(updates[2]![0].bottom).toBe(480);
  });

  it("hides collapsed panels and their splitters", () => {
    const wrapper = mountEui(EuiWorkspace, {
      props: { showLeft: false, showRight: true },
      slots: { left: "<p>Palette</p>", default: "<p>Canvas</p>", right: "<p>Inspector</p>" },
    });
    expect(wrapper.text()).not.toContain("Palette");
    expect(wrapper.findAll('[role="separator"]')).toHaveLength(1);
    expect(wrapper.find("main").text()).toBe("Canvas");
  });
});

describe("EuiStatusBar", () => {
  it("places items and announces the notice or busy text", async () => {
    const wrapper = mountEui(EuiStatusBar, {
      props: {
        items: [
          { id: "sel", text: "2 selected" },
          { id: "zoom", text: "100 %", align: "end" },
        ],
        notice: "Copied",
      },
    });
    expect(wrapper.get(".eui-statusbar__side--end").text()).toContain("100 %");
    expect(wrapper.get('[role="status"]').text()).toBe("Copied");
    await wrapper.setProps({ busy: "Running power flow" });
    expect(wrapper.get('[role="status"]').text()).toBe("Running power flow");
  });
});

describe("EuiNotifications", () => {
  it("labels tone in text, alerts errors and emits dismiss and actions", async () => {
    const wrapper = mountEui(EuiNotifications, {
      props: {
        items: [
          { id: "1", tone: "danger", title: "Analysis failed", actions: [{ id: "log", label: "Show log" }] },
          { id: "2", tone: "success", title: "Saved" },
        ],
      },
    });
    const notices = wrapper.findAll(".eui-notice");
    expect(notices[0]!.get(".eui-notice__body").attributes("role")).toBe("alert");
    expect(notices[0]!.text()).toContain("Error: Analysis failed");
    expect(notices[1]!.find('[role="alert"]').exists()).toBe(false);
    await notices[0]!.get(".eui-notice__action").trigger("click");
    await notices[1]!.get(".eui-notice__dismiss").trigger("click");
    expect(wrapper.emitted("action")).toEqual([["1", "log"]]);
    expect(wrapper.emitted("dismiss")).toEqual([["2"]]);
  });
});
