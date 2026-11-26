// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { nextTick } from "vue";
import EuiDialog from "../src/dialogs/EuiDialog.vue";
import { mountEui } from "./helpers";

async function open(props: Record<string, unknown> = {}) {
  const wrapper = mountEui(EuiDialog, {
    props: { modelValue: true, title: "Analysis options", applyLabel: "Run", ...props },
    slots: { default: '<input aria-label="Tolerance" class="field" /><textarea aria-label="Notes"></textarea>' },
  });
  await nextTick();
  await nextTick();
  const dialog = document.querySelector<HTMLElement>('[role="dialog"]')!;
  return { wrapper, dialog };
}

describe("EuiDialog", () => {
  it("is a labelled modal dialog", async () => {
    const { dialog, wrapper } = await open();
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(document.getElementById(dialog.getAttribute("aria-labelledby")!)?.textContent).toBe("Analysis options");
    wrapper.unmount();
  });

  it("applies on Enter in a field but not in a multi-line field", async () => {
    const { dialog, wrapper } = await open();
    dialog.querySelector("input")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    dialog.querySelector("textarea")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(wrapper.emitted("apply")).toHaveLength(1);
    wrapper.unmount();
  });

  it("cancels on Escape", async () => {
    const { dialog, wrapper } = await open();
    dialog.querySelector("input")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    expect(wrapper.emitted("cancel")).toHaveLength(1);
    wrapper.unmount();
  });

  it("cancels from the close button and blocks everything while busy", async () => {
    const { dialog, wrapper } = await open();
    dialog.querySelector<HTMLButtonElement>(".eui-dialog__close")!.click();
    expect(wrapper.emitted("cancel")).toHaveLength(1);
    expect(wrapper.emitted("update:modelValue")?.[0]).toEqual([false]);
    wrapper.unmount();

    const busy = await open({ busy: true });
    busy.dialog.querySelector<HTMLButtonElement>(".eui-dialog__close")!.click();
    busy.dialog.querySelector("input")!.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    expect(busy.wrapper.emitted("cancel")).toBeUndefined();
    expect(busy.wrapper.emitted("apply")).toBeUndefined();
    busy.wrapper.unmount();
  });
});
