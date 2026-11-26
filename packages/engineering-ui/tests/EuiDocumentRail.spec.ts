// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import EuiDocumentRail from "../src/navigation/EuiDocumentRail.vue";
import { mountEui } from "./helpers";

const items = [
  { id: "a", title: "Main substation", path: "/projects/main.gepro" },
  { id: "b", title: "Factory feeder", dirty: true },
  { id: "c", title: "" },
];

describe("EuiDocumentRail", () => {
  it("renders tiles with codes, the active marker and dirty state", () => {
    const wrapper = mountEui(EuiDocumentRail, { props: { items, modelValue: "b" } });
    const tiles = wrapper.findAll(".eui-rail__tile");
    expect(tiles.map((tile) => tile.get('[aria-hidden="true"]').text())).toEqual(["MS", "FF", "UN"]);
    expect(tiles[1]!.attributes("aria-current")).toBe("page");
    expect(tiles[1]!.get(".eui-visually-hidden").text()).toBe("Factory feeder, unsaved changes");
    expect(tiles.map((tile) => tile.attributes("tabindex"))).toEqual(["-1", "0", "-1"]);
  });

  it("activates, closes with Delete and adds", async () => {
    const wrapper = mountEui(EuiDocumentRail, { props: { items, modelValue: "a" } });
    const tiles = wrapper.findAll(".eui-rail__tile");
    await tiles[2]!.trigger("click");
    await tiles[0]!.trigger("keydown", { key: "Delete" });
    await wrapper.get(".eui-rail__add").trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["c"]]);
    expect(wrapper.emitted("close")).toEqual([["a"]]);
    expect(wrapper.emitted("add")).toHaveLength(1);
  });

  it("moves focus with arrow keys and shows the flyout for the focused tile", async () => {
    const wrapper = mountEui(EuiDocumentRail, { props: { items, modelValue: "a" } });
    const tiles = wrapper.findAll<HTMLButtonElement>(".eui-rail__tile");
    tiles[0]!.element.focus();
    await tiles[0]!.trigger("keydown", { key: "ArrowUp" });
    expect(document.activeElement).toBe(tiles[2]!.element);
    await tiles[0]!.trigger("focus");
    expect(wrapper.get('[role="tooltip"]').text()).toContain("/projects/main.gepro");
  });

  it("blocks other documents and closing while busy", async () => {
    const wrapper = mountEui(EuiDocumentRail, { props: { items, modelValue: "a", busy: true } });
    const tiles = wrapper.findAll(".eui-rail__tile");
    expect(tiles[0]!.attributes("disabled")).toBeUndefined();
    expect(tiles[1]!.attributes("disabled")).toBeDefined();
    await tiles[0]!.trigger("keydown", { key: "Delete" });
    expect(wrapper.emitted("close")).toBeUndefined();
  });
});
