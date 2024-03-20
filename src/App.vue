<template>
    <DlThemeProvider :is-dark="isDark">
        <div v-if="!isReady" class="loading-spinner">
            <DlSpinner text="Loading App..." size="128px" />
        </div>
        <div v-else>
            <div class="top-bar">
                <div
                    style="
                        display: flex;
                        flex-direction: row;
                        align-items: center;
                        gap: 15px;
                    "
                >
                    <DlTypography variant="h4">
                        Last updated: {{ lastUpdated }}
                    </DlTypography>
                    <DlButton
                        :label="buttonLabel"
                        :disabled="buttonStatus"
                        outlined
                        @click="onClick"
                    />
                </div>
                <div>
                    <DlProgressBar
                        label="Progress bar"
                        v-bind="{
                            width: '200px',
                            value: 0.5,
                            showValue: true,
                            showPercentage: true
                        }"
                    />
                </div>
            </div>
            <div class="container">
                <iframe ref="contentIframe" class="frame-container"></iframe>
            </div>
        </div>
    </DlThemeProvider>
</template>

<script setup lang="ts">
import {
    DlThemeProvider,
    DlTypography,
    DlButton,
    DlProgressBar,
    DlSpinner
} from '@dataloop-ai/components'
import { DlEvent } from '@dataloop-ai/jssdk'
import { onMounted } from 'vue'
import { ref } from 'vue-demi'

const contentIframe = ref<HTMLIFrameElement | null>(null)
const isReady = ref<boolean>(false)
const isDark = ref<boolean>(true)
const lastUpdated = ref<string>('Never')
const buttonStatus = ref<boolean>(false)
const buttonLabel = ref<string>('Run')
const datasetId = ref<string>(null)
const projectId = ref<string>(null)

const loadFrame = async (src: string) => {
    contentIframe.value.onload = () => {
        setTimeout(() => {
            buttonLabel.value = 'Run'
            buttonStatus.value = false
        }, 5000)
    }
    contentIframe.value.src = `http://localhost:3003/insights/build/${datasetId.value}`
}

const triggerMainAppLoad = async () => {
    lastUpdated.value = new Date().toLocaleTimeString()
    buttonLabel.value = 'Fetching'
    buttonStatus.value = true

    const project = await window.dl.projects.get()
    projectId.value = project?.id ?? null
    const dataset = await window.dl.datasets.get()
    datasetId.value = dataset?.id ?? null

    if (datasetId.value) {
        loadFrame(`http://localhost:3003/insights/build/${datasetId.value}`)
    } else {
        console.error('No dataset found to fetch insights')

        buttonLabel.value = 'Run'
        buttonStatus.value = false
    }
}

const changeIframeTheme = async (theme) => {
    fetch(`/insights/settings/${datasetId.value}`, {
        method: 'POST', // Specify the method
        headers: {
            'Content-Type': 'application/json' // Specify the content type
        },
        body: JSON.stringify({ theme }) // Convert the JavaScript object to a JSON string
    })
        .then((response) => response.json()) // Parse the JSON response
        .then((data) => {
            console.log('Success:', data) // Handle success
        })
        .catch((error) => {
            console.error('Error:', error) // Handle errors
        })

    loadFrame(`http://localhost:3003/insights/build/${datasetId.value}`)
}

onMounted(() => {
    window.dl.on(DlEvent.READY, async () => {
        const settings = await window.dl.settings.get()
        changeIframeTheme(settings.theme)
        window.dl.on(DlEvent.THEME, (data) => {
            changeIframeTheme(data)
        })
        await triggerMainAppLoad()
        isReady.value = true
    })
})

async function onClick() {
    await triggerMainAppLoad()
}
</script>

<style scoped>
.container {
    display: flex;
    width: 100%;
    height: 100vh;
    justify-content: center;
}

.container > * {
    flex: 0 0 auto;
}

.container iframe {
    flex: 1 1 auto;
    width: 100%;
}

.loading-spinner {
    display: grid;
    place-items: center;
    height: 100vh;
}

.top-bar {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    padding: 10px 0;
}
</style>
