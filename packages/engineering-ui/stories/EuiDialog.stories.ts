// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import EuiDialog from "../src/dialogs/EuiDialog.vue";
import EuiNumberInput from "../src/controls/EuiNumberInput.vue";

const meta = {
  title: "Dialogs/EuiDialog",
  component: EuiDialog,
  args: {
    modelValue: true,
    title: "Analysis options",
    applyLabel: "Run",
    busy: false,
    onApply: fn(),
    onCancel: fn(),
  },
  parameters: { a11y: { context: "body" } },
  render: (args) => ({
    components: { EuiDialog, EuiNumberInput },
    setup() {
      const open = ref(args.modelValue);
      const tolerance = ref(0.001);
      const iterations = ref(20);
      return { args, open, tolerance, iterations };
    },
    template: `
      <button type="button" @click="open = true">Open dialog</button>
      <EuiDialog v-bind="args" v-model="open">
        <template #description>Settings for the next power flow run.</template>
        <div style="display:grid;grid-template-columns:auto 160px;gap:6px 12px;align-items:center">
          <label for="dlg-tol">Tolerance</label>
          <EuiNumberInput id="dlg-tol" v-model="tolerance" unit="MVA" />
          <label for="dlg-iter">Maximum iterations</label>
          <EuiNumberInput id="dlg-iter" v-model="iterations" :decimal="0" />
        </div>
      </EuiDialog>`,
  }),
} satisfies Meta<typeof EuiDialog>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };
export const Busy: Story = { args: { busy: true } };
export const ApplyDisabled: Story = { args: { applyDisabled: true } };
export const ValidationError: Story = {
  render: (args) => ({
    components: { EuiDialog, EuiNumberInput },
    setup: () => ({ args }),
    template: `
      <EuiDialog v-bind="args" title="Renumber elements" apply-label="Renumber" apply-disabled>
        <label for="dlg-start">Start number</label>
        <EuiNumberInput id="dlg-start" :model-value="0" :decimal="0" error="Start number must be at least 1" />
      </EuiDialog>`,
  }),
};
export const Narrow: Story = { args: { width: 280 } };

export const Keyboard: Story = {
  play: async ({ args }) => {
    const body = within(document.body);
    const dialog = await body.findByRole("dialog", { name: "Analysis options" });
    // Focus moves into the dialog.
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
    const tolerance = within(dialog).getByRole("textbox", { name: "Tolerance" });
    await userEvent.click(tolerance);
    await userEvent.keyboard("{Enter}");
    await expect(args.onApply).toHaveBeenCalledTimes(1);
    await userEvent.keyboard("{Escape}");
    await expect(args.onCancel).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(body.queryByRole("dialog")).toBeNull());
  },
};
