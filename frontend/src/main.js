import './assets/main.scss'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
// import { VTreeview } from 'vuetify/lib/labs/components.mjs'
import '@mdi/font/css/materialdesignicons.css'

import App from './App.vue'
import router from './router'

const app = createApp(App)
const vuetify = createVuetify({
    theme: {
        defaultTheme: 'light'
    },
    components,
    directives
})

app.use(createPinia())
app.use(router)
app.use(vuetify)
app.mount('#app')
