// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { expect, userEvent, waitFor, within } from "storybook/test";
import EuiNotifications from "../src/workspace/EuiNotifications.vue";
import { createNotificationQueue } from "../src/workspace/notifications";
import type { EuiNotification } from "../src/workspace/types";

const samples: EuiNotification[] = [
  { id: "1", tone: "info", title: "Opened Main substation", text: "3 sheets, 42 elements" },
  { id: "2", tone: "success", title: "Power flow finished", text: "Converged in 4 iterations" },
  { id: "3", tone: "warning", title: "2 rule violations", actions: [{ id: "show", label: "Show messages" }] },
  { id: "4", tone: "danger", title: "Short circuit failed", text: "Bus B3 is not connected to a source." },
];

const meta = {
  title: "Workspace/EuiNotifications",
  component: EuiNotifications,
  args: { items: samples, position: "top-right" },
  parameters: { layout: "fullscreen", a11y: { context: "body" } },
  decorators: [() => ({ template: '<div style="height:420px"><story /></div>' })],
} satisfies Meta<typeof EuiNotifications>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };

export const Queue: Story = {
  render: () => ({
    components: { EuiNotifications },
    setup() {
      const queue = createNotificationQueue({ defaultTimeout: 4000 });
      const add = (tone: EuiNotification["tone"]) => queue.notify({ tone, title: `${tone} notice` });
      return { queue, add };
    },
    template: `
      <div style="padding:16px;display:flex;gap:8px">
        <button type="button" @click="add('info')">Add info</button>
        <button type="button" @click="add('danger')">Add error</button>
      </div>
      <EuiNotifications :items="queue.items.value" position="top-right" @dismiss="queue.dismiss" />`,
  }),
  play: async ({ canvasElement }) => {
    const canvas = within(canvasElement);
    await userEvent.click(canvas.getByRole("button", { name: "Add error" }));
    const alert = await canvas.findByRole("alert");
    await expect(alert).toHaveTextContent("Error: danger notice");
    await userEvent.click(canvas.getByRole("button", { name: "Dismiss: danger notice" }));
    await waitFor(() => expect(canvas.queryByRole("alert")).toBeNull());
  },
};
