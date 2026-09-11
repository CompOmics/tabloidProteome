import "./assets/main.scss";

import { createApp } from "vue";
import { createPinia } from "pinia";

// Vuetify
import "vuetify/styles";
import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";
import "@mdi/font/css/materialdesignicons.css";

import App from "./App.vue";
import router from "./router";
import { getInitialTheme } from "./theme";

const app = createApp(App);
const vuetify = createVuetify({
    theme: {
        defaultTheme: getInitialTheme(),
        themes: {
            // Matches CosmographView's page backdrop so the light theme looks unchanged.
            light: {
                colors: {
                    background: "#f1f2f5",
                },
            },
            // Blue-grey rather than Vuetify's near-black default — background is the page
            // backdrop, surface is the toolbar/side-panel layer (used via --v-theme-surface).
            dark: {
                colors: {
                    background: "#10141c",
                    surface: "#1c2430",
                },
            },
        },
    },
    components,
    directives,
});

app.use(createPinia());
app.use(router);
app.use(vuetify);
app.mount("#app");
