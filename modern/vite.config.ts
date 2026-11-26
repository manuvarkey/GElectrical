// SPDX-License-Identifier: GPL-3.0-or-later
import { defineConfig } from "vitest/config";
import { defaultClientConditions } from "vite";
import vue from "@vitejs/plugin-vue";
import { quasar, transformAssetUrls } from "@quasar/vite-plugin";

export default defineConfig({
  plugins: [vue({ template: { transformAssetUrls } }), quasar({ sassVariables: false })],
  // "source" resolves @kavilgroup/engineering-ui to its sources during development,
  // so the workspace needs no library build before `npm run dev`.
  resolve: { conditions: ["source", ...defaultClientConditions] },
  server: { host: "127.0.0.1", port: 1420, strictPort: true },
  build: { target: "es2022" },
  test: {
    environment: "happy-dom",
    include: ["src/**/*.spec.ts"],
    server: { deps: { inline: ["quasar"] } },
  },
});
