// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";

const groups: Record<string, string[]> = {
  Surfaces: ["frame", "panel", "raised", "field", "workspace", "hover"],
  Text: ["text", "text-muted", "text-hint", "text-disabled"],
  Accent: ["accent", "accent-fill", "accent-soft", "icon-accent", "selection", "focus-ring"],
  States: ["success", "warning", "danger", "info"],
  Schematic: [
    "schematic-background",
    "schematic-normal",
    "schematic-inactive",
    "schematic-selected",
    "schematic-warning",
    "schematic-grid",
    "schematic-overlay",
  ],
  Chart: ["chart-1", "chart-2", "chart-3", "chart-4", "chart-5", "chart-6"],
  Documents: ["doc-1", "doc-2", "doc-3", "doc-4", "doc-5", "doc-6", "doc-7", "doc-8"],
};

const meta = {
  title: "Theme/Tokens",
  render: () => ({
    setup: () => ({ groups }),
    template: `
      <div style="display:grid;gap:16px;color:var(--eui-text)">
        <section v-for="(tokens, name) in groups" :key="name">
          <h2 style="margin:0 0 6px;font-size:var(--eui-font-size-heading)">{{ name }}</h2>
          <ul style="display:flex;flex-wrap:wrap;gap:8px;margin:0;padding:0;list-style:none">
            <li v-for="token in tokens" :key="token" style="width:132px">
              <div :style="{ background: 'var(--eui-' + token + ')', height: '28px', border: '1px solid var(--eui-border)', borderRadius: 'var(--eui-radius)' }" />
              <code style="font-size:var(--eui-font-size-small)">--eui-{{ token }}</code>
            </li>
          </ul>
        </section>
      </div>`,
  }),
} satisfies Meta;

export default meta;
type Story = StoryObj<typeof meta>;

export const Light: Story = { globals: { theme: "light" } };
export const Dark: Story = { globals: { theme: "dark" } };
