<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Placeholder for the schematic editor (M7 proof of concept). -->
<template>
  <div class="schematic">
    <div class="schematic__sheets" role="tablist" aria-label="Sheets">
      <button
        v-for="sheet in sheets"
        :key="sheet"
        type="button"
        role="tab"
        class="schematic__sheet eui-plain-button"
        :aria-selected="sheet === active"
        :tabindex="sheet === active ? 0 : -1"
        @click="active = sheet"
      >
        {{ sheet }}
      </button>
    </div>
    <svg class="schematic__canvas" role="img" aria-label="Schematic placeholder: transformer feeding a load">
      <defs>
        <pattern id="schematic-grid" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0H0V20" fill="none" class="schematic__grid" />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#schematic-grid)" />
      <g class="schematic__symbol" transform="translate(200 60)">
        <circle cx="0" cy="30" r="22" />
        <circle cx="0" cy="62" r="22" />
        <path d="M0 0V8 M0 84V140 M-80 140H80 M40 140V200" />
        <path class="schematic__selected" d="M30 200H50L40 220Z" />
        <text x="60" y="210">L1 · 12.50 kVA</text>
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const sheets = ["Sheet 1", "Sheet 2"];
const active = ref(sheets[0]);
</script>

<style scoped>
.schematic {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.schematic__sheets {
  display: flex;
  gap: var(--eui-space-1);
  padding: 0 var(--eui-space-4);
  background: var(--eui-panel);
  border-bottom: var(--eui-border-width) solid var(--eui-border-soft);
}
.schematic__sheet {
  padding: var(--eui-space-2) var(--eui-space-5);
  color: var(--eui-text-muted);
  border-bottom: 2px solid transparent;
}
.schematic__sheet[aria-selected="true"] {
  color: var(--eui-accent);
  border-bottom-color: var(--eui-accent);
}
.schematic__canvas {
  flex: 1;
  width: 100%;
  background: var(--eui-schematic-background);
}
.schematic__grid {
  stroke: var(--eui-schematic-grid);
}
.schematic__symbol {
  fill: none;
  stroke: var(--eui-schematic-normal);
  stroke-width: 2;
}
.schematic__symbol text {
  fill: var(--eui-schematic-normal);
  stroke: none;
  font-size: 13px;
}
.schematic__selected {
  stroke: var(--eui-schematic-selected);
}
</style>
