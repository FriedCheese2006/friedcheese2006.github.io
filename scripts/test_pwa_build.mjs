import { readFileSync } from 'node:fs';

const serviceWorker = readFileSync('dist/sw.js', 'utf8');
const expectations = [
    {
        route: 'registerRoute(/\\/icarus-game\\/Data\\//',
        strategy: 'NetworkFirst',
        url: 'https://friedcheese2006.github.io/icarus-game/Data/D_CraftingCatalog.json',
        pattern: /\/icarus-game\/Data\//,
    },
    {
        route: 'registerRoute(/\\/icarus-game\\/ItemIcons\\//',
        strategy: 'StaleWhileRevalidate',
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
    if (!expectation.pattern.test(expectation.url)) {
        throw new Error(`${expectation.pattern} does not match ${expectation.url}`);
    }
}

console.log('Generated PWA runtime routes are valid');
