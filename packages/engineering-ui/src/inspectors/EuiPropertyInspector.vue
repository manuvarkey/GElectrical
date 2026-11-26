<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey

  Schema-driven property inspector. Renders one row per visible field from
  `fields` (backend FieldSchema shape) with values from `values`, and emits
  `change` with the committed text or value. It never validates: messages in
  `errors` come from the host and keep the typed text visible. Keyboard: Tab
  moves between fields, Enter commits, Escape reverts, Space toggles a check
  box, Alt+Down or Enter opens a selector.
-->
<template>
  <section class="eui-inspector" :aria-label="label">
    <div v-if="filterable" class="eui-inspector__filter">
      <label :for="`${uid}-filter`" class="eui-visually-hidden">{{ filterLabel }}</label>
      <EuiIcon name="search" :size="14" />
      <input
        :id="`${uid}-filter`"
        v-model="filter"
        class="eui-inspector__filter-input"
        type="search"
        :placeholder="filterLabel"
        autocomplete="off"
      />
    </div>
    <p v-if="!rows.length" class="eui-inspector__empty">{{ filter ? noMatchLabel : emptyLabel }}</p>
    <div v-else class="eui-inspector__grid">
      <template v-for="row in rows" :key="row.field.code">
        <h3 v-if="row.field.type === 'heading'" class="eui-inspector__heading">{{ row.field.caption }}</h3>
        <template v-else>
          <component
            :is="row.kind === 'action' ? 'span' : 'label'"
            :id="`${row.id}-label`"
            class="eui-inspector__caption"
            :class="{ 'eui-inspector__caption--error': !!errors[row.field.code] }"
            :for="row.kind === 'action' ? undefined : row.id"
            :title="row.field.tooltip || undefined"
          >
            {{ row.field.caption
            }}<span v-if="row.field.unit" class="eui-visually-hidden"> ({{ row.field.unit }})</span>
          </component>
          <div class="eui-inspector__control" :data-field="row.field.code">
            <EuiNumberInput
              v-if="row.kind === 'number'"
              :id="row.id"
              :model-value="numberValue(row.field.code)"
              :unit="row.field.unit"
              :decimal="row.field.type === 'int' ? 0 : row.field.decimal"
              :readonly="row.readonly"
              :error="errors[row.field.code]"
              :mixed="row.mixed"
              :mixed-placeholder="mixedLabel"
              :tooltip="row.field.tooltip"
              @commit="emit('change', { code: row.field.code, value: $event.text, number: $event.value })"
            />
            <QSelect
              v-else-if="row.kind === 'select'"
              class="eui-compact eui-inspector__select"
              dense
              outlined
              options-dense
              hide-bottom-space
              :for="row.id"
              :model-value="row.mixed ? null : stringValue(row.field.code)"
              :options="row.field.selection_list ?? []"
              :placeholder="row.mixed ? mixedLabel : undefined"
              :readonly="row.readonly"
              :error="!!errors[row.field.code]"
              :error-message="errors[row.field.code]"
              :title="row.field.tooltip"
              @update:model-value="emit('change', { code: row.field.code, value: String($event) })"
            />
            <input
              v-else-if="row.kind === 'check'"
              :id="row.id"
              class="eui-inspector__check"
              type="checkbox"
              :checked="!row.mixed && Boolean(values[row.field.code])"
              :indeterminate="row.mixed"
              :disabled="row.readonly"
              :aria-invalid="errors[row.field.code] ? 'true' : undefined"
              :title="row.field.tooltip"
              @change="emit('change', { code: row.field.code, value: ($event.target as HTMLInputElement).checked })"
            />
            <div v-else-if="row.kind === 'action'" class="eui-inspector__action">
              <span class="eui-inspector__value" :title="stringValue(row.field.code)">{{
                row.mixed ? mixedLabel : stringValue(row.field.code)
              }}</span>
              <QBtn
                class="eui-compact"
                flat
                no-caps
                :label="editLabel"
                :aria-label="`${editLabel} ${row.field.caption}`"
                :aria-describedby="`${row.id}-label`"
                :disable="row.readonly"
                @click="emit('edit', row.field.code)"
              />
            </div>
            <InspectorTextField
              v-else
              :id="row.id"
              :model-value="stringValue(row.field.code)"
              :multiline="row.field.type === 'multiline_str'"
              :readonly="row.readonly"
              :error="errors[row.field.code]"
              :mixed="row.mixed"
              :mixed-placeholder="mixedLabel"
              :tooltip="row.field.tooltip"
              @commit="emit('change', { code: row.field.code, value: $event })"
            />
            <div v-if="errors[row.field.code] && row.kind === 'check'" class="eui-inspector__error" role="alert">
              {{ errors[row.field.code] }}
            </div>
          </div>
        </template>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, useId } from "vue";
import { QBtn, QSelect } from "quasar";
import EuiIcon from "../icons/EuiIcon.vue";
import EuiNumberInput from "../controls/EuiNumberInput.vue";
import InspectorTextField from "./InspectorTextField.vue";
import type { EuiFieldChange, EuiFieldSchema, EuiFieldValue } from "./types";

