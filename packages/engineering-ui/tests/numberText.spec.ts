// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { formatNumber, parsePlainNumber, rawNumberText } from "../src/controls/numberText";

describe("formatNumber", () => {
  it("applies the display precision", () => {
    expect(formatNumber(0.8, 2)).toBe("0.80");
    expect(formatNumber(11.0004, 3)).toBe("11.000");
    expect(formatNumber(5, 0)).toBe("5");
  });
  it("keeps full precision without a decimal and blanks missing values", () => {
    expect(formatNumber(1.23456789)).toBe("1.23456789");
    expect(formatNumber(null, 2)).toBe("");
    expect(formatNumber(undefined)).toBe("");
    expect(formatNumber(Number.NaN, 2)).toBe("");
    expect(formatNumber(Number.POSITIVE_INFINITY, 2)).toBe("");
  });
});

describe("rawNumberText", () => {
  it("returns the unrounded value", () => {
    expect(rawNumberText(0.123456789)).toBe("0.123456789");
    expect(rawNumberText(null)).toBe("");
  });
});

describe("parsePlainNumber", () => {
  it.each([
    ["1", 1],
    [" -2.5 ", -2.5],
    ["+.5", 0.5],
    ["3.", 3],
    ["1e3", 1000],
    ["2.5E-2", 0.025],
  ])("parses %j", (text, value) => {
    expect(parsePlainNumber(text)).toBe(value);
  });
  it.each(["", "2*3", "1,5", "abc", "1e", "--1", "Infinity", "0x10", "1e999"])("leaves %j to the host", (text) => {
    expect(parsePlainNumber(text)).toBeNull();
  });
});
