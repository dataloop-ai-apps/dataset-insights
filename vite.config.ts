// @ts-nocheck

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import viteBasicSslPlugin from '@vitejs/plugin-basic-ssl'

// https://vitejs.dev/config/
export default defineConfig({
    build: {
        outDir: 'dist'
    },
    base: '/insights',
    server: {
        host: '0.0.0.0',
        https: false,
        port: 8084
    },
    optimizeDeps: {
        include: [
            'lodash',
            '@dataloop-ai/components',
            'flat',
            'highlight.js',
            'sortablejs',
            '@dataloop-ai/jssdk'
        ],
        exclude: ['node_modules', './node_modules', 'dist', './dist']
    },
    resolve: {
        alias: {
            '@': '/src'
        }
    },
    plugins: [viteBasicSslPlugin(), vue()],
    test: {
        environment: 'jsdom',
        setupFiles: ['tests/setup.js'],
        deps: {
            inline: ['vitest-canvas-mock']
        },
        coverage: {
            reporter: ['lcovonly', 'text']
        }
    }
})
