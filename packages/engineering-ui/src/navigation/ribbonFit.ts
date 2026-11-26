// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
// Adapted from GEstimator modern/src/components/RibbonToolbar.vue at e4e4fb295899feda5253ba216613c70c1f256d4e
//
// Measured ribbon overflow: captions are sized to their best two-line split,
// then the rightmost commands collapse to icon-only buttons until the groups
// fit, keeping a constant ribbon height.

let measure: CanvasRenderingContext2D | null | undefined;

function context() {
  if (measure === undefined) {
    try {
      measure = document.createElement("canvas").getContext("2d");
    } catch {
      measure = null;
    }
  }
  return measure;
}

function sizeCaptions(host: HTMLElement) {
  const ctx = context();
  if (!ctx) return;
  for (const button of Array.from(host.querySelectorAll<HTMLElement>(".eui-ribbon__command"))) {
    const label = button.querySelector<HTMLElement>(".eui-ribbon__label");
    const text = label?.textContent?.trim();
    if (!label || !text) continue;
    const style = getComputedStyle(label);
    ctx.font = `${style.fontStyle} ${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const spacing = parseFloat(style.letterSpacing) || 0;
    const width = (value: string) => ctx.measureText(value).width + Math.max(0, value.length - 1) * spacing;
    const words = text.split(/\s+/);
    let caption = width(text);
    for (let split = 1; split < words.length; split++) {
      caption = Math.min(
        caption,
        Math.max(width(words.slice(0, split).join(" ")), width(words.slice(split).join(" "))),
      );
    }
    // 3 px margin over canvas measurement avoids subpixel wrapping; cap under the 80 px button width.
    caption = Math.min(71, Math.ceil(caption) + 3);
    const padding = getComputedStyle(button);
    const total = caption + parseFloat(padding.paddingLeft) + parseFloat(padding.paddingRight);
    button.style.setProperty("--eui-ribbon-caption-width", `${caption}px`);
    button.style.setProperty("--eui-ribbon-button-width", `${Math.max(52, Math.ceil(total))}px`);
  }
}

/** Fits the ribbon panel `host` to its width. Returns the number of collapsed commands. */
export function fitRibbon(host: HTMLElement): number {
  host.querySelectorAll("[data-mini]").forEach((button) => button.removeAttribute("data-mini"));
  sizeCaptions(host);
  const groups = Array.from(host.querySelectorAll<HTMLElement>(".eui-ribbon__group"));
  const used = () => groups.reduce((total, group) => total + group.getBoundingClientRect().width, 0);
  const style = getComputedStyle(host);
  const available = host.clientWidth - (parseFloat(style.paddingLeft) || 0) - (parseFloat(style.paddingRight) || 0);
  let collapsed = 0;
  const buttons = Array.from(host.querySelectorAll<HTMLElement>(".eui-ribbon__command")).reverse();
  for (const button of buttons) {
    if (used() <= available) break;
    if (button.hasAttribute("data-keep-label")) continue;
    if (button.getBoundingClientRect().width) {
      button.dataset.mini = "true";
      collapsed++;
    }
  }
  return collapsed;
}
