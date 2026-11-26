<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Unit-aware numeric input. Shows the value with `decimal` places, the raw
  value while editing, and the unit beside the field. Enter or focus loss
  commits; Escape reverts. Validation belongs to the host: committed text is
  emitted as typed (arithmetic allowed) together with the parsed number when
  it is a plain number. Text that the host rejects stays in the field with
  the host's `error` message until the value changes or the user reverts.
-->
<template>
  <QInput
    ref="field"
    class="eui-number-input eui-compact"
    :class="{ 'eui-number-input--mixed': mixed && draft === null }"
    dense
    outlined
    hide-bottom-space
    :for="id"
    :model-value="display"
    :aria-label="ariaLabel"
    :aria-invalid="error ? 'true' : undefined"
    :placeholder="mixed && draft === null ? mixedPlaceholder : placeholder"
    :disable="disabled"
    :readonly="readonly"
    :error="!!error"
    :error-message="error"
    :title="tooltip"
    inputmode="decimal"
    autocomplete="off"
    spellcheck="false"
    @update:model-value="inputText"
    @focus="focused = true"
    @blur="blur"
    @keydown="keydown"
  >
    <template v-if="unit" #append>
      <span class="eui-number-input__unit" aria-hidden="true">{{ unit }}</span>
    </template>
  </QInput>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { QInput } from "quasar";
import { formatNumber, parsePlainNumber, rawNumberText } from "./numberText";

export interface EuiNumberCommit {
  /** Text as typed by the user. */
  text: string;
  /** Parsed value when `text` is a plain number; null for expressions or empty text. */
  value: number | null;
}

export interface EuiNumberInputProps {
  modelValue: number | null | undefined;
  /** Accessible name (the unit is appended automatically). Use `id` with an external label instead when one exists. */
  label?: string;
  /** Id of the native input, for an external `<label for>`. */
  id?: string;
  unit?: string;
  /** Display precision; the raw value is shown while editing. */
  decimal?: number;
  disabled?: boolean;
  readonly?: boolean;
  /** Message from the host; the typed text stays visible while set. */
  error?: string;
  placeholder?: string;
  /** Several selected items have different values. */
  mixed?: boolean;
  mixedPlaceholder?: string;
  tooltip?: string;
}

const props = withDefaults(defineProps<EuiNumberInputProps>(), {
  label: undefined,
  id: undefined,
  unit: "",
  decimal: undefined,
  disabled: false,
  readonly: false,
  error: "",
  placeholder: "",
  mixed: false,
  mixedPlaceholder: "Multiple values",
  tooltip: undefined,
});
const emit = defineEmits<{
  "update:modelValue": [value: number];
  commit: [payload: EuiNumberCommit];
  revert: [];
}>();

const field = ref<InstanceType<typeof QInput>>();
const focused = ref(false);
/** Uncommitted or rejected text; null shows the value. */
const draft = ref<string | null>(null);

const ariaLabel = computed(() =>
  props.label ? (props.unit ? `${props.label} (${props.unit})` : props.label) : undefined,
);
const display = computed(() => {
  if (draft.value !== null) return draft.value;
  if (props.mixed) return "";
  return focused.value ? rawNumberText(props.modelValue) : formatNumber(props.modelValue, props.decimal);
});

// A new value from the host replaces any pending text.
watch(
  () => props.modelValue,
  () => {
    draft.value = null;
  },
);

function inputText(value: string | number | null) {
  draft.value = value === null ? "" : String(value);
}

function commit() {
  if (draft.value === null || props.readonly || props.disabled) return;
  const text = draft.value;
  const value = parsePlainNumber(text);
  if (!props.mixed && text.trim() === rawNumberText(props.modelValue)) {
    draft.value = null;
    return;
  }
  // An accepted plain number equal to the current value would leave the draft forever.
  if (value !== null && value === props.modelValue) draft.value = null;
  emit("commit", { text, value });
  if (value !== null) emit("update:modelValue", value);
}

function blur() {
  focused.value = false;
  commit();
}

function keydown(event: KeyboardEvent) {
  if (event.key === "Enter") {
    // Not prevented: an enclosing dialog may apply on the same Enter.
    commit();
  } else if (event.key === "Escape" && draft.value !== null) {
    event.preventDefault();
    event.stopPropagation();
    draft.value = null;
    emit("revert");
  }
}

defineExpose({ focus: () => field.value?.focus() });
</script>

<style scoped>
.eui-number-input :deep(.q-field__native) {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.eui-number-input__unit {
  color: var(--eui-text-muted);
  font-size: var(--eui-font-size-small);
  padding-left: var(--eui-space-2);
}
</style>
