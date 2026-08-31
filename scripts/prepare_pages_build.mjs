import { copyFileSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const indexPath = 'dist/index.html';
const fallbackPath = 'dist/404.html';
copyFileSync(indexPath, fallbackPath);

const index = readFileSync(indexPath);
const fallback = readFileSync(fallbackPath);
if (!index.equals(fallback)) {
    throw new Error('GitHub Pages fallback does not match index.html');
}

const html = index.toString('utf8');
const rootAssetReferences = [...html.matchAll(/(?:href|src)="(\/[^"?#]+)(?:[?#][^"]*)?"/g)].map((match) => match[1]);
for (const reference of rootAssetReferences) {
    if (!existsSync(join('dist', reference))) {
        throw new Error(`GitHub Pages artifact is missing ${reference}`);
    }
}

console.log(`GitHub Pages fallback is valid with ${rootAssetReferences.length} referenced assets`);
