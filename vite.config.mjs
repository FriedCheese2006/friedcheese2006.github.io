import vue from '@vitejs/plugin-vue';
import { defineConfig } from 'vite';
import { readFileSync } from 'node:fs';
import { resolve } from 'path';
import { VitePWA } from 'vite-plugin-pwa';

const outDir = resolve(import.meta.dirname, 'dist');
const projectRootDir = import.meta.dirname;
const { version: appVersion } = JSON.parse(readFileSync(resolve(projectRootDir, 'package.json'), 'utf8'));
const cacheVersion = `v${appVersion}`;

export default defineConfig({
    define: {
        __APP_VERSION__: JSON.stringify(appVersion),
    },
    plugins: [
        vue(),
        VitePWA({
            registerType: 'autoUpdate',
            injectRegister: 'auto',
            includeAssets: [
                'favicon.ico',
                'pwa-192.png',
                'pwa-512.png',
                'icarus-game/Images/question-mark.png',
            ],
            manifest: {
                name: 'PROSPECTOR',
                short_name: 'PROSPECTOR',
                description: 'Planetary Resource Order & Surface Prep Engine for Crafting, Tallying, Output & Requisitions: an ICARUS crafting planner.',
                theme_color: '#0a0f18',
                background_color: '#0a0f18',
                display: 'standalone',
                scope: '/',
                start_url: '/',
                icons: [
                    { src: '/favicon.ico', sizes: '16x16 32x32 48x48 64x64', type: 'image/x-icon', purpose: 'any' },
                    { src: '/pwa-192.png', sizes: '192x192', type: 'image/png' },
                    { src: '/pwa-512.png', sizes: '512x512', type: 'image/png' },
                    { src: '/pwa-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
                ],
            },
            workbox: {
                navigateFallback: null,
                cleanupOutdatedCaches: true,
                globPatterns: ['**/*.{js,css,ico,svg,woff,woff2}'],
                runtimeCaching: [
                    {
                        urlPattern: ({ request, url }) => request.mode === 'navigate' && !/^\/(api|auth)(\/|$)/.test(url.pathname),
                        handler: 'NetworkFirst',
                        options: {
                            cacheName: 'prospector-pages',
                            networkTimeoutSeconds: 5,
                            fetchOptions: { cache: 'no-store' },
                            cacheableResponse: { statuses: [0, 200] },
                            expiration: { maxEntries: 10, maxAgeSeconds: 60 * 60 * 24 * 7 },
                        },
                    },
                    {
                        urlPattern: /\/icarus-game\/Data\//,
                        handler: 'NetworkFirst',
                        options: {
                            cacheName: `prospector-game-data-${cacheVersion}`,
                            networkTimeoutSeconds: 5,
                            cacheableResponse: { statuses: [0, 200] },
                            expiration: { maxEntries: 20, maxAgeSeconds: 60 * 60 * 24 * 7 },
                        },
                    },
                    {
                        urlPattern: /\/icarus-game\/ItemIcons\//,
                        handler: 'StaleWhileRevalidate',
                        options: {
                            cacheName: `prospector-game-icons-${cacheVersion}`,
                            cacheableResponse: { statuses: [0, 200] },
                            expiration: { maxEntries: 2000, maxAgeSeconds: 60 * 60 * 24 * 30 },
                        },
                    },
                ],
            },
        }),
    ],
    resolve: {
        alias: {
            '@': resolve(projectRootDir, 'src'),
        },
    },
    build: {
        outDir,
        emptyOutDir: true,
        rollupOptions: {
            input: {
                main: resolve(projectRootDir, 'index.html'),
            },
        },
    },
});
