// SPDX-License-Identifier: GPL-3.0-or-later
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { Quasar } from "quasar";
import App from "./App.vue";

function mountApp() {
  const host = document.createElement("div");
  document.body.append(host);
  return mount(App, { attachTo: host, global: { plugins: [[Quasar, {}]] } });
}

describe("App shell (mock data)", () => {
  it("composes ribbon, rail, palette, inspector, messages and status bar", () => {
    const wrapper = mountApp();
    expect(wrapper.find('[role="tablist"][aria-label="GElectrical ribbon"]').exists()).toBe(true);
    expect(wrapper.find('nav[aria-label="Open projects"]').text()).toContain("Main substation");
    expect(wrapper.find('aside[aria-label="Components"]').text()).toContain("Transformer");
    expect(wrapper.find('section[aria-label="Properties of L1"]').exists()).toBe(true);
    expect(wrapper.find('section[aria-label="Messages"]').text()).toContain("Voltage drop above limit");
    expect(wrapper.find('footer[aria-label="Status bar"]').text()).toContain("1 element selected");
    wrapper.unmount();
  });

  it("toggles panels from the View tab and marks edits dirty", async () => {
    const wrapper = mountApp();
    await wrapper.get('[role="tab"]:nth-child(5)').trigger("click");
    await wrapper.get('[data-command="toggle-bottom"]').trigger("click");
    expect(wrapper.find('section[aria-label="Messages"]').exists()).toBe(false);
    const name = wrapper.get('[data-field="name"] input');
    await name.setValue("Office");
    await name.trigger("keydown", { key: "Enter" });
    await nextTick();
    expect(wrapper.get('[role="status"]').text()).toBe("Changed name");
    expect(wrapper.find('[data-status="dirty"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it("shows the mock backend message for expressions", async () => {
    const wrapper = mountApp();
    const power = wrapper.get('[data-field="sn_kva"] input');
    await power.setValue("2*5");
    await power.trigger("keydown", { key: "Enter" });
    await nextTick();
    expect(wrapper.get('[data-field="sn_kva"]').text()).toContain("Expressions need the backend");
    expect((power.element as HTMLInputElement).value).toBe("2*5");
    wrapper.unmount();
  });
});
