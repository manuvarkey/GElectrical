<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Shell composition only: ribbon, rail, panels, status bar (frontend.md §2). -->
<template>
  <div class="shell">
    <header>
      <h1 class="eui-visually-hidden">GElectrical</h1>
      <EuiRibbon
        v-model="shell.activeTab.value"
        :tabs="shell.tabs.value"
        label="GElectrical ribbon"
        :busy="!!shell.busy.value"
        @command="shell.command"
      />
    </header>
    <EuiWorkspace
      v-model:sizes="shell.sizes.value"
      :show-left="shell.panels.value.showLeft"
      :show-right="shell.panels.value.showRight"
      :show-bottom="shell.panels.value.showBottom"
      left-label="Components"
      right-label="Inspector"
      bottom-label="Messages"
      center-label="Drawing"
    >
      <template #rail>
        <EuiDocumentRail
          v-model="shell.activeDocument.value"
          :items="shell.documents.value"
          label="Open projects"
          add-label="New project"
          :busy="!!shell.busy.value"
          @add="shell.addDocument"
          @close="shell.closeDocument"
        />
      </template>
      <template #left><ComponentPalette @insert="shell.command(`insert:${$event}`)" /></template>
      <SchematicPlaceholder />
      <template #right>
        <EuiPropertyInspector
          :fields="mockLoadFields"
          :values="shell.values.value"
          :errors="shell.errors.value"
          label="Properties of L1"
          filterable
          @change="shell.changeField"
          @edit="shell.command(`edit:${$event}`)"
        />
      </template>
      <template #bottom><MessagesPanel /></template>
    </EuiWorkspace>
    <EuiStatusBar :items="shell.statusItems.value" :notice="shell.notice.value" :busy="shell.busy.value" />
    <EuiNotifications :items="shell.notifications.items.value" @dismiss="shell.notifications.dismiss" />
    <SettingsDialog v-model="shell.settingsOpen.value" />
  </div>
</template>

<script setup lang="ts">
import { EuiDocumentRail, EuiRibbon } from "@kavilgroup/engineering-ui/navigation";
import { EuiNotifications, EuiStatusBar, EuiWorkspace } from "@kavilgroup/engineering-ui/workspace";
import { EuiPropertyInspector } from "@kavilgroup/engineering-ui/inspectors";
import ComponentPalette from "./components/ComponentPalette.vue";
import MessagesPanel from "./components/MessagesPanel.vue";
import SchematicPlaceholder from "./components/SchematicPlaceholder.vue";
import SettingsDialog from "./components/SettingsDialog.vue";
import { useShell } from "./composables/useShell";
import { mockLoadFields } from "./mock/project";

const shell = useShell();
</script>

<style scoped>
.shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--eui-frame);
  color: var(--eui-text);
}
</style>
