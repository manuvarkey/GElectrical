<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey
  Adapted from GEstimator modern/src/components/DocumentRail.vue at e4e4fb295899feda5253ba216613c70c1f256d4e
  Styles adapted from GEstimator modern/src/style.css at e4e4fb295899feda5253ba216613c70c1f256d4e

  Vertical document rail: one tile per open document with a dirty marker, a
  hover/focus flyout with name and path, and an add tile. One tab stop; Up,
  Down, Home and End move between tiles, Enter or Space activates, Delete
  closes.
-->
<template>
  <nav class="eui-rail" :aria-label="label">
    <ul ref="list" class="eui-rail__list">
      <li v-for="tile in tiles" :key="tile.item.id" class="eui-rail__entry">
        <button
          class="eui-rail__tile eui-plain-button"
          type="button"
          :style="{ '--eui-rail-colour': `var(--eui-doc-${tile.colour})` }"
          :aria-current="tile.active ? 'page' : undefined"
          :aria-describedby="hover?.id === tile.item.id ? `${uid}-flyout` : undefined"
          aria-keyshortcuts="Delete"
          :tabindex="tile.item.id === focusId ? 0 : -1"
          :disabled="busy && !tile.active"
          @click="emit('update:modelValue', tile.item.id)"
          @auxclick="middleClose($event, tile.item.id)"
          @keydown="keydown($event, tile.item.id)"
          @focus="
            focusId = tile.item.id;
            show($event, tile.item.id);
          "
          @blur="hide(tile.item.id)"
          @mouseenter="show($event, tile.item.id)"
          @mouseleave="hide(tile.item.id)"
        >
          <span aria-hidden="true">{{ tile.code }}</span>
          <span class="eui-visually-hidden"
            >{{ tile.name }}{{ tile.item.dirty ? `, ${dirtyLabel.toLowerCase()}` : "" }}</span
          >
          <span v-if="tile.item.dirty" class="eui-rail__dirty" aria-hidden="true" />
        </button>
        <button
          class="eui-rail__close eui-plain-button"
          type="button"
          tabindex="-1"
          :aria-label="`${closeLabel} ${tile.name}`"
          :title="`${closeLabel} ${tile.name}`"
          :disabled="busy"
          @click.stop="emit('close', tile.item.id)"
        >
          <EuiIcon name="close" :size="12" />
        </button>
      </li>
    </ul>
    <button
      class="eui-rail__add eui-plain-button"
      type="button"
      :aria-label="addLabel"
      :title="addLabel"
      :disabled="busy"
      @click="emit('add')"
    >
      <EuiIcon name="plus" :size="16" />
    </button>
    <div
      v-if="hoverTile"
      :id="`${uid}-flyout`"
      class="eui-rail__flyout"
      :style="{ top: `${hover!.top}px` }"
      role="tooltip"
    >
      <div class="eui-rail__flyout-name">
        <span class="eui-rail__dot" :style="{ '--eui-rail-colour': `var(--eui-doc-${hoverTile.colour})` }" />{{
          hoverTile.name
        }}
      </div>
      <div class="eui-rail__flyout-path">{{ hoverTile.item.path || unsavedLabel }}</div>
      <div v-if="hoverTile.item.dirty" class="eui-rail__flyout-dirty">{{ dirtyLabel }}</div>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, ref, useId, watch } from "vue";
import EuiIcon from "../icons/EuiIcon.vue";
import { moveRovingFocus } from "../composables/rovingFocus";
import { documentCode, documentColourIndex } from "./documentTiles";
import type { EuiDocumentItem } from "./types";

export interface EuiDocumentRailProps {
  items: EuiDocumentItem[];
  /** Id of the active document. */
  modelValue?: string;
  busy?: boolean;
  label?: string;
  addLabel?: string;
  closeLabel?: string;
  untitledLabel?: string;
  unsavedLabel?: string;
  dirtyLabel?: string;
}

const props = withDefaults(defineProps<EuiDocumentRailProps>(), {
  modelValue: undefined,
  busy: false,
  label: "Open documents",
  addLabel: "New document",
  closeLabel: "Close",
  untitledLabel: "Untitled",
  unsavedLabel: "Not saved to a file yet",
  dirtyLabel: "Unsaved changes",
});
const emit = defineEmits<{ "update:modelValue": [id: string]; close: [id: string]; add: [] }>();

const uid = useId();
const list = ref<HTMLElement>();
const hover = ref<{ id: string; top: number }>();
const focusId = ref<string>();

const tiles = computed(() =>
  props.items.map((item) => {
    const name = item.title || props.untitledLabel;
    const colour = item.colour && item.colour >= 1 && item.colour <= 8 ? item.colour : documentColourIndex(item.id);
    return { item, name, code: documentCode(name), colour, active: item.id === props.modelValue };
  }),
);
const hoverTile = computed(() => tiles.value.find((tile) => tile.item.id === hover.value?.id));

