<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Focusable window splitter (WAI-ARIA separator). Arrow keys resize by 16 px
  (Shift: 64 px), Home/End jump to the limits, pointer drag resizes.
-->
<template>
  <div
    class="eui-splitter"
    :class="`eui-splitter--${orientation}`"
    role="separator"
    tabindex="0"
    :aria-orientation="orientation"
    :aria-label="label"
    :aria-valuenow="Math.round(modelValue)"
    :aria-valuemin="min"
    :aria-valuemax="max"
    :aria-controls="controls"
    @keydown="keydown"
    @pointerdown="pointerdown"
  />
</template>

<script setup lang="ts">
const props = defineProps<{
  /** "vertical" separates side-by-side panels; "horizontal" stacked panels. */
  orientation: "vertical" | "horizontal";
  label: string;
  modelValue: number;
  min: number;
  max: number;
  /** +1 when moving right/down grows the panel, -1 when it shrinks it. */
  direction: 1 | -1;
  controls?: string;
}>();
const emit = defineEmits<{ "update:modelValue": [value: number] }>();

function clamp(value: number) {
  return Math.min(props.max, Math.max(props.min, value));
}

function keydown(event: KeyboardEvent) {
  const step = event.shiftKey ? 64 : 16;
  const grow = props.orientation === "vertical" ? "ArrowRight" : "ArrowDown";
  const shrink = props.orientation === "vertical" ? "ArrowLeft" : "ArrowUp";
  let next: number | undefined;
  if (event.key === grow) next = props.modelValue + step * props.direction;
  else if (event.key === shrink) next = props.modelValue - step * props.direction;
  else if (event.key === "Home") next = props.min;
  else if (event.key === "End") next = props.max;
  if (next === undefined) return;
  event.preventDefault();
  emit("update:modelValue", clamp(next));
}

function pointerdown(event: PointerEvent) {
  if (event.button !== 0) return;
  const target = event.currentTarget as HTMLElement;
  const start = props.orientation === "vertical" ? event.clientX : event.clientY;
  const initial = props.modelValue;
  target.setPointerCapture?.(event.pointerId);
  const move = (moveEvent: PointerEvent) => {
    const position = props.orientation === "vertical" ? moveEvent.clientX : moveEvent.clientY;
    emit("update:modelValue", clamp(initial + (position - start) * props.direction));
  };
  const up = () => {
    target.removeEventListener("pointermove", move);
    target.removeEventListener("pointerup", up);
    target.removeEventListener("pointercancel", up);
  };
  target.addEventListener("pointermove", move);
  target.addEventListener("pointerup", up);
  target.addEventListener("pointercancel", up);
}
</script>

<style scoped>
.eui-splitter {
  flex: none;
  background: transparent;
  touch-action: none;
}
.eui-splitter--vertical {
  width: var(--eui-splitter-size);
  cursor: col-resize;
}
.eui-splitter--horizontal {
  height: var(--eui-splitter-size);
  cursor: row-resize;
}
.eui-splitter:hover {
  background: var(--eui-border);
}
.eui-splitter:focus-visible {
  outline: none;
  background: var(--eui-focus-ring);
}
</style>
