// SPDX-License-Identifier: MIT
import { describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";

describe("useTheme", () => {
  it("resolves system, light and dark onto data-theme and Quasar Dark", async () => {
    vi.resetModules();
    const listeners: (() => void)[] = [];
    const media = { matches: true, addEventListener: (_: string, fn: () => void) => listeners.push(fn) };
    vi.stubGlobal("matchMedia", () => media);
    const { useTheme, bindQuasarDark } = await import("../src/theme/useTheme");
    const theme = useTheme();
    const dark = { set: vi.fn() };
    bindQuasarDark(dark);
    expect(theme.preference.value).toBe("system");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(dark.set).toHaveBeenLastCalledWith(true);

    media.matches = false;
    listeners.forEach((fn) => fn());
    await nextTick();
    expect(theme.resolved.value).toBe("light");
    expect(dark.set).toHaveBeenLastCalledWith(false);

    theme.setPreference("dark");
    await nextTick();
    expect(document.documentElement.dataset.theme).toBe("dark");
    theme.toggle();
    await nextTick();
    expect(theme.preference.value).toBe("light");
    vi.unstubAllGlobals();
  });

  it("applies valid fonts and ignores invalid ones", async () => {
    vi.resetModules();
    const { useTheme, normalizeFontFamily, normalizeFontSize } = await import("../src/theme/useTheme");
    const theme = useTheme();
    theme.setFonts({ family: "Inter", size: 14, tableFamily: "", tableSize: 99 });
    const style = document.documentElement.style;
    expect(style.getPropertyValue("--eui-font-family")).toContain('"Inter"');
    expect(style.getPropertyValue("--eui-font-size")).toBe("14px");
    expect(style.getPropertyValue("--eui-table-font-size")).toBe("");
    expect(normalizeFontFamily("Bad\u0007Font")).toBe("");
    expect(normalizeFontFamily(42)).toBe("");
    expect(normalizeFontSize(9)).toBeNull();
    expect(normalizeFontSize(30)).toBe(30);
  });
});
