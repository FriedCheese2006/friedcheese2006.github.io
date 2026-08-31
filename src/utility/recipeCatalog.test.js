import { describe, expect, it } from 'vitest';

import {
    canonicalizeItemId,
    getCatalogItemOptions,
    getRecipeOutputQuantity,
    migrateTabToCatalog,
    resolveRecipeForItem,
} from './recipeCatalog';

const catalog = {
    schemaVersion: 1,
    itemsById: {
        Flour: { id: 'Flour', label: 'Flour', imagePath: '/icarus-game/ItemIcons/Resources/Flour.png' },
        Wheat: { id: 'Wheat', label: 'Wheat', imagePath: '/icarus-game/ItemIcons/Resources/Wheat.png' },
    },
    itemIdByAlias: {
        Flour: 'Flour',
        Flour_Template: 'Flour',
        Wheat: 'Wheat',
    },
    recipesById: {
        'processor:Flour': {
            id: 'processor:Flour',
            name: 'Flour',
            source: 'processor',
            enabled: true,
            inputs: [{ itemId: 'Wheat', quantity: 10 }],
            outputs: [{ itemId: 'Flour', quantity: 1 }],
        },
        'processor:Flour_Corn': {
            id: 'processor:Flour_Corn',
            name: 'Flour_Corn',
            source: 'processor',
            enabled: true,
            inputs: [{ itemId: 'Wheat', quantity: 5 }],
            outputs: [{ itemId: 'Flour', quantity: 2 }],
        },
    },
    recipeIdsByOutputItemId: {
        Flour: ['processor:Flour', 'processor:Flour_Corn'],
    },
    recipeIdsByInputItemId: {
        Wheat: ['processor:Flour', 'processor:Flour_Corn'],
    },
    defaultRecipeIdByOutputItemId: {
        Flour: 'processor:Flour',
    },
};

describe('recipe catalog selectors', () => {
    it('resolves aliases, defaults, overrides, and output quantities', () => {
        expect(canonicalizeItemId(catalog, 'Flour_Template')).toBe('Flour');
        expect(resolveRecipeForItem(catalog, 'Flour').id).toBe('processor:Flour');
        const alternative = resolveRecipeForItem(catalog, 'Flour', { Flour: 'processor:Flour_Corn' });
        expect(alternative.id).toBe('processor:Flour_Corn');
        expect(getRecipeOutputQuantity(alternative, 'Flour')).toBe(2);
    });

    it('migrates legacy recipe IDs into canonical items and plan overrides', () => {
        const migrated = migrateTabToCatalog(
            {
                id: 'plan-1',
                items: [{ id: 'Flour_Corn', quantity: 4, recipeId: 'processor:missing' }],
            },
            catalog
        );

        expect(migrated.items).toEqual([{ id: 'Flour', quantity: 4 }]);
        expect(migrated.recipeOverrides).toEqual({ Flour: 'processor:Flour_Corn' });
        expect(migrated.completedNodeKeys).toEqual([]);
    });

    it('builds one search option per relevant item', () => {
        expect(getCatalogItemOptions(catalog)).toEqual([
            expect.objectContaining({ id: 'Flour', recipeCount: 2, outputQuantity: 1 }),
            expect.objectContaining({ id: 'Wheat', recipeCount: 0, outputQuantity: 1 }),
        ]);
    });
});