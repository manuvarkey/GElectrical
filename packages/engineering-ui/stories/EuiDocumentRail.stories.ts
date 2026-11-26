// SPDX-License-Identifier: MIT
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import { expect, fn, userEvent, within } from "storybook/test";
import EuiDocumentRail from "../src/navigation/EuiDocumentRail.vue";
import type { EuiDocumentItem } from "../src/navigation/types";

const documents: EuiDocumentItem[] = [
  { id: "doc-main", title: "Main substation", path: "/home/user/projects/main-substation.gepro" },
  { id: "doc-factory", title: "Factory feeder", path: "/home/user/projects/factory.gepro", dirty: true },
  { id: "doc-new", title: "" },
];

const meta = {
  title: "Navigation/EuiDocumentRail",
  component: EuiDocumentRail,
  args: { items: documents, modelValue: "doc-main", busy: false, onClose: fn(), onAdd: fn() },
  parameters: { layout: "fullscreen" },
  render: (args) => ({
    components: { EuiDocumentRail },
    setup() {
      const active = ref(args.modelValue);
      return { args, active };
    },
    template: '<div style="display:flex;height:360px"><EuiDocumentRail v-bind="args" v-model="active" /></div>',
  }),
} satisfies Meta<typeof EuiDocumentRail>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Dark: Story = { globals: { theme: "dark" } };
export const Busy: Story = { args: { busy: true } };
export const Single: Story = { args: { items: documents.slice(0, 1) } };
export const ManyDocuments: Story = {
  args: {
    items: Array.from({ length: 14 }, (_, index) => ({
      id: `doc-${index}`,
      title: `Project ${index + 1}`,
      colour: (index % 8) + 1,
      dirty: index % 4 === 0,
    })),
    modelValue: "doc-3",
  },
};

export const Keyboard: Story = {
  play: async ({ canvasElement, args }) => {
    const canvas = within(canvasElement);
    await userEvent.tab();
    const main = canvas.getByRole("button", { name: "Main substation" });
    await expect(main).toHaveFocus();
    await expect(main).toHaveAttribute("aria-current", "page");
    await userEvent.keyboard("{ArrowDown}");
    const factory = canvas.getByRole("button", { name: "Factory feeder, unsaved changes" });
    await expect(factory).toHaveFocus();
    await expect(within(document.body).getByRole("tooltip")).toHaveTextContent("factory.gepro");
    await userEvent.keyboard("{Enter}");
    await expect(factory).toHaveAttribute("aria-current", "page");
    await userEvent.keyboard("{Delete}");
    await expect(args.onClose).toHaveBeenCalledWith("doc-factory");
    await userEvent.keyboard("{End}");
    await expect(canvas.getByRole("button", { name: "Untitled" })).toHaveFocus();
    await userEvent.tab();
    await expect(canvas.getByRole("button", { name: "New document" })).toHaveFocus();
    await userEvent.keyboard(" ");
    await expect(args.onAdd).toHaveBeenCalled();
  },
};
