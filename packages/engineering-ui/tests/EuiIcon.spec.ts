// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import EuiIcon from "../src/icons/EuiIcon.vue";
import { iconNames, iconPaths } from "../src/icons/iconPaths";

describe("EuiIcon", () => {
  it("is decorative without a label", () => {
    const wrapper = mount(EuiIcon, { props: { name: "save" } });
    expect(wrapper.attributes("aria-hidden")).toBe("true");
    expect(wrapper.attributes("role")).toBeUndefined();
    expect(wrapper.findAll("path")).toHaveLength(2);
  });
  it("exposes an accessible name with a label and scales the stroke", () => {
    const wrapper = mount(EuiIcon, { props: { name: "transformer", label: "Transformer", size: 12 } });
    expect(wrapper.attributes("role")).toBe("img");
    expect(wrapper.attributes("aria-label")).toBe("Transformer");
    expect(wrapper.attributes("stroke-width")).toBe("2.5");
    expect(mount(EuiIcon, { props: { name: "busbar", size: 24 } }).attributes("stroke-width")).toBe("1.75");
  });
  it("keeps every path within the drawing grammar (body plus at most one accent)", () => {
    for (const name of iconNames) expect(iconPaths[name].length).toBeLessThanOrEqual(2);
  });
});
