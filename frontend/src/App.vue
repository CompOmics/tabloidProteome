<script setup>
import { ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
// import HelloWorld from './components/HelloWorld.vue'
const drawer = ref(false);
</script>

<template lang="pug">
v-app
    v-container.nav-container(fluid)
        v-toolbar.toolbar(
            density="compact"
            floating
            absolute
            location="top left"
            style="padding-left: 12px;"
        )
            template(
                v-slot:prepend
            )
                a(href="/")
                    img.logo(
                        src="./assets/logo.png"
                    )
        v-toolbar.toolbar(
                density="compact"
                floating
                absolute
                location="top end"
        )
            template(v-slot:append)
                nav
                    RouterLink(to="/") Home
                    RouterLink(to="/about") About
                    RouterLink(to="/privacy") Privacy
    RouterView
</template>

<style scoped>
.nav-container {
    height: 55px;
}
.toolbar {
    background-color: white;
}
.logo {
    padding-top: 20px;
    width: 80px;
    height: 80px;
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

    .logo {
        margin: 0 2rem 0 0;
    }

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
