import { describe, expect, it } from 'vitest';

import { calculateRequirements, calculateReverseLookup } from './requirementTree';

const catalog = {
    itemsById: {
        Plank: { id: 'Plank', label: 'Plank', imagePath: '/plank.png' },
        Wood: { id: 'Wood', label: 'Wood', imagePath: '/wood.png' },
        Resin: { id: 'Resin', label: 'Resin', imagePath: '/resin.png' },
        Refined_Oil: { id: 'Refined_Oil', label: 'Refined Oil', imagePath: '/oil.png', isResource: true, quantityUnit: 'L' },
    },
    itemIdByAlias: { Plank: 'Plank', Wood: 'Wood' },
    recipesById: {
        'processor:Plank': {
            id: 'processor:Plank',
            name: 'Plank',
            source: 'processor',
            enabled: true,
            inputs: [{ itemId: 'Wood', quantity: 2 }],
            outputs: [{ itemId: 'Plank', quantity: 1 }],
            recipeSetIds: ['Bench'],
        },
        'processor:Plank_Bulk': {
            id: 'processor:Plank_Bulk',
            name: 'Plank_Bulk',
            source: 'processor',
            enabled: true,
            inputs: [{ itemId: 'Wood', quantity: 3 }],
            outputs: [{ itemId: 'Plank', quantity: 2 }],
            recipeSetIds: ['Bench'],
        },
        'processor:Wood': {
            id: 'processor:Wood',
            name: 'Wood',
            source: 'processor',
            enabled: true,
            inputs: [
                { itemId: 'Resin', quantity: 2 },
                { itemId: 'Refined_Oil', quantity: 0.5, quantityUnit: 'L' },
            ],
            outputs: [{ itemId: 'Wood', quantity: 1 }],
            recipeSetIds: ['Sawmill'],
        },
    },
    recipeIdsByOutputItemId: { Plank: ['processor:Plank', 'processor:Plank_Bulk'], Wood: ['processor:Wood'] },
    recipeIdsByInputItemId: { Wood: ['processor:Plank', 'processor:Plank_Bulk'], Refined_Oil: ['processor:Wood'] },
    defaultRecipeIdByOutputItemId: { Plank: 'processor:Plank', Wood: 'processor:Wood' },
    recipeSetsById: { Bench: { id: 'Bench', label: 'Bench', itemId: null }, Sawmill: { id: 'Sawmill', label: 'Sawmill', itemId: null } },
};

describe('requirement traversal', () => {
    it('applies one plan override to quantity and station calculation', () => {
        const result = calculateRequirements({
            selectedItems: [{ id: 'Plank', quantity: 4 }],
            catalog,
            recipeOverrides: { Plank: 'processor:Plank_Bulk' },
            isRawItem: (label) => label === 'Resin',
        });

        expect(result.requirementTrees.primary[0].recipeId).toBe('processor:Plank_Bulk');
        expect(result.requirementTrees.primary[0].children[0].quantity).toBe(6);
        expect(result.requirementTrees.primary[0].children[0].children[0].id).toBe('Resin');
        expect(result.requirementTrees.primary[0].children[0].children[1]).toEqual(
            expect.objectContaining({ id: 'Refined_Oil', quantity: 3, quantityUnit: 'L', isRaw: true })
        );
        expect(result.requiredItemData).toEqual({ Wood: 6, Resin: 12, Refined_Oil: 3 });
        expect(result.requiredComponents.find((item) => item.id === 'Refined_Oil')).toEqual(
            expect.objectContaining({ quantity: 3, quantityUnit: 'L', isRaw: true })
        );
        expect(result.rawComponents).toEqual([
            expect.objectContaining({ id: 'Resin', quantity: 12 }),
            expect.objectContaining({ id: 'Refined_Oil', quantity: 3, quantityUnit: 'L' }),
        ]);
        expect(result.requiredRecipeSetIds).toEqual(['Bench', 'Sawmill']);
    });

    it('stops raw totals before alternate processing inputs', () => {
        const oreCatalog = {
            ...catalog,
            itemsById: {
                ...catalog.itemsById,
                Metal_Ore: { id: 'Metal_Ore', label: 'Iron Ore', imagePath: '/ore.png' },
                Frozen_Ore: { id: 'Frozen_Ore', label: 'Frozen Ore', imagePath: '/frozen.png' },
            },
            recipesById: {
                ...catalog.recipesById,
                'processor:Metal_Ore': {
                    id: 'processor:Metal_Ore',
                    name: 'Metal_Ore',
                    source: 'processor',
                    enabled: true,
                    inputs: [{ itemId: 'Frozen_Ore', quantity: 2 }],
                    outputs: [{ itemId: 'Metal_Ore', quantity: 1 }],
                    recipeSetIds: ['Cleaner'],
                },
                'processor:Plank': {
                    ...catalog.recipesById['processor:Plank'],
                    inputs: [{ itemId: 'Metal_Ore', quantity: 3 }],
                },
            },
            recipeIdsByOutputItemId: {
                ...catalog.recipeIdsByOutputItemId,
                Metal_Ore: ['processor:Metal_Ore'],
            },
            defaultRecipeIdByOutputItemId: {
                ...catalog.defaultRecipeIdByOutputItemId,
                Metal_Ore: 'processor:Metal_Ore',
            },
        };

        const result = calculateRequirements({
            selectedItems: [{ id: 'Plank', quantity: 1 }],
            catalog: oreCatalog,
            isRawItem: (label) => label.endsWith('Ore'),
        });

        expect(result.requiredItemData).toEqual({ Metal_Ore: 3, Frozen_Ore: 6 });
        expect(result.rawComponents).toEqual([expect.objectContaining({ id: 'Metal_Ore', quantity: 3 })]);
    });

    it('keeps a sub-item render key stable when its recipe changes', () => {
        const alternateCatalog = {
            ...catalog,
            recipesById: {
                ...catalog.recipesById,
                'processor:Wood_Alternate': {
                    ...catalog.recipesById['processor:Wood'],
                    id: 'processor:Wood_Alternate',
                    name: 'Wood_Alternate',
                    inputs: [{ itemId: 'Resin', quantity: 3 }],
                },
            },
            recipeIdsByOutputItemId: {
                ...catalog.recipeIdsByOutputItemId,
                Wood: ['processor:Wood', 'processor:Wood_Alternate'],
            },
        };
        const defaultResult = calculateRequirements({ selectedItems: [{ id: 'Plank', quantity: 1 }], catalog: alternateCatalog });
        const alternateResult = calculateRequirements({
            selectedItems: [{ id: 'Plank', quantity: 1 }],
            catalog: alternateCatalog,
            recipeOverrides: { Wood: 'processor:Wood_Alternate' },
        });
        const defaultWood = defaultResult.requirementTrees.primary[0].children[0];
        const alternateWood = alternateResult.requirementTrees.primary[0].children[0];

        expect(alternateWood.renderKey).toBe(defaultWood.renderKey);
        expect(alternateWood.nodeKey).not.toBe(defaultWood.nodeKey);
    });

    it('returns every recipe variant in reverse lookup', () => {
        const results = calculateReverseLookup({ selectedItems: [{ id: 'Wood' }], catalog });

        expect(results.map((result) => result.recipeId)).toEqual(['processor:Plank', 'processor:Plank_Bulk']);
        expect(results.every((result) => result.itemId === 'Plank')).toBe(true);
    });
});