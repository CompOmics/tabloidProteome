<script setup>
import { ref } from "vue";
import { RouterLink, RouterView } from "vue-router";
// import HelloWorld from './components/HelloWorld.vue'
const drawer = ref(false);
const showAnalyticsNotice = ref(true);
</script>

<template lang="pug">
v-app
    v-container(fluid)
        v-toolbar.toolbar(density="compact")
            template(
                v-slot:prepend
            )
                a(href="/")
                    img.logo(
                        src="./assets/logo.png"
                    )
            template(v-slot:append)
                nav
                    RouterLink(to="/") Home
                    RouterLink(to="/about") About
            
            //- template(
            //-     v-slot:append
            //- )
            //-     .d-flex.ga-1
            //-         v-btn(
            //-             icon="mdi-menu"
            //-             @click.stop="drawer = !drawer"
            //-         )
            //- v-app-bar-nav-icon(variant="image") 
            //- v-btn(
            //-   icon="mdi-menu"
            //-   @click.stop="drawer = !drawer"
            //- )
        v-navigation-drawer(
            v-model="drawer"
            location="right"
            temporary
        )
            v-btn(
                icon="mdi-close"
                @click.stop="drawer = !drawer"
            )
            v-list-item(title="About")
            v-list-item(title="Privacy")
    RouterView
    v-alert.analytics-notice(
        v-if="showAnalyticsNotice"
        type="info"
        closable
        @update:modelValue="showAnalyticsNotice = $event"
    )
        | This site uses Google Analytics to help us understand user interactions and improve our service.
</template>

<style scoped>
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
  width: 100%;
  font-size: 12px;
  text-align: center;
  margin-top: 2rem;
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
    margin-top: 1rem;
  }
}

.analytics-notice {
  position: fixed;
  bottom: 20px;
  right: 20px;
  max-width: 400px;
  z-index: 1000;
}
</style>
