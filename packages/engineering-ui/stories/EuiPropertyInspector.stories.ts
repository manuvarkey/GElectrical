// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import { expect, fn, userEvent, within } from "storybook/test";
import EuiPropertyInspector from "../src/inspectors/EuiPropertyInspector.vue";
import type { EuiFieldChange, EuiFieldValue } from "../src/inspectors/types";
import { loadFields, loadValues, manyFields, manyValues } from "./fixtures/fields";

const meta = {
  title: "Inspectors/EuiPropertyInspector",
  component: EuiPropertyInspector,
  args: { fields: loadFields, values: loadValues, onChange: fn(), onEdit: fn() },
  parameters: { a11y: { context: "body" } },
  render: (args) => ({
    components: { EuiPropertyInspector },
    setup() {
      // A stand-in host: accepts plain values and echoes them back as the new state.
      const values = ref<Record<string, EuiFieldValue | undefined>>({ ...args.values });
      // args.onChange is bound through v-bind as well.
      function change(event: EuiFieldChange) {
        values.value = { ...values.value, [event.code]: event.number ?? event.value };
      }
      return { args, values, change };
    },
    template:
      '<div style="width:320px;border:1px solid var(--eui-border)"><EuiPropertyInspector v-bind="args" :values="values" @change="change" /></div>',
  }),
} satisfies Meta<typeof EuiPropertyInspector>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };
export const ReadOnly: Story = { args: { readonly: true } };
export const ValidationErrors: Story = {
  args: { errors: { sn_kva: "Rated power must be greater than 0", ref: "Reference L1 is already used" } },
};
export const ValidationErrorsDark: Story = { ...ValidationErrors, globals: { theme: "dark" } };
export const MultipleSelection: Story = { args: { mixed: ["name", "sn_kva", "mode", "type"] } };
export const Empty: Story = { args: { fields: [], values: {} } };
export const Narrow: Story = {
  render: (args) => ({
    components: { EuiPropertyInspector },
    setup: () => ({ args }),
    template: '<div style="width:220px"><EuiPropertyInspector v-bind="args" /></div>',
  }),
};
export const Wide: Story = {
  render: (args) => ({
    components: { EuiPropertyInspector },
    setup: () => ({ args }),
    template: '<div style="width:640px"><EuiPropertyInspector v-bind="args" /></div>',
  }),
};
export const LargeSchema: Story = {
  args: { fields: manyFields, values: manyValues, filterable: true },
  render: (args) => ({
    components: { EuiPropertyInspector },
    setup: () => ({ args }),
    template: '<div style="width:320px;height:420px;overflow:auto"><EuiPropertyInspector v-bind="args" /></div>',
  }),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.type(canvas.getByRole("searchbox", { name: "Filter properties" }), "Parameter 57");
    await expect(canvasElement.querySelectorAll("[data-field]")).toHaveLength(1);
  },
};

export const Keyboard: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    const reference = canvas.getByRole("textbox", { name: "Reference" });
    await userEvent.click(reference);
    await userEvent.tab();
    await expect(canvas.getByRole("textbox", { name: "Name" })).toHaveFocus();
    await userEvent.keyboard("{Control>}a{/Control}Office lighting{Enter}");
    await expect(args.onChange).toHaveBeenCalledWith({ code: "name", value: "Office lighting" });

    const power = canvas.getByRole("textbox", { name: "Rated power (kVA)" });
    await userEvent.click(power);
    await userEvent.clear(power);
    await userEvent.type(power, "20{Escape}");
    await expect(power).toHaveValue("12.5");
    await userEvent.clear(power);
    await userEvent.type(power, "20{Enter}");
    await expect(args.onChange).toHaveBeenCalledWith({ code: "sn_kva", value: "20", number: 20 });

    const inductive = canvas.getByRole("checkbox", { name: "Inductive" });
    inductive.focus();
    await userEvent.keyboard(" ");
    await expect(args.onChange).toHaveBeenCalledWith({ code: "mode", value: false });

    await userEvent.click(canvas.getByRole("button", { name: "Edit… Load profile" }));
    await expect(args.onEdit).toHaveBeenCalledWith("load_profile");
  },
};
