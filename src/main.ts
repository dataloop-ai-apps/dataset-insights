import './style.css'
import { createApp } from 'vue'
import App from './App.vue'
import { initializeFrameDriver, xFrameDriver } from '@dataloop-ai/jssdk'

initializeFrameDriver().then(() => {
    createApp(App).mount('#app')
})
declare global {
    interface Window {
        dl: xFrameDriver
    }
}
