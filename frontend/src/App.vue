<script setup lang="ts">
import { watch } from "vue";
import { RouterLink, RouterView } from "vue-router";
import { useTheme } from "vuetify";
import { THEME_STORAGE_KEY } from "./theme";

const theme = useTheme();

function toggleTheme(): void {
    const next = theme.global.name.value === "dark" ? "light" : "dark";
    theme.global.name.value = next;
    localStorage.setItem(THEME_STORAGE_KEY, next);
}

// The legacy --color-* CSS variables in assets/base.css key off this class rather than
// prefers-color-scheme, so they stay in sync when the user overrides the system theme.
watch(
    () => theme.global.current.value.dark,
    (isDark) => {
        document.documentElement.classList.toggle("dark-theme", isDark);
    },
    { immediate: true },
);
</script>

<template lang="pug">
v-app
    v-container.nav-container.pa-0(fluid)
        v-toolbar.toolbar(
            height="56"
            absolute
        )
            div.toolbar-row
                a(href="/")
                    img.logo(
                        src="./assets/logo.png"
                    )
                div.toolbar-actions
                    nav
                        RouterLink(to="/") Home
                        RouterLink(to="/about") About
                        RouterLink(to="/privacy") Privacy
                    v-btn(
                        icon
                        variant="text"
                        size="small"
                        :title="theme.global.current.value.dark ? 'Switch to light mode' : 'Switch to dark mode'"
                        @click="toggleTheme"
                    )
                        v-icon {{ theme.global.current.value.dark ? 'mdi-weather-sunny' : 'mdi-weather-night' }}
    RouterView
</template>

<style scoped>
.nav-container {
    height: 56px;
    margin-bottom: 12px;
}
.toolbar {
    background-color: rgb(var(--v-theme-surface));
}
.toolbar-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0 12px;
}
.toolbar-actions {
    display: flex;
    align-items: center;
    gap: 8px;
}
.logo {
    width: 62px;
    height: 47px;
    margin-top: 10px;
}
.v-navigation-drawer.v-navigaion-drawer--active {
    top: 25px !important;
}
nav {
    font-size: 12px;
    text-align: center;
}

nav a.router-link-exact-active {
    color: var(--color-text);
}

nav a.router-link-exact-active:hover {
    background-color: transparent;
}

nav a {
    /* display: inline-block; */
    padding: 0 1rem;
    border-left: 1px solid var(--color-border);
}

nav a:first-of-type {
    border: 0;
}

@media (min-width: 1024px) {
    header {
        display: flex;
        place-items: center;
    }

    /* .logo {
        margin: 0 2rem 0 0;
    } */

    header .wrapper {
        display: flex;
        place-items: flex-start;
        flex-wrap: wrap;
    }

    nav {
        text-align: left;
        margin-left: -1rem;
        font-size: 1rem;
        padding: 1rem 0;
    }
}
</style>
