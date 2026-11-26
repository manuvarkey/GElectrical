<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Text field used by the property inspector: Enter (Ctrl+Enter when
  multi-line) or focus loss commits, Escape reverts. Rejected text stays
  with the host's message until the value changes.
-->
<template>
  <QInput
    class="eui-compact"
    dense
    outlined
    hide-bottom-space
    :for="id"
    :type="multiline ? 'textarea' : 'text'"
    :autogrow="multiline"
    :model-value="draft ?? (mixed ? '' : modelValue)"
    :placeholder="mixed && draft === null ? mixedPlaceholder : undefined"
    :readonly="readonly"
    :disable="disabled"
    :error="!!error"
    :error-message="error"
    :aria-invalid="error ? 'true' : undefined"
    :title="tooltip"
    autocomplete="off"
    @update:model-value="draft = $event === null ? '' : String($event)"
    @blur="commit"
    @keydown="keydown"
  />
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { QInput } from "quasar";

const props = defineProps<{
  id: string;
  modelValue: string;
  multiline?: boolean;
  readonly?: boolean;
  disabled?: boolean;
  error?: string;
  mixed?: boolean;
  mixedPlaceholder: string;
  tooltip?: string;
}>();
const emit = defineEmits<{ commit: [value: string] }>();

const draft = ref<string | null>(null);

watch(
  () => props.modelValue,
  () => {
    draft.value = null;
  },
);

function commit() {
  if (draft.value === null || props.readonly || props.disabled) return;
  const value = draft.value;
  if (value === props.modelValue && !props.mixed) {
    draft.value = null;
    return;
  }
  emit("commit", value);
}

function keydown(event: KeyboardEvent) {
  if (event.key === "Enter" && (!props.multiline || event.ctrlKey)) {
    if (props.multiline) event.preventDefault();
    commit();
  } else if (event.key === "Escape" && draft.value !== null) {
    event.preventDefault();
    event.stopPropagation();
    draft.value = null;
  }
}
</script>
