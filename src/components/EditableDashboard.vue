<template>
    <div class="p-8 bg-slate-900 min-h-screen">
        <div class="py-2 px-2.5 flex justify-end space-x-2">
            <Button v-if="isEditing" @click="addWidget">Add Widget</Button>
            <Button @click="toggleEdit" outline>
                {{ isEditing ? 'Stop Editing' : 'Start Editing' }}
            </Button>
        </div>
        <div class="grid-stack">
            <Widget
                v-for="widget in widgets"
                :key="widget.id"
                :data="widget"
                :is-editing="isEditing"
                @delete="deleteWidget"
            />
        </div>
    </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import Widget from '@/components/Widget.vue'
import Button from '@/components/Button.vue'
import { GridStack } from 'gridstack'
import 'gridstack/dist/gridstack.min.css'
import 'gridstack/dist/gridstack-extra.min.css'

const grid = ref(null)
const widgets = ref([
    {
        id: 1,
        title: 'Widget 1',
        grid: {
            x: 0,
            y: 0,
            w: 2,
            h: 2
        }
    },
    {
        id: 2,
        title: 'Widget 2',
        grid: {
            x: 2,
            y: 0,
            w: 2,
            h: 1
        }
    },
    {
        id: 3,
        title: 'Widget 3',
        grid: {
            x: 0,
            y: 2,
            w: 2,
            h: 1
        }
    },
    {
        id: 4,
        title: 'Widget 4',
        grid: {
            x: 2,
            y: 2,
            w: 1,
            h: 2
        }
    },
    {
        id: 5,
        title: 'Widget 5',
        grid: {
            x: 3,
            y: 2,
            w: 1,
            h: 2
        }
    }
])

function initGridStack() {
    grid.value = GridStack.init({
        column: 4,
        cellHeight: 100,
        margin: 10,
        disableResize: !isEditing.value,
        disableDrag: !isEditing.value
    })
    makeWidgets(widgets.value)
}

function makeWidgets(widgets) {
    widgets.forEach((widget) => {
        makeWidget(widget)
    })
}
function makeWidget(item) {
    const elSelector = `#${item.id}`
    return grid.value.makeWidget(elSelector)
}

async function addWidget() {
    const widgetCount = widgets.value.length + 1
    const widget = {
        id: widgetCount,
        title: `Widget ${widgetCount}`,
        grid: {
            w: 1,
            h: 1
        }
    }
    widgets.value.push(widget)
    await nextTick()
    makeWidget(widget)
}

function deleteWidget(widget) {
    const index = widgets.value.findIndex((w) => w.id === widget.id)
    if (index === -1) {
        return
    }
    const selector = `#${CSS.escape(widget.id)}`
    grid.value.removeWidget(selector)
    grid.value.compact()
    widgets.value.splice(index, 1)
}

const isEditing = ref(false)

function toggleEdit() {
    if (isEditing.value) {
        grid.value.disable()
    } else {
        grid.value.enable()
    }
    isEditing.value = !isEditing.value
}

onMounted(() => {
    initGridStack()
})
</script>
