<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Desktop workspace layout: optional rail, collapsible left and right panels,
  a centre area and a collapsible bottom panel, separated by keyboard-operable
  splitters. Panel sizes are view state owned by the host (v-model:sizes).
-->
<template>
  <div class="eui-workspace">
    <slot name="rail" />
    <div class="eui-workspace__body">
      <div class="eui-workspace__row">
        <aside
          v-if="showLeft && $slots.left"
          :id="`${uid}-left`"
          class="eui-workspace__panel eui-workspace__panel--left"
          :style="{ width: `${current.left}px` }"
          :aria-label="leftLabel"
        >
          <div class="eui-workspace__scroll"><slot name="left" /></div>
          <WorkspaceSplitter
            class="eui-workspace__edge eui-workspace__edge--right"
            orientation="vertical"
            :label="`Resize ${leftLabel.toLowerCase()}`"
            :model-value="current.left"
            :min="limits.side[0]"
            :max="limits.side[1]"
            :direction="1"
            :controls="`${uid}-left`"
            @update:model-value="resize('left', $event)"
          />
        </aside>
        <main class="eui-workspace__center" :aria-label="centerLabel">
          <slot />
        </main>
        <aside
          v-if="showRight && $slots.right"
          :id="`${uid}-right`"
          class="eui-workspace__panel eui-workspace__panel--right"
          :style="{ width: `${current.right}px` }"
          :aria-label="rightLabel"
        >
          <WorkspaceSplitter
            class="eui-workspace__edge eui-workspace__edge--left"
            orientation="vertical"
            :label="`Resize ${rightLabel.toLowerCase()}`"
            :model-value="current.right"
            :min="limits.side[0]"
            :max="limits.side[1]"
            :direction="-1"
            :controls="`${uid}-right`"
            @update:model-value="resize('right', $event)"
          />
          <div class="eui-workspace__scroll"><slot name="right" /></div>
        </aside>
      </div>
      <section
        v-if="showBottom && $slots.bottom"
        :id="`${uid}-bottom`"
        class="eui-workspace__panel eui-workspace__panel--bottom"
        :style="{ height: `${current.bottom}px` }"
        :aria-label="bottomLabel"
      >
        <WorkspaceSplitter
          class="eui-workspace__edge eui-workspace__edge--top"
          orientation="horizontal"
          :label="`Resize ${bottomLabel.toLowerCase()}`"
          :model-value="current.bottom"
          :min="limits.bottom[0]"
          :max="limits.bottom[1]"
          :direction="-1"
          :controls="`${uid}-bottom`"
          @update:model-value="resize('bottom', $event)"
        />
        <div class="eui-workspace__scroll"><slot name="bottom" /></div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, useId } from "vue";
import WorkspaceSplitter from "./WorkspaceSplitter.vue";
import type { EuiWorkspaceSizes } from "./types";

export interface EuiWorkspaceProps {
  showLeft?: boolean;
  showRight?: boolean;
  showBottom?: boolean;
  leftLabel?: string;
  rightLabel?: string;
  bottomLabel?: string;
  centerLabel?: string;
  /** [min, max] width of the side panels in px. */
  sideLimits?: [number, number];
  /** [min, max] height of the bottom panel in px. */
  bottomLimits?: [number, number];
}

const props = withDefaults(defineProps<EuiWorkspaceProps>(), {
  showLeft: true,
  showRight: true,
  showBottom: false,
  leftLabel: "Left panel",
  rightLabel: "Right panel",
  bottomLabel: "Bottom panel",
  centerLabel: "Workspace",
  sideLimits: () => [160, 560],
  bottomLimits: () => [80, 480],
});
const sizes = defineModel<EuiWorkspaceSizes>("sizes", { default: () => ({ left: 240, right: 300, bottom: 180 }) });

const uid = useId();
const limits = computed(() => ({ side: props.sideLimits, bottom: props.bottomLimits }));
const current = computed(() => ({
  left: clamp(sizes.value.left, props.sideLimits),
  right: clamp(sizes.value.right, props.sideLimits),
  bottom: clamp(sizes.value.bottom, props.bottomLimits),
}));

function clamp(value: number, [min, max]: [number, number]) {
  return Math.min(max, Math.max(min, Number.isFinite(value) ? value : min));
}

function resize(panel: keyof EuiWorkspaceSizes, value: number) {
  sizes.value = { ...sizes.value, [panel]: value };
}
</script>

<style scoped>
.eui-workspace {
  display: flex;
  flex: 1;
  min-height: 0;
  min-width: 0;
  background: var(--eui-frame);
  color: var(--eui-text);
}
.eui-workspace__body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
}
.eui-workspace__row {
  display: flex;
  flex: 1;
  min-height: 0;
}
.eui-workspace__panel {
  position: relative;
  flex: none;
  display: flex;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--eui-panel);
}
.eui-workspace__panel--left {
  border-right: var(--eui-border-width) solid var(--eui-border-soft);
}
.eui-workspace__panel--right {
  border-left: var(--eui-border-width) solid var(--eui-border-soft);
}
.eui-workspace__panel--bottom {
  border-top: var(--eui-border-width) solid var(--eui-border-soft);
}
.eui-workspace__scroll {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}
/* Splitters sit on the inner edge of their panel, inside its landmark. */
.eui-workspace__edge {
  position: absolute;
  z-index: 2;
}
.eui-workspace__edge--right {
  top: 0;
  right: 0;
  bottom: 0;
}
.eui-workspace__edge--left {
  top: 0;
  left: 0;
  bottom: 0;
}
.eui-workspace__edge--top {
  top: 0;
  left: 0;
  right: 0;
}
.eui-workspace__center {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: var(--eui-workspace);
}
</style>
