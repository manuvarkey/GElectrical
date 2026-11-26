// SPDX-License-Identifier: GPL-3.0-or-later
import { createApp } from "vue";
import { Dark, Quasar } from "quasar";
import "quasar/src/css/index.sass";
import "@kavilgroup/engineering-ui/style.css";
import { bindQuasarDark, useTheme } from "@kavilgroup/engineering-ui/theme";
import App from "./App.vue";
import "./app.css";

useTheme({ initial: "system" });
bindQuasarDark(Dark);

createApp(App).use(Quasar, { plugins: { Dark } }).mount("#app");
