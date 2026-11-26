<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<template>
  <div class="palette">
    <div class="palette__search">
      <label for="palette-search" class="eui-visually-hidden">Search components</label>
      <EuiIcon name="search" :size="14" />
      <input id="palette-search" v-model="query" type="search" placeholder="Search components" autocomplete="off" />
    </div>
    <section v-for="group in groups" :key="group.group" class="palette__group" :aria-label="group.group">
      <h2 class="palette__heading">{{ group.group }}</h2>
      <ul class="palette__list">
        <li v-for="item in group.items" :key="item.code">
          <button type="button" class="palette__item eui-plain-button" @click="emit('insert', item.code)">
            <EuiIcon :name="item.icon" :size="20" />{{ item.name }}
          </button>
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { EuiIcon } from "@kavilgroup/engineering-ui/icons";
import { mockPalette } from "../mock/project";

const emit = defineEmits<{ insert: [code: string] }>();
const query = ref("");
const groups = computed(() => {
  const text = query.value.trim().toLowerCase();
  return mockPalette
    .map((group) => ({ ...group, items: group.items.filter((item) => item.name.toLowerCase().includes(text)) }))
    .filter((group) => group.items.length);
});
</script>

<style scoped>
.palette {
  padding: var(--eui-space-4);
}
.palette__search {
  display: flex;
  align-items: center;
  gap: var(--eui-space-3);
  height: var(--eui-control-height);
  padding: 0 var(--eui-space-3);
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: var(--eui-radius);
  background: var(--eui-field);
  color: var(--eui-text-muted);
}
.palette__search:focus-within {
  outline: var(--eui-focus-width) solid var(--eui-focus-ring);
}
.palette__search input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--eui-text);
  font: inherit;
}
.palette__heading {
  margin: var(--eui-space-5) 0 var(--eui-space-2);
  font-size: var(--eui-font-size-small);
  font-weight: 600;
  text-transform: uppercase;
  color: var(--eui-text-muted);
}
.palette__list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.palette__item {
  display: flex;
  align-items: center;
  gap: var(--eui-space-4);
  width: 100%;
  min-height: var(--eui-row-height);
  padding: var(--eui-space-1) var(--eui-space-3);
  border-radius: var(--eui-radius);
}
.palette__item .eui-icon {
  color: var(--eui-icon);
}
.palette__item:hover {
  background: var(--eui-hover);
}
</style>
