// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import EuiPropertyInspector from "../src/inspectors/EuiPropertyInspector.vue";
import { loadFields, loadValues } from "../stories/fixtures/fields";
import { mountEui } from "./helpers";

function setup(props: Record<string, unknown> = {}) {
  return mountEui(EuiPropertyInspector, { props: { fields: loadFields, values: loadValues, ...props } });
}

describe("EuiPropertyInspector", () => {
  it("renders one control per visible field type and hides disabled fields", () => {
    const wrapper = setup();
    expect(wrapper.findAll("h3").map((heading) => heading.text())).toEqual(["General", "Rating"]);
    expect(wrapper.find('[data-field="hidden"]').exists()).toBe(false);
    expect(wrapper.get<HTMLInputElement>('[data-field="sn_kva"] input').element.value).toBe("12.50");
    expect(wrapper.get<HTMLInputElement>('[data-field="phases"] input').element.value).toBe("3");
    expect(wrapper.get<HTMLInputElement>('[data-field="mode"] input[type="checkbox"]').element.checked).toBe(true);
    expect(wrapper.find('[data-field="notes"] textarea').exists()).toBe(true);
    expect(wrapper.get('[data-field="load_profile"]').text()).toContain("load_prof_1");
    expect(wrapper.get('[data-field="uid"] input').attributes("readonly")).toBeDefined();
  });

  it("labels controls from their captions", () => {
    const wrapper = setup();
    const input = wrapper.get('[data-field="sn_kva"] input');
    const label = wrapper.get(`label[for="${input.attributes("id")}"]`);
    expect(label.text()).toBe("Rated power (kVA)");
    const checkbox = wrapper.get('[data-field="mode"] input[type="checkbox"]');
    expect(wrapper.get(`label[for="${checkbox.attributes("id")}"]`).text()).toBe("Inductive");
  });

  it("emits committed text, numbers, booleans and edit requests", async () => {
    const wrapper = setup();
    const power = wrapper.get('[data-field="sn_kva"] input');
    await power.setValue("15");
    await power.trigger("keydown", { key: "Enter" });
    const name = wrapper.get('[data-field="name"] input');
    await name.setValue("Office");
    await name.trigger("keydown", { key: "Enter" });
    await wrapper.get('[data-field="mode"] input[type="checkbox"]').setValue(false);
    await wrapper.get('[data-field="load_profile"] button').trigger("click");
    expect(wrapper.emitted("change")).toEqual([
      [{ code: "sn_kva", value: "15", number: 15 }],
      [{ code: "name", value: "Office" }],
      [{ code: "mode", value: false }],
    ]);
    expect(wrapper.emitted("edit")).toEqual([["load_profile"]]);
  });

  it("shows host errors, mixed values and read-only state", () => {
    const wrapper = setup({ errors: { sn_kva: "Must be positive" }, mixed: ["name", "mode"], readonly: true });
    expect(wrapper.get('[data-field="sn_kva"]').text()).toContain("Must be positive");
    expect(wrapper.get('[data-field="name"] input').attributes("placeholder")).toBe("Multiple values");
    expect(wrapper.get<HTMLInputElement>('[data-field="mode"] input[type="checkbox"]').element.indeterminate).toBe(
      true,
    );
    expect(wrapper.get('[data-field="name"] input').attributes("readonly")).toBeDefined();
  });

  it("filters fields by caption", async () => {
    const wrapper = setup({ filterable: true });
    await wrapper.get('input[type="search"]').setValue("power");
    expect(wrapper.findAll("[data-field]").map((row) => row.attributes("data-field"))).toEqual(["sn_kva"]);
    await wrapper.get('input[type="search"]').setValue("zzz");
    expect(wrapper.text()).toContain("No matching properties");
  });
});
