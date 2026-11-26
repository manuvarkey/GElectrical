// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import EuiStatusBar from "../src/workspace/EuiStatusBar.vue";

const meta = {
  title: "Workspace/EuiStatusBar",
  component: EuiStatusBar,
  parameters: { layout: "fullscreen" },
  args: {
    items: [
      { id: "selection", text: "2 elements selected" },
      { id: "mode", text: "Insert: Load · R rotate · Esc cancel", icon: "pointer" },
      { id: "coords", text: "X 120  Y 340", align: "end" },
      { id: "zoom", text: "100 %", align: "end", icon: "search" },
      { id: "saved", text: "Unsaved changes", align: "end", tone: "warning", icon: "warning" },
    ],
    notice: "Copied 2 elements",
  },
} satisfies Meta<typeof EuiStatusBar>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };
export const Busy: Story = { args: { busy: "Running power flow…" } };
export const Narrow: Story = { decorators: [() => ({ template: '<div style="width:360px"><story /></div>' })] };
