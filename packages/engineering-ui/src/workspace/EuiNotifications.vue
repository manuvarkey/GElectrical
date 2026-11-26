<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Notification stack. Items come from the host (see createNotificationQueue);
  errors use role="alert", the rest a polite live region. Tone is always
  shown as text and icon, never by colour alone.
-->
<template>
  <section class="eui-notifications" :class="`eui-notifications--${position}`" :aria-label="label">
    <TransitionGroup name="eui-notice" tag="ul" class="eui-notifications__list" aria-live="polite">
      <li
        v-for="item in items"
        :key="item.id"
        class="eui-notice"
        :class="`eui-notice--${item.tone}`"
        :data-notice="item.id"
      >
        <EuiIcon class="eui-notice__icon" :name="icons[item.tone]" :size="18" />
        <div class="eui-notice__body" :role="item.tone === 'danger' ? 'alert' : undefined">
          <div class="eui-notice__title">
            <span class="eui-visually-hidden">{{ toneLabels[item.tone] }}: </span>{{ item.title }}
          </div>
          <div v-if="item.text" class="eui-notice__text">{{ item.text }}</div>
          <div v-if="item.actions?.length" class="eui-notice__actions">
            <button
              v-for="action in item.actions"
              :key="action.id"
              type="button"
              class="eui-notice__action eui-plain-button"
              @click="emit('action', item.id, action.id)"
            >
              {{ action.label }}
            </button>
          </div>
        </div>
        <button
          type="button"
          class="eui-notice__dismiss eui-plain-button"
          :aria-label="`${dismissLabel}: ${item.title}`"
          :title="dismissLabel"
          @click="emit('dismiss', item.id)"
        >
          <EuiIcon name="close" :size="14" />
        </button>
      </li>
    </TransitionGroup>
  </section>
</template>

<script setup lang="ts">
import EuiIcon from "../icons/EuiIcon.vue";
import type { EuiIconName } from "../icons/iconPaths";
import type { EuiNotification } from "./types";

export interface EuiNotificationsProps {
  items: readonly EuiNotification[];
  position?: "bottom-right" | "top-right";
  label?: string;
  dismissLabel?: string;
  /** Screen-reader prefix per tone. */
  toneLabels?: Record<EuiNotification["tone"], string>;
}

withDefaults(defineProps<EuiNotificationsProps>(), {
  position: "bottom-right",
  label: "Notifications",
  dismissLabel: "Dismiss",
  toneLabels: () => ({ info: "Information", success: "Done", warning: "Warning", danger: "Error" }),
});
const emit = defineEmits<{ dismiss: [id: string]; action: [id: string, actionId: string] }>();

const icons: Record<EuiNotification["tone"], EuiIconName> = {
  info: "info",
  success: "success",
  warning: "warning",
  danger: "error",
};
</script>

<style scoped>
.eui-notifications {
  position: fixed;
  right: var(--eui-space-6);
  z-index: 70;
  width: min(360px, calc(100vw - 2 * var(--eui-space-6)));
  pointer-events: none;
}
.eui-notifications--bottom-right {
  bottom: calc(var(--eui-statusbar-height) + var(--eui-space-4));
}
.eui-notifications--top-right {
  top: var(--eui-space-6);
}
.eui-notifications__list {
  display: flex;
  flex-direction: column;
  gap: var(--eui-space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}
.eui-notice {
  display: flex;
  align-items: flex-start;
  gap: var(--eui-space-4);
  padding: var(--eui-space-4) var(--eui-space-4) var(--eui-space-4) var(--eui-space-5);
  background: var(--eui-raised);
  color: var(--eui-text);
  border: var(--eui-border-width) solid var(--eui-border);
  border-left: 4px solid var(--eui-notice-tone);
  border-radius: var(--eui-radius);
  box-shadow: var(--eui-shadow);
  pointer-events: auto;
}
.eui-notice--info {
  --eui-notice-tone: var(--eui-info);
}
.eui-notice--success {
  --eui-notice-tone: var(--eui-success);
}
.eui-notice--warning {
  --eui-notice-tone: var(--eui-warning);
}
.eui-notice--danger {
  --eui-notice-tone: var(--eui-danger);
}
.eui-notice__icon {
  color: var(--eui-notice-tone);
  --eui-icon-accent: var(--eui-notice-tone);
  margin-top: 1px;
}
.eui-notice__body {
  flex: 1;
  min-width: 0;
}
.eui-notice__title {
  font-weight: 600;
  overflow-wrap: anywhere;
}
.eui-notice__text {
  margin-top: var(--eui-space-1);
  color: var(--eui-text-muted);
  overflow-wrap: anywhere;
}
.eui-notice__actions {
  display: flex;
  gap: var(--eui-space-4);
  margin-top: var(--eui-space-3);
}
.eui-notice__action {
  color: var(--eui-accent);
  font-weight: 600;
  text-decoration: underline;
}
.eui-notice__dismiss {
  display: flex;
  padding: var(--eui-space-1);
  border-radius: var(--eui-radius);
  color: var(--eui-text-muted);
}
.eui-notice__dismiss:hover {
  background: var(--eui-hover);
  color: var(--eui-text);
}
.eui-notice-enter-active,
.eui-notice-leave-active {
  transition:
    opacity 0.15s ease,
    transform 0.15s ease;
}
.eui-notice-enter-from,
.eui-notice-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
@media (prefers-reduced-motion: reduce) {
  .eui-notice-enter-active,
  .eui-notice-leave-active {
    transition: none;
  }
}
</style>
