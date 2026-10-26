import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
// import store from './store'
import './assets/scss/app.scss'

// Self-hosted so Buefy's default (mdi) icon pack has glyphs to render, and so
// the app has no runtime dependency on a third-party CDN (jsdelivr previously
// served this and was dropped during the Vue3 migration without a replacement
// -- also avoids browser Tracking Prevention warnings on the CDN origin).
import '@mdi/font/css/materialdesignicons.css'

import 'leaflet/dist/leaflet.css'

import Buefy from 'buefy'
import 'buefy/dist/buefy.css'

import VueGtag from 'vue-gtag-next'

import titleMixin from './mixins/titleMixin'

const app = createApp(App)
app.mixin(titleMixin)
app.use(VueGtag, {
  property: { id: 'G-X1CBD2T8XH' }
})
app.use(Buefy)
app.use(router)
// app.use(store)

app.mount('#app')
