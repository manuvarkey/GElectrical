// SPDX-License-Identifier: MIT
import { mount, type ComponentMountingOptions } from "@vue/test-utils";
import { Quasar } from "quasar";
import type { Component } from "vue";

/** Mounts with the Quasar plugin installed, attached to the document for focus tests. */
export function mountEui<C extends Component>(component: C, options: ComponentMountingOptions<C> = {}) {
  const host = document.createElement("div");
  document.body.append(host);
  return mount(component, {
    attachTo: host,
    ...options,
    global: { plugins: [[Quasar, {}]], ...options.global },
  } as ComponentMountingOptions<C>);
}