export interface EuiPropertyInspectorProps {
  fields: EuiFieldSchema[];
  values: Record<string, EuiFieldValue | undefined>;
  /** Host validation messages by field code. */
  errors?: Record<string, string>;
  /** Codes whose values differ across a multiple selection. */
  mixed?: string[];
  /** Shows every field read-only. */
  readonly?: boolean;
  /** Shows a caption filter above the fields. */
  filterable?: boolean;
  label?: string;
  filterLabel?: string;
  emptyLabel?: string;
  noMatchLabel?: string;
  mixedLabel?: string;
  editLabel?: string;
}

const props = withDefaults(defineProps<EuiPropertyInspectorProps>(), {
  errors: () => ({}),
  mixed: () => [],
  readonly: false,
  filterable: false,
  label: "Properties",
  filterLabel: "Filter properties",
  emptyLabel: "No properties",
  noMatchLabel: "No matching properties",
  mixedLabel: "Multiple values",
  editLabel: "Edit…",
});
const emit = defineEmits<{ change: [change: EuiFieldChange]; edit: [code: string] }>();

const uid = useId();
const filter = ref("");

type RowKind = "number" | "select" | "check" | "action" | "text";

function kindOf(field: EuiFieldSchema): RowKind {
  if (field.selection_list?.length) return "select";
  if (field.type === "int" || field.type === "float") return "number";
  if (field.type === "bool") return "check";
  if (field.type === "graph" || field.type === "data" || field.type === "font") return "action";
  return "text";
}

const rows = computed(() => {
  const query = filter.value.trim().toLowerCase();
  const visible = props.fields.filter((field) => field.enabled !== false);
  const matched = query
    ? visible.filter((field) => field.type !== "heading" && field.caption.toLowerCase().includes(query))
    : visible;
  return matched.map((field) => ({
    field,
    kind: kindOf(field),
    id: `${uid}-${field.code}`,
    readonly: props.readonly || field.editable === false,
    mixed: props.mixed.includes(field.code),
  }));
});

function numberValue(code: string): number | null {
  const value = props.values[code];
  return typeof value === "number" ? value : null;
}

function stringValue(code: string): string {
  const value = props.values[code];
  return value === null || value === undefined ? "" : String(value);
}
</script>

<style scoped>
.eui-inspector {
  display: flex;
  flex-direction: column;
  min-width: 0;
  color: var(--eui-text);
  background: var(--eui-panel);
}
.eui-inspector__filter {
  display: flex;
  align-items: center;
  gap: var(--eui-space-3);
  margin: var(--eui-space-4);
  padding: 0 var(--eui-space-3);
  height: var(--eui-control-height);
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: var(--eui-radius);
  background: var(--eui-field);
  color: var(--eui-text-muted);
}
.eui-inspector__filter:focus-within {
  outline: var(--eui-focus-width) solid var(--eui-focus-ring);
  outline-offset: -1px;
}
.eui-inspector__filter-input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--eui-text);
  font: inherit;
}
.eui-inspector__filter-input::placeholder {
  color: var(--eui-text-hint);
}
.eui-inspector__empty {
  margin: var(--eui-space-5) var(--eui-space-4);
  color: var(--eui-text-muted);
}
.eui-inspector__grid {
  display: grid;
  grid-template-columns: minmax(80px, 40%) minmax(0, 1fr);
  align-items: start;
  gap: var(--eui-space-2) var(--eui-space-4);
  padding: var(--eui-space-2) var(--eui-space-4) var(--eui-space-4);
}
.eui-inspector__heading {
  grid-column: 1 / -1;
  margin: var(--eui-space-4) 0 0;
  padding-bottom: var(--eui-space-1);
  border-bottom: var(--eui-border-width) solid var(--eui-border-soft);
  font-size: var(--eui-font-size-small);
  font-weight: 600;
  color: var(--eui-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  line-height: var(--eui-line-height);
}
.eui-inspector__caption {
  display: flex;
  align-items: center;
  min-height: var(--eui-control-height);
  color: var(--eui-text-muted);
  overflow-wrap: anywhere;
}
.eui-inspector__caption--error {
  color: var(--eui-danger);
}
.eui-inspector__control {
  min-width: 0;
}
.eui-inspector__check {
  width: 16px;
  height: 16px;
  margin: calc((var(--eui-control-height) - 16px) / 2) 0;
  accent-color: var(--eui-accent-fill);
}
.eui-inspector__check:focus-visible {
  outline: var(--eui-focus-width) solid var(--eui-focus-ring);
  outline-offset: 2px;
}
.eui-inspector__action {
  display: flex;
  align-items: center;
  gap: var(--eui-space-3);
  min-height: var(--eui-control-height);
}
.eui-inspector__value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.eui-inspector__action :deep(.q-btn) {
  color: var(--eui-accent);
}
.eui-inspector__error {
  color: var(--eui-danger);
  font-size: var(--eui-font-size-caption);
}
</style>
