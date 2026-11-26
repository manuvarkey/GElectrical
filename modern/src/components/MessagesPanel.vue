<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<template>
  <ul class="messages">
    <li v-for="message in mockMessages" :key="message.title" class="messages__item">
      <EuiIcon :name="message.severity === 'warning' ? 'warning' : 'info'" :size="16" />
      <strong>{{ message.severity === "warning" ? "Warning" : "Information" }}:</strong>
      {{ message.title }} <span class="messages__text">{{ message.text }}</span>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { EuiIcon } from "@kavilgroup/engineering-ui/icons";
import { mockMessages } from "../mock/project";
</script>

<style scoped>
.messages {
  margin: 0;
  padding: var(--eui-space-3) var(--eui-space-4);
  list-style: none;
}
.messages__item {
  display: flex;
  align-items: center;
  gap: var(--eui-space-3);
  min-height: var(--eui-row-height);
}
.messages__text {
  color: var(--eui-text-muted);
}
</style>
