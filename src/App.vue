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
                        :disabled="operationRunning"
                        :outlined="operationRunning"
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
                        :indeterminate="frameLoadFailed"
                    />
                </div>
            </div>
            <div v-if="!buildReady" class="loading-spinner">
                <DlSpinner text="Loading App..." size="128px" />
            </div>
            <div class="container">
                <iframe
                    id="iframe1"
                    ref="contentIframe"
                    class="frame-container"
                    frameBorder="0"
                    data-theme="dark-mode"
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
import { debounce } from 'lodash'

const contentIframe = ref<HTMLIFrameElement | null>(null)
const isReady = ref<boolean>(false)
const buildReady = ref<boolean>(true)
const currentTheme = ref<ThemeType>(ThemeType.LIGHT)
const lastUpdated = ref<string>('Never')
const operationRunning = ref<boolean>(true)
const buttonLabel = ref<string>('Run')
const progressValue = ref<number>(0)
const datasetId = ref<string>(null)
const projectId = ref<string>(null)
const exportItemId = ref<string>(null)
const frameLoadFailed = ref<boolean>(false)

const isDark = computed<boolean>(() => {
    return currentTheme.value === ThemeType.DARK
})

const loadFrame = async () => {
    try {
        contentIframe.value.onload = () => {
            buttonLabel.value = 'Run'
            operationRunning.value = false
        }

        contentIframe.value.onerror = () => {
            buttonLabel.value = 'Run'
            operationRunning.value = false
            frameLoadFailed.value = true
        }

        buttonLabel.value = 'Loading'
        fetch(
            `http://localhost:3004/insights/build?datasetId=${datasetId.value}&itemId=${exportItemId.value}&theme=${currentTheme.value}`
        )
        buildReady.value = false
        await pollBuildStatus()
        buildReady.value = true
        contentIframe.value.src = `http://localhost:3004/dash`
    } catch (e) {
        console.error('Failed loading frame', e)
        buttonLabel.value = 'Run'
        operationRunning.value = false
        frameLoadFailed.value = true
    }
}

const updateStatus = async () => {
    const exportStatus = await fetch(
        `http://localhost:3004/export/status?datasetId=${datasetId.value}`
    )
    if (!exportStatus.ok) {
        throw new Error(`HTTP error! status: ${exportStatus.status}`)
    }
    const data = await exportStatus.json()
    if (Object.keys(data).length === 0) {
        return false
    }

    if (frameLoadFailed.value) {
        frameLoadFailed.value = false
    }
    lastUpdated.value = data.exportDate
    progressValue.value = data.progress / 100
    exportItemId.value = data.exportItemId

    const completed = data.progress === 100
    return completed
}

const getBuildStatus = async () => {
    const buildStatus = await fetch(
        `http://localhost:3004/build/status?datasetId=${datasetId.value}`
    )
    if (!buildStatus.ok) {
        throw new Error(`HTTP error! status: ${buildStatus.status}`)
    }
    const data = await buildStatus.json()
    if (Object.keys(data).length === 0) {
        return false
    }

    if (frameLoadFailed.value) {
        frameLoadFailed.value = false
    }

    const completed = data.status === 'ready'
    return completed
}

const handleInitialFrameLoading = async () => {
    try {
        if (datasetId.value) {
            const existingStatus = await updateStatus()
            if (!existingStatus) {
                await pollStatus()
            }

            return loadFrame()
        } else {
            console.error('No dataset found to fetch insights')
        }
    } catch (e) {
        console.error('Error fetching insights', e)
    }

    buttonLabel.value = 'Run'
    operationRunning.value = false
}

const triggerMainAppLoad = async () => {
    const project = await window.dl.projects.get()
    projectId.value = project?.id ?? null
    const dataset = await window.dl.datasets.get()
    datasetId.value = dataset?.id ?? null

    buttonLabel.value = 'Running'
    operationRunning.value = true
}

onMounted(() => {
    window.dl.on(DlEvent.READY, async () => {
        const settings = await window.dl.settings.get()
        currentTheme.value = settings.theme
        window.dl.on(DlEvent.THEME, (data) => {
            currentTheme.value = data
            loadFrame()
        })
        isReady.value = true

        nextTick(() => {
            triggerMainAppLoad().then(() => {
                nextTick(() => {
                    handleInitialFrameLoading()
                })
            })
        })
    })
})

const pollStatus = async () => {
    const interval = 1000
    const maxAttempts = 600 // max 10 minutes
    let attempts = 0

    return new Promise<boolean>((resolve, reject) => {
        const intervalId = setInterval(async () => {
            attempts++
            const completed = await updateStatus()
            if (completed) {
                clearInterval(intervalId)
                resolve(true)
            } else if (attempts >= maxAttempts) {
                clearInterval(intervalId)
                reject(new Error('Max attempts reached'))
            }
        }, interval)
    })
}

const pollBuildStatus = async () => {
    const interval = 1000
    const maxAttempts = 600 // max 10 minutes
    let attempts = 0

    return new Promise<boolean>((resolve, reject) => {
        const intervalId = setInterval(async () => {
            attempts++
            const completed = await getBuildStatus()
            if (completed) {
                clearInterval(intervalId)
                resolve(true)
            } else if (attempts >= maxAttempts) {
                clearInterval(intervalId)
                reject(new Error('Max attempts reached'))
            }
        }, interval)
    })
}

const runDatasetInsightGeneration = async () => {
    fetch(`http://localhost:3004/export/run?datasetId=${datasetId.value}`)
    await pollStatus()
    loadFrame()
}

const debouncedRunDatasetInsightGeneration = debounce(
    runDatasetInsightGeneration,
    300
)

async function onClick() {
    operationRunning.value = true
    buttonLabel.value = 'Running'
    lastUpdated.value = new Date().toString().split(' ').slice(1, 5).join(' ')
    progressValue.value = 0
    frameLoadFailed.value = true

    debouncedRunDatasetInsightGeneration()
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

    border-bottom: 1px solid var(--dl-color-disabled);
}
</style>
