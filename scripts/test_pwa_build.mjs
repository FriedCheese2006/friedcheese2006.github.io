import { readFileSync } from 'node:fs';

const serviceWorker = readFileSync('dist/sw.js', 'utf8');
const { version } = JSON.parse(readFileSync('package.json', 'utf8'));

const pageCacheIndex = serviceWorker.indexOf('cacheName:"prospector-pages"');
if (pageCacheIndex === -1) {
    throw new Error('Generated service worker is missing the page navigation cache');
}
const pageRouteDefinition = serviceWorker.slice(Math.max(0, pageCacheIndex - 240), pageCacheIndex + 160);
if (!pageRouteDefinition.includes('"navigate"') || !pageRouteDefinition.includes('NetworkFirst') || !pageRouteDefinition.includes('cache:"no-store"')) {
    throw new Error('Page navigations do not use a cache-bypassing NetworkFirst request');
}
if (serviceWorker.includes('createHandlerBoundToURL("index.html")')) {
    throw new Error('Page navigations still use the precached index.html app shell');
}

const expectations = [
    {
        route: 'registerRoute(/\\/icarus-game\\/Data\\//',
        strategy: 'NetworkFirst',
        cacheName: `prospector-game-data-v${version}`,
        url: 'https://friedcheese2006.github.io/icarus-game/Data/D_CraftingCatalog.json',
        pattern: /\/icarus-game\/Data\//,
    },
    {
        route: 'registerRoute(/\\/icarus-game\\/ItemIcons\\//',
        strategy: 'StaleWhileRevalidate',
        cacheName: `prospector-game-icons-v${version}`,
        url: 'https://friedcheese2006.github.io/icarus-game/ItemIcons/Tools/icon.png',
        pattern: /\/icarus-game\/ItemIcons\//,
    },
];

for (const expectation of expectations) {
    const routeIndex = serviceWorker.indexOf(expectation.route);
    if (routeIndex === -1) {
        throw new Error(`Generated service worker is missing route ${expectation.route}`);
    }
    const routeDefinition = serviceWorker.slice(routeIndex, routeIndex + 160);
    if (!routeDefinition.includes(expectation.strategy)) {
        throw new Error(`${expectation.route} does not use ${expectation.strategy}`);
    }
    if (!routeDefinition.includes(expectation.cacheName)) {
        throw new Error(`${expectation.route} does not use versioned cache ${expectation.cacheName}`);
    }
    if (!expectation.pattern.test(expectation.url)) {
        throw new Error(`${expectation.pattern} does not match ${expectation.url}`);
    }
}

console.log('Generated PWA runtime routes are valid');
