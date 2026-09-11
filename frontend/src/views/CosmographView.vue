<script setup lang="ts">
// import CosmographComponent from "../components/CosmographComponent.vue";
import Cosmograph2 from "../components/Cosmograph2.vue";
</script>

<template lang="pug">
v-container.cosmograph-page(fluid)
    //- CosmographComponent
    Cosmograph2()
</template>

<style scoped>
.cosmograph-page {
    background-color: rgb(var(--v-theme-background));
}
</style>
