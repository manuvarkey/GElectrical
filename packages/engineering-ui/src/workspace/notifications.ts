// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Manu Varkey
// Adapted from GEstimator modern/src/statusNotice.ts at e4e4fb295899feda5253ba216613c70c1f256d4e
//
// A notification queue owned by the host (no global state): transient
// results time out; errors stay until dismissed.

import { readonly, ref, type Ref } from "vue";
import type { EuiNotification } from "./types";

export interface EuiNotificationQueue {
  items: Readonly<Ref<readonly EuiNotification[]>>;
  /** Adds or replaces a notification. Danger notices never time out. Returns its id. */
  notify(notice: Omit<EuiNotification, "id"> & { id?: string }, timeout?: number): string;
  dismiss(id: string): void;
  clear(): void;
}

export function createNotificationQueue(
  options: { defaultTimeout?: number; limit?: number } = {},
): EuiNotificationQueue {
  const defaultTimeout = options.defaultTimeout ?? 5000;
  const limit = options.limit ?? 5;
  const items = ref<EuiNotification[]>([]);
  const timers = new Map<string, ReturnType<typeof setTimeout>>();
  let counter = 0;

  function dismiss(id: string) {
    const timer = timers.get(id);
    if (timer) clearTimeout(timer);
    timers.delete(id);
    items.value = items.value.filter((item) => item.id !== id);
  }

  function notify(notice: Omit<EuiNotification, "id"> & { id?: string }, timeout = defaultTimeout) {
    const id = notice.id ?? `eui-notice-${++counter}`;
    dismiss(id);
    const item: EuiNotification = { ...notice, id };
    const next = [...items.value, item];
    // Drop the oldest non-error notices beyond the limit; errors stay visible.
    while (next.length > limit) {
      const index = next.findIndex((entry) => entry.tone !== "danger");
      if (index < 0) break;
      const [removed] = next.splice(index, 1);
      if (removed) dismissTimer(removed.id);
    }
    items.value = next;
    if (item.tone !== "danger" && timeout > 0)
      timers.set(
        id,
        setTimeout(() => dismiss(id), timeout),
      );
    return id;
  }

  function dismissTimer(id: string) {
    const timer = timers.get(id);
    if (timer) clearTimeout(timer);
    timers.delete(id);
  }

  function clear() {
    for (const timer of timers.values()) clearTimeout(timer);
    timers.clear();
    items.value = [];
  }

  return { items: readonly(items) as Readonly<Ref<readonly EuiNotification[]>>, notify, dismiss, clear };
}
