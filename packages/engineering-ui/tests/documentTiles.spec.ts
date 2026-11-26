// SPDX-License-Identifier: MIT
import { describe, expect, it } from "vitest";
import { documentCode, documentColourIndex } from "../src/navigation/documentTiles";

describe("documentCode", () => {
  it("uses initials of the first two words", () => {
    expect(documentCode("Main substation.gepro")).toBe("MS");
    expect(documentCode("ht-panel_rev2")).toBe("HP");
  });
  it("uses two letters of a single word and a dash for empty titles", () => {
    expect(documentCode("factory")).toBe("FA");
    expect(documentCode("   ")).toBe("–");
  });
});

describe("documentColourIndex", () => {
  it("is stable and within 1–8", () => {
    const index = documentColourIndex("doc-1");
    expect(index).toBe(documentColourIndex("doc-1"));
    for (const seed of ["a", "b", "project", "x".repeat(200)]) {
      expect(documentColourIndex(seed)).toBeGreaterThanOrEqual(1);
      expect(documentColourIndex(seed)).toBeLessThanOrEqual(8);
    }
  });
});
