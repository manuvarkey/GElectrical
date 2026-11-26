<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<template>
  <EuiDialog
    :model-value="modelValue"
    title="Settings"
    apply-label="Apply"
    @update:model-value="emit('update:modelValue', $event)"
    @apply="apply"
  >
    <fieldset class="settings__group">
      <legend>Theme</legend>
      <label v-for="option in options" :key="option.value" class="settings__option">
        <input v-model="choice" type="radio" name="theme" :value="option.value" />{{ option.label }}
      </label>
    </fieldset>
  </EuiDialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { EuiDialog } from "@kavilgroup/engineering-ui/dialogs";
import { useTheme, type EuiThemePreference } from "@kavilgroup/engineering-ui/theme";

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();
const theme = useTheme();
const options: { value: EuiThemePreference; label: string }[] = [
  { value: "system", label: "Follow the system" },
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
];
const choice = ref<EuiThemePreference>(theme.preference.value);

watch(
  () => props.modelValue,
  (open) => {
    if (open) choice.value = theme.preference.value;
  },
);

function apply() {
  // Persisting the preference moves to Python program settings in M9.
  theme.setPreference(choice.value);
  emit("update:modelValue", false);
}
</script>

<style scoped>
.settings__group {
  display: flex;
  flex-direction: column;
  gap: var(--eui-space-3);
  margin: 0;
  padding: var(--eui-space-4) var(--eui-space-5);
  border: var(--eui-border-width) solid var(--eui-border);
  border-radius: var(--eui-radius);
}
.settings__option {
  display: flex;
  align-items: center;
  gap: var(--eui-space-3);
}
.settings__option input {
  accent-color: var(--eui-accent-fill);
}
</style>
