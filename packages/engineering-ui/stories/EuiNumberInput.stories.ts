// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import { expect, fn, userEvent, within } from "storybook/test";
import EuiNumberInput from "../src/controls/EuiNumberInput.vue";

const meta = {
  title: "Controls/EuiNumberInput",
  component: EuiNumberInput,
  args: { modelValue: 12.5, label: "Rated power", unit: "kVA", decimal: 2, onCommit: fn(), onRevert: fn() },
  render: (args) => ({
    components: { EuiNumberInput },
    setup() {
      const value = ref(args.modelValue);
      return { args, value };
    },
    template: '<div style="width:220px"><EuiNumberInput v-bind="args" v-model="value" /></div>',
  }),
} satisfies Meta<typeof EuiNumberInput>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };
export const Disabled: Story = { args: { disabled: true } };
export const ReadOnly: Story = { args: { readonly: true } };
export const ValidationError: Story = { args: { error: "Rated power must be greater than 0" } };
export const ValidationErrorDark: Story = { ...ValidationError, globals: { theme: "dark" } };
export const MultipleValues: Story = { args: { mixed: true } };
export const Percent: Story = { args: { modelValue: 0.85, label: "Loading", unit: "%", decimal: 1 } };
export const NoUnit: Story = { args: { modelValue: 0.8, label: "Power factor", unit: "", decimal: 3 } };
export const Narrow: Story = {
  render: (args) => ({
    components: { EuiNumberInput },
    setup: () => ({ args }),
    template: '<div style="width:96px"><EuiNumberInput v-bind="args" /></div>',
  }),
};

export const Keyboard: Story = {
  play: async ({ canvasElement, args }) => {
    const input = within(canvasElement).getByRole("textbox", { name: "Rated power (kVA)" });
    await expect(input).toHaveValue("12.50");
    await userEvent.click(input);
    await expect(input).toHaveValue("12.5");
    await userEvent.clear(input);
    await userEvent.type(input, "2*7.5{Enter}");
    await expect(args.onCommit).toHaveBeenCalledWith({ text: "2*7.5", value: null });
    await userEvent.clear(input);
    await userEvent.type(input, "99{Escape}");
    await expect(args.onRevert).toHaveBeenCalled();
    await userEvent.clear(input);
    await userEvent.type(input, "15{Enter}");
    await expect(args.onCommit).toHaveBeenLastCalledWith({ text: "15", value: 15 });
    await userEvent.tab();
    await expect(input).toHaveValue("15.00");
  },
};
