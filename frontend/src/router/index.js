import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import SigmaView from '@/views/SigmaView.vue'
import CytoscapeView from '@/views/CytoscapeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/about',
      name: 'about',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/AboutView.vue'),
    },
    {
      path: '/cytoscape',
      name: 'cytoscape',
      component: () => import('../views/CytoscapeView.vue')
    },
    {
      path: '/sigma',
      name: 'sigma',
      component: () => import('../views/SigmaView.vue'),
    },
  ],
})

export default router
