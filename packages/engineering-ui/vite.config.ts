// SPDX-License-Identifier: MIT
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { quasar } from "@quasar/vite-plugin";
import { storybookTest } from "@storybook/addon-vitest/vitest-plugin";
import { playwright } from "@vitest/browser-playwright";

const dirname = fileURLToPath(new URL(".", import.meta.url));
const entries = [
  "index",
  "theme",
  "icons",
  "composables",
  "controls",
  "dialogs",
  "navigation",
  "workspace",
  "inspectors",
];

// The Quasar plugin rewrites `import { QBtn } from "quasar"` into deep source
// paths. Use it for tests and Storybook only (Storybook adds it in viteFinal);
// the library output must import Quasar by its public entry.
const forTests = !!process.env.VITEST;

export default defineConfig({
  plugins: [vue(), ...(forTests ? [quasar({ sassVariables: false })] : [])],
  build: {
    target: "es2022",
    sourcemap: true,
    cssCodeSplit: false,
    lib: {
      entry: {
        ...Object.fromEntries(
          entries.map((name) => [name, `${dirname}src/${name === "index" ? "index" : `${name}/index`}.ts`]),
        ),
        styles: `${dirname}src/styles.ts`,
      },
      formats: ["es"],
      fileName: (_format, name) => `${name}.js`,
      cssFileName: "engineering-ui",
    },
    rolldownOptions: {
      external: (id) => id === "vue" || id === "quasar" || id.startsWith("quasar/"),
    },
  },
  test: {
    projects: [
      {
        extends: true,
        test: {
          name: "unit",
          environment: "happy-dom",
          include: ["tests/**/*.spec.ts"],
        },
      },
      {
        extends: true,
        plugins: [storybookTest({ configDir: `${dirname}.storybook` })],
        test: {
          name: "storybook",
          browser: {
            enabled: true,
            headless: true,
            provider: playwright(),
            instances: [{ browser: "chromium" }],
          },
        },
      },
    ],
  },
});
