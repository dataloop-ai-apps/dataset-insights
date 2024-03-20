import { xFrameDriver } from '@dataloop-ai/jssdk'

declare global {
    interface Window {
        dl: xFrameDriver
    }
}
