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
                        :outlined="buttonStatus"
                        @click="onClick"
                    />
                </div>
                <div>
                    <DlProgressBar
                        label="Progress bar"
                        :value="progressValue"
                        v-bind="{
                            width: '200px',
                            showValue: true,
                            showPercentage: true
                        }"
                    />
                </div>
            </div>
            <div class="container">
                <iframe
                    id="iframe1"
                    ref="contentIframe"
                    class="frame-container"
                    frameBorder="0"
                    sandbox="allow-scripts allow-same-origin"
                ></iframe>
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
import { DlEvent, ThemeType } from '@dataloop-ai/jssdk'
import { ref, onMounted, computed, nextTick } from 'vue-demi'

const contentIframe = ref<HTMLIFrameElement | null>(null)
const isReady = ref<boolean>(false)
const currentTheme = ref<ThemeType>(ThemeType.LIGHT)
const lastUpdated = ref<string>('Never')
const buttonStatus = ref<boolean>(false)
const buttonLabel = ref<string>('Run')
const progressValue = ref<number>(0)
const datasetId = ref<string>(null)
const projectId = ref<string>(null)
const exportItemId = ref<string>(null)

const isDark = computed<boolean>(() => {
    return currentTheme.value === ThemeType.DARK
})

const loadFrame = async (src: string) => {
    contentIframe.value.onload = () => {
        setTimeout(() => {
            buttonLabel.value = 'Run'
            buttonStatus.value = false
        }, 5000)
    }
    await updateStatus()
    fetch(
        `http://localhost:3004/insights/build?datasetId=${datasetId.value}&itemId=${exportItemId.value}`
    )
    contentIframe.value.src = `http://localhost:3004/dash`
}

const updateStatus = async () => {
    try {
        const exportStatus = await fetch(
            `http://localhost:3004/export/status?datasetId=${datasetId.value}`
        )
        if (!exportStatus.ok) {
            throw new Error(`HTTP error! status: ${exportStatus.status}`)
        }
        const data = await exportStatus.json()
        buttonLabel.value = data.status === 'ready' ? 'Run' : 'Running'
        buttonStatus.value = data.status === 'ready' ? false : true
        lastUpdated.value = data.exportDate
        console.log(data.progress / 100)
        progressValue.value = data.progress / 100
        exportItemId.value = data.exportItemId
    } catch (err) {
        console.error('Error fetching export status:', err)
    }
}

const triggerMainAppLoad = async () => {
    const project = await window.dl.projects.get()
    projectId.value = project?.id ?? null
    const dataset = await window.dl.datasets.get()
    datasetId.value = dataset?.id ?? null

    await updateStatus()

    if (datasetId.value) {
        loadFrame(
            `http://localhost:3004/insights/build?datasetId=${datasetId.value}&itemId=${exportItemId.value}`
        )
    } else {
        console.error('No dataset found to fetch insights')

        buttonLabel.value = 'Run'
        buttonStatus.value = false
    }
}

onMounted(() => {
    window.dl.on(DlEvent.READY, async () => {
        const settings = await window.dl.settings.get()
        currentTheme.value = settings.theme
        window.dl.on(DlEvent.THEME, (data) => {
            currentTheme.value = data
        })
        isReady.value = true

        nextTick(() => {
            triggerMainAppLoad()
        })
    })
})

async function onClick() {
    fetch(`http://localhost:3004/export/run?datasetId=${datasetId.value}`)
    await updateStatus()
    while (buttonStatus.value === true) {
        console.log('waiting for export to finish')
        await updateStatus()
        await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    loadFrame(
        `http://localhost:3004/insights/build?datasetId=${datasetId.value}$itemId=${exportItemId.value}`
    )
}
</script>

<style scoped>
.container {
    display: flex;
    height: 100vh;
    justify-content: center;
}

.container > * {
    flex: 0 0 auto;
}

.container iframe {
    flex: 1 1 auto;
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

    border-bottom: 1px solid var(--dl-color-disabled);
}
</style>
