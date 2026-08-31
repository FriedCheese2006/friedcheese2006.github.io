export const rawItemMatchers = Object.freeze([
    /Ore$/,
    /Vestige$/,
    /Fur$/,
    /Animal Fat/,
    /Meat$/,
    /Carcass$/,
    /Pelt$/,
    'Aluminium Ore',
    'Animal Fat',
    'Bone',
    'Clay',
    'Condensed Enzymes',
    'Egg',
    'Exotics',
    'Fiber',
    'Fur',
    'Leather',
    'Obsidian',
    'Oxite',
    'Poison Sac',
    'Salt',
    'Scoria',
    'Seed',
    'Silica',
    'Spider Silk',
    'Stabilized Exotics',
    'Stone',
    'Stick',
    'Sulfur',
    'Tree Sap',
    'Volatile Raw Exotics',
    'Wood',
]);

export const isRawItem = (label) => rawItemMatchers.some((matcher) => (matcher instanceof RegExp ? matcher.test(label) : matcher === label));

export function generateHighlightedText(inputText, regions = []) {
    let content = '';
    let nextNonHighlightedRegionStartingIndex = 0;

    regions.forEach((region) => {
        const lastRegionNextIndex = region[1] + 1;
        const nonHighlightedRegion = inputText.substring(nextNonHighlightedRegionStartingIndex, region[0]);
        const highlightedRegion = inputText.substring(region[0], lastRegionNextIndex);
        content += `${nonHighlightedRegion}<span class="highlight-result">${highlightedRegion}</span>`;
        nextNonHighlightedRegionStartingIndex = lastRegionNextIndex;
    });

    return content + inputText.substring(nextNonHighlightedRegionStartingIndex);
}