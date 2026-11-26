// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { moveRovingFocus, nextRovingIndex } from "../src/composables/rovingFocus";

describe("nextRovingIndex", () => {
  it("wraps in both directions", () => {
    expect(nextRovingIndex("ArrowRight", 2, 3, "horizontal")).toBe(0);
    expect(nextRovingIndex("ArrowLeft", 0, 3, "horizontal")).toBe(2);
    expect(nextRovingIndex("ArrowDown", 0, 3, "vertical")).toBe(1);
    expect(nextRovingIndex("ArrowUp", 0, 3, "vertical")).toBe(2);
  });
  it("jumps with Home and End and ignores cross-axis keys", () => {
    expect(nextRovingIndex("Home", 2, 3, "vertical")).toBe(0);
    expect(nextRovingIndex("End", 0, 3, "horizontal")).toBe(2);
    expect(nextRovingIndex("ArrowDown", 0, 3, "horizontal")).toBe(-1);
    expect(nextRovingIndex("Enter", 0, 3, "horizontal")).toBe(-1);
    expect(nextRovingIndex("ArrowRight", 0, 0, "horizontal")).toBe(-1);
  });
});

describe("moveRovingFocus", () => {
  it("focuses the next item and prevents the default action", () => {
    const buttons = [0, 1, 2].map(() => document.body.appendChild(document.createElement("button")));
    const event = new KeyboardEvent("keydown", { key: "ArrowRight", cancelable: true });
    Object.defineProperty(event, "target", { value: buttons[0] });
    expect(moveRovingFocus(event, buttons, "horizontal")).toBe(1);
    expect(document.activeElement).toBe(buttons[1]);
    expect(event.defaultPrevented).toBe(true);
  });
});
