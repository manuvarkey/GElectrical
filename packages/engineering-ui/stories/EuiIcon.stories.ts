// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, within } from "storybook/test";
import EuiIcon from "../src/icons/EuiIcon.vue";
import { iconNames } from "../src/icons/iconPaths";

const meta = {
  title: "Icons/EuiIcon",
  component: EuiIcon,
  args: { name: "transformer", size: 24 },
  argTypes: { name: { control: "select", options: iconNames } },
} satisfies Meta<typeof EuiIcon>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Labelled: Story = {
  args: { label: "Transformer" },
  play: async ({ canvasElement }) => {
    await expect(within(canvasElement).getByRole("img", { name: "Transformer" })).toBeInTheDocument();
  },
};

const gallery = {
  render: (args: { size?: number }) => ({
    components: { EuiIcon },
    setup: () => ({ iconNames, args }),
    template: `
      <ul style="display:grid;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));gap:8px;margin:0;padding:0;list-style:none;color:var(--eui-icon)">
        <li v-for="name in iconNames" :key="name" style="display:flex;flex-direction:column;align-items:center;gap:4px">
          <EuiIcon :name="name" :size="args.size" />
          <code style="font-size:var(--eui-font-size-caption);color:var(--eui-text-muted)">{{ name }}</code>
        </li>
      </ul>`,
  }),
};

export const Gallery: Story = { ...gallery, args: { size: 24 } };
export const GallerySmall: Story = { ...gallery, args: { size: 16 } };
export const GalleryDark: Story = { ...gallery, args: { size: 24 }, globals: { theme: "dark" } };
