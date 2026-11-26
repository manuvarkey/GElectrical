// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import EuiNumberInput from "../src/controls/EuiNumberInput.vue";
import { mountEui } from "./helpers";

/** Quasar reports blur after a zero-delay timeout. */
async function blur(element: HTMLElement) {
  element.blur();
  await new Promise((resolve) => setTimeout(resolve, 5));
  await nextTick();
}

function setup(props: Record<string, unknown> = {}) {
  const wrapper = mountEui(EuiNumberInput, {
    props: { modelValue: 0.8, decimal: 2, unit: "kVA", label: "Rated power", ...props },
  });
  return { wrapper, input: wrapper.get("input") };
}

describe("EuiNumberInput", () => {
  it("shows the formatted value, the unit and an accessible name", () => {
    const { wrapper, input } = setup({ modelValue: 0.123456 });
    expect(input.element.value).toBe("0.12");
    expect(input.attributes("aria-label")).toBe("Rated power (kVA)");
    expect(wrapper.text()).toContain("kVA");
  });

  it("shows the raw value while focused", async () => {
    const { input } = setup({ modelValue: 0.123456 });
    (input.element as HTMLInputElement).focus();
    await nextTick();
    expect(input.element.value).toBe("0.123456");
  });

  it("commits plain numbers with Enter", async () => {
    const { wrapper, input } = setup();
    await input.setValue("1.25");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("commit")?.[0]).toEqual([{ text: "1.25", value: 1.25 }]);
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([1.25]);
  });

  it("passes expressions to the host as text without a value", async () => {
    const { wrapper, input } = setup();
    (input.element as HTMLInputElement).focus();
    await input.setValue("2*0.4");
    await blur(input.element as HTMLInputElement);
    expect(wrapper.emitted("commit")?.[0]).toEqual([{ text: "2*0.4", value: null }]);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("keeps rejected text with the host message until the value changes", async () => {
    const { wrapper, input } = setup();
    await input.setValue("-5");
    await input.trigger("keydown", { key: "Enter" });
    await wrapper.setProps({ error: "Rated power must be positive" });
    expect(input.element.value).toBe("-5");
    expect(input.attributes("aria-invalid")).toBe("true");
    expect(wrapper.text()).toContain("Rated power must be positive");
    await wrapper.setProps({ modelValue: 2, error: "" });
    expect(input.element.value).toBe("2.00");
  });

  it("reverts with Escape and does not commit unchanged text", async () => {
    const { wrapper, input } = setup();
    await input.setValue("9");
    await input.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("revert")).toHaveLength(1);
    expect(input.element.value).toBe("0.80");
    (input.element as HTMLInputElement).focus();
    await input.setValue("0.8");
    await blur(input.element as HTMLInputElement);
    expect(wrapper.emitted("commit")).toBeUndefined();
  });

  it("does not commit when read-only and shows the mixed placeholder", async () => {
    const { wrapper, input } = setup({ readonly: true, mixed: true });
    expect(input.attributes("placeholder")).toBe("Multiple values");
    await input.setValue("3");
    await input.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("commit")).toBeUndefined();
  });
});
