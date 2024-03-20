import "./style.css";
import { createApp } from "vue"
import App from "./App.vue"
import { initializeFrameDriver, xFrameDriver } from '@dataloop-ai/jssdk'

initializeFrameDriver().then(() => {
    console.log('in main.ts')
    console.log(window.dl)
    createApp(App).mount("#app")
})
declare global {
    interface Window {
        dl: xFrameDriver
    }
}
