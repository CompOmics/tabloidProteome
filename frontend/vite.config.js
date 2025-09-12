import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  css: {
    preprocessorOptions: {
        scss: {
            //additionalData: `@use "@/assets/main.scss";`,
        },
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:5600",
        changeOrigin: true,
        // secure: false,
        rewrite: (path) => path.replace(/^\/api/, '')
      },
    },
  }
})
