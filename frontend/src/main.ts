import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import PrimeVue from 'primevue/config'
import App from './App.vue'
import router from './router'
import './style.css'

createApp(App)
  .use(router)
  .use(VueQueryPlugin)
  .use(PrimeVue, { unstyled: true })
  .mount('#app')
