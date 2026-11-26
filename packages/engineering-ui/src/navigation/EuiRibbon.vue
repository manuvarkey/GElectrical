<!--
  SPDX-License-Identifier: MIT
  Copyright (c) 2026 Manu Varkey
  Adapted from GEstimator modern/src/components/RibbonToolbar.vue at e4e4fb295899feda5253ba216613c70c1f256d4e
  Styles adapted from GEstimator modern/src/style.css at e4e4fb295899feda5253ba216613c70c1f256d4e

  Data-driven ribbon: a tab strip (one tab stop, arrow keys switch tabs) and
  a command toolbar for the active tab (one tab stop, arrow keys move between
  commands). Commands are reported by id; the host decides what they do.
-->
<template>
  <div class="eui-ribbon" :class="{ 'eui-ribbon--busy': busy }">
    <div class="eui-ribbon__strip">
      <div ref="tabList" class="eui-ribbon__tabs" role="tablist" :aria-label="label">
        <button
          v-for="tab in tabs"
          :id="`${uid}-tab-${tab.id}`"
          :key="tab.id"
          class="eui-ribbon__tab eui-plain-button"
          :class="{ 'eui-ribbon__tab--contextual': tab.contextual }"
          type="button"
          role="tab"
          :aria-selected="tab.id === active?.id"
          :aria-controls="`${uid}-panel`"
          :tabindex="tab.id === active?.id ? 0 : -1"
          @click="select(tab.id)"
          @keydown="tabKeydown"
        >
          {{ tab.label }}
        </button>
      </div>
      <div v-if="$slots.end" class="eui-ribbon__end"><slot name="end" /></div>
    </div>
    <div
      v-if="active"
      :id="`${uid}-panel`"
      ref="panel"
      class="eui-ribbon__panel"
      role="tabpanel"
      :aria-labelledby="`${uid}-tab-${active.id}`"
    >
      <div
        class="eui-ribbon__toolbar"
        role="toolbar"
        :aria-label="`${active.label} commands`"
        @keydown="commandKeydown"
      >
        <div
          v-for="group in active.groups"
          :key="group.id"
          class="eui-ribbon__group"
          role="group"
          :aria-label="group.label"
        >
          <div class="eui-ribbon__commands">
            <button
              v-for="command in group.commands"
              :key="command.id"
              class="eui-ribbon__command eui-plain-button"
              :class="{ 'eui-ribbon__command--danger': command.danger }"
              type="button"
              :data-command="command.id"
              :data-keep-label="command.keepLabel || command.danger || undefined"
              :aria-label="command.label"
              :aria-pressed="command.pressed === undefined ? undefined : command.pressed"
              :aria-keyshortcuts="ariaShortcut(command.shortcut)"
              :title="tooltip(command)"
              :disabled="busy || command.disabled"
              :tabindex="command.id === focusId ? 0 : -1"
              @click="run(command)"
              @focus="focusId = command.id"
            >
              <EuiIcon :name="command.icon" :size="24" />
              <span class="eui-ribbon__label" aria-hidden="true">{{ command.label }}</span>
            </button>
          </div>
          <div class="eui-ribbon__group-label" aria-hidden="true">{{ group.label }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
import EuiIcon from "../icons/EuiIcon.vue";
import { moveRovingFocus } from "../composables/rovingFocus";
import { fitRibbon } from "./ribbonFit";
import type { EuiRibbonCommand, EuiRibbonTab } from "./types";

export interface EuiRibbonProps {
  tabs: EuiRibbonTab[];
  /** Accessible name of the tab strip. */
  label?: string;
  /** Disables every command while a long operation runs. */
  busy?: boolean;
}

const props = withDefaults(defineProps<EuiRibbonProps>(), { label: "Ribbon", busy: false });
const activeId = defineModel<string>({ default: "" });
const emit = defineEmits<{ command: [id: string] }>();

const uid = useId();
const tabList = ref<HTMLElement>();
const panel = ref<HTMLElement>();
const active = computed(() => props.tabs.find((tab) => tab.id === activeId.value) ?? props.tabs[0]);
const enabledCommands = computed(() =>
  (active.value?.groups ?? []).flatMap((group) => group.commands).filter((command) => !command.disabled),
);
const focusId = ref<string>();

watch(
  enabledCommands,
  (commands) => {
    if (!commands.some((command) => command.id === focusId.value)) focusId.value = commands[0]?.id;
  },
  { immediate: true },
);

function select(id: string) {
  activeId.value = id;
}

function tabKeydown(event: KeyboardEvent) {
  const items = Array.from(tabList.value?.querySelectorAll<HTMLElement>('[role="tab"]') ?? []);
  const index = moveRovingFocus(event, items, "horizontal");
  // Automatic activation: moving focus selects the tab.
  if (index >= 0) select(props.tabs[index]!.id);
}

function commandKeydown(event: KeyboardEvent) {
  const items = Array.from(panel.value?.querySelectorAll<HTMLElement>(".eui-ribbon__command:not(:disabled)") ?? []);
  moveRovingFocus(event, items, "horizontal");
}

function run(command: EuiRibbonCommand) {
  if (!props.busy && !command.disabled) emit("command", command.id);
}

function tooltip(command: EuiRibbonCommand) {
  const text = command.tooltip || command.label;
  return command.shortcut ? `${text} (${command.shortcut})` : text;
}

function ariaShortcut(shortcut?: string) {
  return shortcut ? shortcut.replace(/Ctrl/g, "Control") : undefined;
}

let resize: ResizeObserver | undefined;
let frame = 0;
function fit() {
  cancelAnimationFrame(frame);
  frame = requestAnimationFrame(() => {
    if (panel.value) fitRibbon(panel.value);
  });
}

watch(
  () => [active.value, props.tabs],
  () => nextTick(fit),
  { deep: true },
);

onMounted(() => {
  if (typeof ResizeObserver === "function" && panel.value) {
    resize = new ResizeObserver(fit);
    resize.observe(panel.value);
  }
  document.fonts?.addEventListener?.("loadingdone", fit);
  fit();
});

onBeforeUnmount(() => {
  resize?.disconnect();
  document.fonts?.removeEventListener?.("loadingdone", fit);
  cancelAnimationFrame(frame);
});

defineExpose({ fit });
</script>

<style scoped>
.eui-ribbon {
  display: flex;
  flex-direction: column;
  background: var(--eui-panel);
  color: var(--eui-text);
  border-bottom: var(--eui-border-width) solid var(--eui-border);
  min-width: 0;
}
.eui-ribbon__strip {
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  border-bottom: var(--eui-border-width) solid var(--eui-border-soft);
  min-height: 30px;
  padding: 0 var(--eui-space-5);
}
.eui-ribbon__tabs {
  display: flex;
  gap: var(--eui-space-1);
  overflow: hidden;
}
.eui-ribbon__tab {
  padding: 0 var(--eui-space-5);
  border-bottom: 2px solid transparent;
  color: var(--eui-text-muted);
  white-space: nowrap;
}
.eui-ribbon__tab:hover {
  background: var(--eui-hover);
}
.eui-ribbon__tab[aria-selected="true"] {
  color: var(--eui-accent);
  border-bottom-color: var(--eui-accent);
}
.eui-ribbon__tab--contextual {
  color: var(--eui-icon-accent);
  font-weight: 600;
}
.eui-ribbon__tab:focus-visible {
  outline-offset: -2px;
}
.eui-ribbon__end {
  display: flex;
  align-items: center;
  gap: var(--eui-space-2);
}
.eui-ribbon__panel {
  height: calc(56px + 2.1em);
  padding: var(--eui-space-2) var(--eui-space-3);
  overflow: hidden;
}
.eui-ribbon__toolbar {
  display: flex;
  align-items: stretch;
  height: 100%;
}
.eui-ribbon__group {
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  gap: var(--eui-space-1);
  padding: 0 var(--eui-space-2);
  border-right: var(--eui-border-width) solid var(--eui-border);
}
.eui-ribbon__group:last-child {
  border-right: 0;
}
.eui-ribbon__commands {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: max-content;
  grid-template-rows: repeat(3, calc((32px + 2.1em) / 3));
  align-content: start;
  flex: 1;
  gap: 1px var(--eui-space-1);
}
.eui-ribbon__group-label {
  font-size: var(--eui-font-size-caption);
  color: var(--eui-text-hint);
  text-align: center;
  text-transform: uppercase;
  line-height: 1;
}
.eui-ribbon__command {
  grid-row: span 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  width: var(--eui-ribbon-button-width, auto);
  min-width: 52px;
  max-width: 88px;
  padding: var(--eui-space-1) var(--eui-space-2);
  border-radius: var(--eui-radius-large);
  text-align: center;
  color: var(--eui-text);
}
.eui-ribbon__command .eui-icon {
  color: var(--eui-icon);
}
.eui-ribbon__command:hover:not(:disabled),
.eui-ribbon__command[aria-pressed="true"] {
  background: var(--eui-accent-soft);
  color: var(--eui-accent);
}
.eui-ribbon__command:disabled {
  color: var(--eui-text-disabled);
}
.eui-ribbon__command:disabled .eui-icon {
  color: var(--eui-text-disabled);
}
.eui-ribbon__command--danger:not(:disabled) .eui-icon {
  color: var(--eui-danger);
}
.eui-ribbon__label {
  display: -webkit-box;
  overflow: hidden;
  white-space: normal;
  overflow-wrap: anywhere;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-height: 1.05;
  min-height: 2.1em;
  max-width: var(--eui-ribbon-caption-width, 80px);
}
.eui-ribbon__command[data-mini] {
  grid-row: auto;
  flex-direction: row;
  width: 30px;
  min-width: 30px;
  max-width: 30px;
  padding: 0 var(--eui-space-2);
}
.eui-ribbon__command[data-mini] .eui-icon {
  width: 20px;
  height: 20px;
}
.eui-ribbon__command[data-mini] .eui-ribbon__label {
  display: none;
}
</style>
