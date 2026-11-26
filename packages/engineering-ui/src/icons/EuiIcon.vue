<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey
  Adapted from GEstimator modern/src/components/AppIcon.vue at e4e4fb295899feda5253ba216613c70c1f256d4e
-->
<template>
  <svg
    class="eui-icon"
    :data-icon="name"
    :width="px"
    :height="px"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    :role="label ? 'img' : undefined"
    :aria-label="label || undefined"
    :aria-hidden="label ? undefined : 'true'"
    focusable="false"
  >
    <path class="eui-icon__body" :d="paths[0]" />
    <path v-if="paths[1]" class="eui-icon__accent" :d="paths[1]" />
  </svg>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { iconPaths, type EuiIconName } from "./iconPaths";

export interface EuiIconProps {
  name: EuiIconName;
  /** Size in px (default 18). */
  size?: number;
  /** Accessible name. Without it the icon is decorative (aria-hidden). */
  label?: string;
}

const props = defineProps<EuiIconProps>();

const paths = computed<readonly [string, string?]>(() => iconPaths[props.name] ?? iconPaths.grid);
const px = computed(() => props.size || 18);
// About 1.25 px lines at small sizes, 1.75 units on the 24 grid above that.
const strokeWidth = computed(() => (px.value <= 18 ? Math.round((1.25 * 24 * 100) / px.value) / 100 : 1.75));
</script>

<style scoped>
.eui-icon__accent {
  stroke: var(--eui-icon-accent, currentColor);
}
</style>
