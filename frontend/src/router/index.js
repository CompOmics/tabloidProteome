import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: "/about",
            name: "about",
            component: () => import("../views/AboutView.vue"),
        },
        {
            path: "/privacy",
            name: "privacy",
            component: () => import("../views/PrivacyView.vue"),
        },
        {
            path: "/",
            name: "home",
            component: () => import("../views/CosmographView.vue"),
        },
        {
            path: "/cosmograph",
            name: "cosmograph",
            component: () => import("../views/CosmographView.vue"),
        },
    ],
});

export default router;
