// SPDX-License-Identifier: MIT
import { setup, type Preview } from "@storybook/vue3-vite";
import { Dark, Quasar } from "quasar";
import "quasar/src/css/index.sass";
import "../src/style.css";
import { bindQuasarDark, useTheme, type EuiThemePreference } from "../src/theme";

setup((app) => {
  app.use(Quasar, { plugins: { Dark } });
});

const theme = useTheme({ initial: "light" });
bindQuasarDark(Dark);

const preview: Preview = {
  globalTypes: {
    theme: {
      description: "EngineeringUI theme",
      toolbar: {
        title: "Theme",
        icon: "mirror",
        items: [
          { value: "light", title: "Light" },
          { value: "dark", title: "Dark" },
          { value: "system", title: "System" },
        ],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: { theme: "light" },
  decorators: [
    (story, context) => {
      theme.setPreference((context.globals.theme as EuiThemePreference) || "light");
      return {
        components: { story },
        template: '<div class="eui-story"><story /></div>',
      };
    },
  ],
  parameters: {
    layout: "padded",
    controls: { matchers: { color: /(background|color)$/i } },
    // Serious a11y violations fail the Vitest story run.
    a11y: { test: "error" },
  },
  tags: ["autodocs"],
};

export default preview;
