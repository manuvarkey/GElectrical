// SPDX-License-Identifier: MIT
import type { StorybookConfig } from "@storybook/vue3-vite";
import { quasar } from "@quasar/vite-plugin";

const config: StorybookConfig = {
  stories: ["../stories/**/*.mdx", "../stories/**/*.stories.ts"],
  addons: ["@storybook/addon-docs", "@storybook/addon-a11y", "@storybook/addon-vitest"],
  framework: { name: "@storybook/vue3-vite", options: {} },
  core: { disableTelemetry: true },
  async viteFinal(config) {
    const present = config.plugins
      ?.flat()
      .some((plugin) => plugin && "name" in plugin && plugin.name === "vite:quasar");
    return present ? config : { ...config, plugins: [...(config.plugins ?? []), quasar({ sassVariables: false })] };
  },
};

export default config;
