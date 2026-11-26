// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import { expect, userEvent, within } from "storybook/test";
import EuiWorkspace from "../src/workspace/EuiWorkspace.vue";
import EuiDocumentRail from "../src/navigation/EuiDocumentRail.vue";

const meta = {
  title: "Workspace/EuiWorkspace",
  component: EuiWorkspace,
  args: {
    showLeft: true,
    showRight: true,
    showBottom: true,
    leftLabel: "Components",
    rightLabel: "Inspector",
    bottomLabel: "Messages",
    centerLabel: "Drawing",
  },
  parameters: { layout: "fullscreen" },
  render: (args) => ({
    components: { EuiWorkspace, EuiDocumentRail },
    setup() {
      const sizes = ref({ left: 220, right: 280, bottom: 120 });
      return { args, sizes };
    },
    template: `
      <div style="display:flex;height:480px">
        <EuiWorkspace v-bind="args" v-model:sizes="sizes">
          <template #rail><EuiDocumentRail :items="[{ id: 'a', title: 'Main substation' }]" model-value="a" /></template>
          <template #left><p style="padding:8px;margin:0">Component palette</p></template>
          <div style="padding:8px">Schematic canvas · left {{ sizes.left }} px · right {{ sizes.right }} px · bottom {{ sizes.bottom }} px</div>
          <template #right><p style="padding:8px;margin:0">Properties</p></template>
          <template #bottom><p style="padding:8px;margin:0">Analysis log</p></template>
        </EuiWorkspace>
      </div>`,
  }),
} satisfies Meta<typeof EuiWorkspace>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };
export const PanelsCollapsed: Story = { args: { showLeft: false, showRight: false, showBottom: false } };
export const Narrow: Story = {
  decorators: [() => ({ template: '<div style="width:640px"><story /></div>' })],
};

export const Keyboard: Story = {
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    const left = canvas.getByRole("separator", { name: "Resize components" });
    await userEvent.click(left);
    await userEvent.keyboard("{ArrowRight}");
    await expect(left).toHaveAttribute("aria-valuenow", "236");
    await userEvent.keyboard("{Shift>}{ArrowLeft}{/Shift}");
    await expect(left).toHaveAttribute("aria-valuenow", "172");
    await userEvent.keyboard("{Home}");
    await expect(left).toHaveAttribute("aria-valuenow", "160");
    const bottom = canvas.getByRole("separator", { name: "Resize messages" });
    bottom.focus();
    await userEvent.keyboard("{ArrowUp}");
    await expect(bottom).toHaveAttribute("aria-valuenow", "136");
  },
};
