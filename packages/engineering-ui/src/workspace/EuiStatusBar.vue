<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Status bar: static items at the start and end, a transient notice and an
  optional busy indicator. Only the notice and busy text are announced
  (polite live region) so routine updates such as coordinates stay quiet.
-->
<template>
  <footer class="eui-statusbar" :aria-label="label">
    <div class="eui-statusbar__side">
      <span
        v-for="item in startItems"
        :key="item.id"
        class="eui-statusbar__item"
        :class="`eui-statusbar__item--${item.tone || 'neutral'}`"
        :title="item.title"
        :data-status="item.id"
      >
        <EuiIcon v-if="item.icon" :name="item.icon" :size="14" />{{ item.text }}
      </span>
    </div>
    <div class="eui-statusbar__notice" role="status" aria-live="polite">
      <template v-if="busy"> <span class="eui-statusbar__spinner" aria-hidden="true" />{{ busy }} </template>
      <template v-else>{{ notice }}</template>
    </div>
    <div class="eui-statusbar__side eui-statusbar__side--end">
      <span
        v-for="item in endItems"
        :key="item.id"
        class="eui-statusbar__item"
        :class="`eui-statusbar__item--${item.tone || 'neutral'}`"
        :title="item.title"
        :data-status="item.id"
      >
        <EuiIcon v-if="item.icon" :name="item.icon" :size="14" />{{ item.text }}
      </span>
      <slot name="end" />
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from "vue";
import EuiIcon from "../icons/EuiIcon.vue";
import type { EuiStatusItem } from "./types";

export interface EuiStatusBarProps {
  items?: EuiStatusItem[];
  /** Transient feedback such as "Copied 3 elements". */
  notice?: string;
  /** Text of a running operation; shows a busy indicator instead of the notice. */
  busy?: string;
  label?: string;
}

const props = withDefaults(defineProps<EuiStatusBarProps>(), {
  items: () => [],
  notice: "",
  busy: "",
  label: "Status bar",
});

const startItems = computed(() => props.items.filter((item) => item.align !== "end"));
const endItems = computed(() => props.items.filter((item) => item.align === "end"));
</script>

<style scoped>
.eui-statusbar {
  display: flex;
  align-items: center;
  gap: var(--eui-space-5);
  min-height: var(--eui-statusbar-height);
  padding: 0 var(--eui-space-4);
  background: var(--eui-frame);
  color: var(--eui-text-muted);
  border-top: var(--eui-border-width) solid var(--eui-border);
  font-size: var(--eui-font-size-small);
  white-space: nowrap;
  min-width: 0;
}
.eui-statusbar__side {
  display: flex;
  align-items: center;
  gap: var(--eui-space-5);
  min-width: 0;
}
.eui-statusbar__side--end {
  margin-left: auto;
}
.eui-statusbar__item {
  display: inline-flex;
  align-items: center;
  gap: var(--eui-space-2);
  overflow: hidden;
  text-overflow: ellipsis;
}
.eui-statusbar__item--success {
  color: var(--eui-success);
}
.eui-statusbar__item--warning {
  color: var(--eui-warning);
}
.eui-statusbar__item--danger {
  color: var(--eui-danger);
}
.eui-statusbar__item--info {
  color: var(--eui-info);
}
.eui-statusbar__notice {
  display: flex;
  align-items: center;
  gap: var(--eui-space-3);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--eui-text);
}
.eui-statusbar__spinner {
  width: 10px;
  height: 10px;
  border: 2px solid var(--eui-border);
  border-top-color: var(--eui-accent-fill);
  border-radius: 50%;
  animation: eui-spin 0.9s linear infinite;
}
@keyframes eui-spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .eui-statusbar__spinner {
    animation: none;
  }
}
</style>