// The roving tab stop returns to the active document whenever it or the list changes.
watch(
  () => [props.modelValue, props.items.map((item) => item.id).join("\n")],
  () => {
    focusId.value = props.items.some((item) => item.id === props.modelValue) ? props.modelValue : props.items[0]?.id;
  },
  { immediate: true },
);

function show(event: Event, id: string) {
  hover.value = { id, top: (event.currentTarget as HTMLElement).getBoundingClientRect().top };
}

function hide(id: string) {
  if (hover.value?.id === id) hover.value = undefined;
}

function middleClose(event: MouseEvent, id: string) {
  if (event.button !== 1) return;
  event.preventDefault();
  if (!props.busy) emit("close", id);
}

function keydown(event: KeyboardEvent, id: string) {
  const items = Array.from(list.value?.querySelectorAll<HTMLElement>(".eui-rail__tile:not(:disabled)") ?? []);
  if (moveRovingFocus(event, items, "vertical") >= 0) return;
  if (event.key === "Delete" && !props.busy) {
    event.preventDefault();
    emit("close", id);
  }
}
</script>

<style scoped>
.eui-rail {
  position: relative;
  flex: none;
  width: var(--eui-rail-width);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--eui-space-3);
  padding: var(--eui-space-4) 0;
  background: var(--eui-frame);
  border-right: var(--eui-border-width) solid var(--eui-border);
  overflow-x: hidden;
  overflow-y: auto;
}
.eui-rail__list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--eui-space-3);
  margin: 0;
  padding: 0;
  list-style: none;
}
.eui-rail__entry {
  position: relative;
}
.eui-rail__tile {
  position: relative;
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: var(--eui-radius);
  background: var(--eui-panel);
  color: var(--eui-text-muted);
  font-weight: 700;
  font-size: var(--eui-font-size-small);
  letter-spacing: 0.02em;
}
.eui-rail__tile:hover:not(:disabled) {
  color: var(--eui-text);
  border-color: var(--eui-text-hint);
}
.eui-rail__tile:disabled {
  color: var(--eui-text-disabled);
}
.eui-rail__tile[aria-current="page"] {
  background: var(--eui-rail-colour);
  border-color: var(--eui-rail-colour);
  color: var(--eui-on-strong);
}
.eui-rail__tile[aria-current="page"]::before {
  content: "";
  position: absolute;
  left: -8px;
  top: 7px;
  bottom: 7px;
  width: 3px;
  border-radius: 2px;
  background: var(--eui-accent);
}
.eui-rail__tile:focus-visible,
.eui-rail__add:focus-visible {
  outline-offset: 2px;
}
.eui-rail__dirty {
  position: absolute;
  top: -3px;
  right: -3px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--eui-warning);
  border: 2px solid var(--eui-frame);
}
.eui-rail__close {
  position: absolute;
  top: -6px;
  left: -6px;
  width: 16px;
  height: 16px;
  display: none;
  align-items: center;
  justify-content: center;
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: 50%;
  background: var(--eui-raised);
  color: var(--eui-text-muted);
}
.eui-rail__entry:hover .eui-rail__close {
  display: flex;
}
.eui-rail__close:hover:not(:disabled) {
  color: var(--eui-text);
}
.eui-rail__add {
  width: 34px;
  height: 34px;
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1.5px dashed var(--eui-border);
  border-radius: var(--eui-radius);
  color: var(--eui-text-muted);
}
.eui-rail__add:hover:not(:disabled) {
  border-color: var(--eui-accent);
  color: var(--eui-text);
}
.eui-rail__flyout {
  position: fixed;
  left: calc(var(--eui-rail-width) + var(--eui-space-3));
  z-index: 60;
  width: 248px;
  padding: var(--eui-space-4) var(--eui-space-5);
  background: var(--eui-raised);
  color: var(--eui-text);
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: var(--eui-radius);
  box-shadow: var(--eui-shadow);
  pointer-events: none;
  font-size: var(--eui-font-size-small);
}
.eui-rail__flyout-name {
  display: flex;
  align-items: center;
  gap: var(--eui-space-4);
  font-weight: 650;
  overflow-wrap: anywhere;
}
.eui-rail__dot {
  width: 9px;
  height: 9px;
  flex: none;
  border-radius: 50%;
  background: var(--eui-rail-colour);
}
.eui-rail__flyout-path {
  margin-top: var(--eui-space-3);
  color: var(--eui-text-muted);
  overflow-wrap: anywhere;
}
.eui-rail__flyout-dirty {
  margin-top: var(--eui-space-2);
  color: var(--eui-warning);
}
</style>
