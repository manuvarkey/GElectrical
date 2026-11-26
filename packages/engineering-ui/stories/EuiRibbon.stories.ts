// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import { expect, fn, userEvent, waitFor, within } from "storybook/test";
import EuiRibbon from "../src/navigation/EuiRibbon.vue";
import EuiIcon from "../src/icons/EuiIcon.vue";
import { ribbonTabs } from "./fixtures/ribbon";

const meta = {
  title: "Navigation/EuiRibbon",
  component: EuiRibbon,
  args: { tabs: ribbonTabs, modelValue: "home", busy: false, onCommand: fn() },
  parameters: { layout: "fullscreen" },
  render: (args) => ({
    components: { EuiRibbon, EuiIcon },
    setup() {
      const active = ref(args.modelValue);
      return { args, active };
    },
    template: `
      <EuiRibbon v-bind="args" v-model="active">
        <template #end>
          <button class="eui-plain-button" type="button" aria-label="Help" title="Help" style="display:flex;padding:4px">
            <EuiIcon name="help" />
          </button>
        </template>
      </EuiRibbon>`,
  }),
} satisfies Meta<typeof EuiRibbon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = {
  globals: { theme: "dark" },
  play: async ({ canvasElement }) => {
    // The a11y check runs against the dark tokens.
    await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
    const panel = canvasElement.querySelector(".eui-ribbon")!;
    await expect(getComputedStyle(panel).backgroundColor).toBe("rgb(51, 51, 60)");
  },
};
export const Busy: Story = { args: { busy: true } };
export const ContextualTab: Story = { args: { modelValue: "selection" } };

export const Narrow: Story = {
  decorators: [() => ({ template: '<div style="width:420px"><story /></div>' })],
  play: async ({ canvasElement }) => {
    // Commands collapse to icon-only buttons, which keep their accessible names.
    await waitFor(() => expect(canvasElement.querySelectorAll("[data-mini]").length).toBeGreaterThan(0));
    await expect(within(canvasElement).getByRole("button", { name: "Paste" })).toBeInTheDocument();
  },
};

export const Wide: Story = {
  decorators: [() => ({ template: '<div style="width:1400px"><story /></div>' })],
  play: async ({ canvasElement }) => {
    await waitFor(() => expect(canvasElement.querySelectorAll("[data-mini]").length).toBe(0));
  },
};

export const Keyboard: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.tab();
    await expect(canvas.getByRole("tab", { name: "Home" })).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    await expect(canvas.getByRole("tab", { name: "Insert" })).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{End}");
    await expect(canvas.getByRole("tab", { name: "Transformer" })).toHaveFocus();
    await userEvent.keyboard("{Home}");
    // The tab strip's end slot (Help) comes before the command toolbar.
    await userEvent.tab();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "New sheet" })).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}{ArrowRight}{ArrowRight}");
    await expect(canvas.getByRole("button", { name: "Undo" })).toHaveFocus();
    // Redo is disabled and skipped.
    await userEvent.keyboard("{ArrowRight}");
    await expect(canvas.getByRole("button", { name: "Cut" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    await expect(args.onCommand).toHaveBeenCalledWith("cut");
  },
};
