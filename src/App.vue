<template>
    <DlThemeProvider :is-dark="isDark">
        <img alt="Vue logo" src="./assets/dataloop-logo.svg" class="logo" />
        <DlTypography variant="h1">
            {{ buttonLabel }}
            {{ buttonStatus }}
            <div style="padding-left: 50%">
                Last updated: {{ lastUpdated }}
                <DlButton
                    :label="buttonLabel"
                    :disabled="buttonStatus"
                    @click="onClick"
                />
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
        </DlTypography>
        <div class="container">
            <iframe
                ref="contentIframe"
                class="frame-container"
                :src="iframeSource"
            ></iframe>
        </div>
    </DlThemeProvider>
</template>

<script setup lang="ts">
import {
    DlThemeProvider,
    DlTypography,
    DlButton,
    DlProgressBar
} from '@dataloop-ai/components'
import { DlEvent } from '@dataloop-ai/jssdk'
import { onMounted } from 'vue'
import { ref } from 'vue-demi'

const iframeSource = ref('src/loading.html')
// let iframeSource = ref('http://localhost:3003/insights/main');
const isDark = ref(true)
const lastUpdated = ref('Never')
const buttonStatus = ref(false)
const buttonLabel = ref('Run')
let dataset_id = null
let project_id = null

async function main() {
    console.log('in main')
    lastUpdated.value = new Date().toLocaleTimeString()
    buttonLabel.value = 'Fetching'
    console.log(`${buttonLabel.value}`)
    buttonStatus.value = true
    console.log(`${buttonStatus.value}`)
    project_id = (await window.dl.projects.get()).id
    dataset_id = (await window.dl.datasets.get()).id
    iframeSource.value = `http://localhost:3003/insights/build/${dataset_id}`
    buttonLabel.value = 'Run'
    buttonStatus.value = false
}

async function changeIframeTheme(theme) {
    fetch(`/insights/settings/${dataset_id}`, {
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
    iframeSource.value = `http://localhost:3003/insights/build/${dataset_id}`
}

onMounted(() => {
    console.log(`${iframeSource.value}`)
    try {
        window.onload = function () {
            console.log('on load function')
            async function init() {
                await window.dl.on('ready', async () => {
                    console.log('In init')
                    const settings = await window.dl.settings.get()
                    changeIframeTheme(settings.theme)
                    await window.dl.on('theme', (data) => {
                        changeIframeTheme(data)
                    })
                    await main()
                })
            }
            init()
        }
    } catch (e) {
        console.error('Error initializing xFrameDriver', e)
    }
})

async function onClick() {
    await main()
}
</script>

<style scoped>
.container {
    display: flex;
    /* Make the container a flexbox */
    /* Stack elements vertically */
    width: 100vw;
    height: 100vh;
    /* Set container height to 100% viewport height */
    justify-content: center;
}

.container > * {
    /* Target all direct children of the container */
    flex: 0 0 auto;
    /* Set default size for child elements */
}

.container iframe {
    /* Style the iframe specifically */
    flex: 1 1 auto;
    /* Allow iframe to expand to fill remaining space */
    width: 100%;
}
</style>
