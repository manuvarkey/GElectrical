<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey
  Adapted from GEstimator modern/src/components/PersistentDialog.vue at e4e4fb295899feda5253ba216613c70c1f256d4e

  Modal dialog for bounded tasks, built on Quasar's QDialog (focus trap and
  focus restore). Enter applies (outside multi-line fields and buttons),
  Escape cancels; both are blocked while busy.
-->
<template>
  <QDialog
    :model-value="modelValue"
    :aria-labelledby="`${uid}-title`"
    :aria-describedby="$slots.description ? `${uid}-description` : undefined"
    no-backdrop-dismiss
    no-esc-dismiss
    :transition-duration="120"
    @update:model-value="update"
    @keydown="keydown"
    @show="emit('show')"
  >
    <QCard class="eui-dialog" :style="{ width: `${width}px` }">
      <header class="eui-dialog__header">
        <h2 :id="`${uid}-title`" class="eui-dialog__title">{{ title }}</h2>
        <button
          type="button"
          class="eui-dialog__close eui-plain-button"
          :aria-label="closeLabel"
          :title="closeLabel"
          :disabled="busy"
          @click="cancel"
        >
          <EuiIcon name="close" :size="16" />
        </button>
      </header>
      <p v-if="$slots.description" :id="`${uid}-description`" class="eui-dialog__description">
        <slot name="description" />
      </p>
      <div class="eui-dialog__content">
        <slot />
      </div>
      <footer v-if="applyLabel || $slots.actions" class="eui-dialog__actions">
        <slot name="actions">
          <QBtn
            class="eui-compact eui-dialog__cancel"
            flat
            no-caps
            :label="cancelLabel"
            :disable="busy"
            @click="cancel"
          />
          <QBtn
            class="eui-compact eui-dialog__apply"
            unelevated
            no-caps
            :label="applyLabel"
            :loading="busy"
            :disable="applyDisabled || busy"
            @click="apply"
          />
        </slot>
      </footer>
    </QCard>
  </QDialog>
</template>

<script setup lang="ts">
import { useId } from "vue";
import { QBtn, QCard, QDialog } from "quasar";
import EuiIcon from "../icons/EuiIcon.vue";

export interface EuiDialogProps {
  modelValue: boolean;
  title: string;
  /** Label of the primary button; omit for dialogs with custom actions or none. */
  applyLabel?: string;
  cancelLabel?: string;
  closeLabel?: string;
  applyDisabled?: boolean;
  /** Blocks closing and applying while an operation runs. */
  busy?: boolean;
  /** Card width in px (capped to the viewport). */
  width?: number;
}

const props = withDefaults(defineProps<EuiDialogProps>(), {
  applyLabel: "",
  cancelLabel: "Cancel",
  closeLabel: "Close dialog",
  applyDisabled: false,
  busy: false,
  width: 480,
});
const emit = defineEmits<{ "update:modelValue": [value: boolean]; apply: []; cancel: []; show: [] }>();

const uid = useId();

function update(value: boolean) {
  if (!value && props.busy) return;
  emit("update:modelValue", value);
}

function cancel() {
  if (props.busy) return;
  emit("cancel");
  emit("update:modelValue", false);
}

function apply() {
  if (props.busy || props.applyDisabled || !props.applyLabel) return;
  emit("apply");
}

function keydown(event: KeyboardEvent) {
  if (event.key === "Escape") {
    // Leave Escape to an open child popup (for example a selector menu).
    if (event.defaultPrevented || (event.target as HTMLElement).closest("[aria-expanded='true']")) return;
    event.preventDefault();
    cancel();
    return;
  }
  if (event.key !== "Enter" || event.defaultPrevented || event.shiftKey || event.altKey || event.ctrlKey) return;
  const target = event.target as HTMLElement;
  if (target.closest("textarea, button, a, [role='combobox'], [role='listbox'], [role='checkbox']")) return;
  event.preventDefault();
  apply();
}
</script>

<style scoped>
.eui-dialog {
  display: flex;
  flex-direction: column;
  max-width: calc(100vw - 2 * var(--eui-space-6));
  max-height: calc(100vh - 2 * var(--eui-space-6));
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: var(--eui-radius-large);
  box-shadow: var(--eui-shadow);
  font-family: var(--eui-font-family);
  font-size: var(--eui-font-size);
}
.eui-dialog__header {
  display: flex;
  align-items: center;
  gap: var(--eui-space-4);
  padding: var(--eui-space-4) var(--eui-space-4) var(--eui-space-4) var(--eui-space-6);
  border-bottom: var(--eui-border-width) solid var(--eui-border-soft);
}
.eui-dialog__title {
  flex: 1;
  margin: 0;
  font-size: var(--eui-font-size-heading);
  font-weight: 600;
  line-height: var(--eui-line-height);
  letter-spacing: normal;
}
.eui-dialog__close {
  display: flex;
  padding: var(--eui-space-2);
  border-radius: var(--eui-radius);
  color: var(--eui-text-muted);
}
.eui-dialog__close:hover:not(:disabled) {
  background: var(--eui-hover);
  color: var(--eui-text);
}
.eui-dialog__description {
  margin: 0;
  padding: var(--eui-space-4) var(--eui-space-6) 0;
  color: var(--eui-text-muted);
}
.eui-dialog__content {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: var(--eui-space-5) var(--eui-space-6);
}
.eui-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--eui-space-4);
  padding: var(--eui-space-4) var(--eui-space-6);
  border-top: var(--eui-border-width) solid var(--eui-border-soft);
}
.eui-dialog__cancel {
  color: var(--eui-text);
}
.eui-dialog__apply {
  background: var(--eui-accent-fill);
  color: var(--eui-on-accent);
  font-weight: 600;
}
</style>
