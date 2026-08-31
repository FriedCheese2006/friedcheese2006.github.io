import fs from 'node:fs';
import { describe, expect, it } from 'vitest';

import { isRawItem } from './icarusUi';
import { getRecipeIdsForItem } from './recipeCatalog';
import { calculateRequirements } from './requirementTree';

const catalog = JSON.parse(fs.readFileSync('public/icarus-game/Data/D_CraftingCatalog.json', 'utf8'));

const findChild = (node, itemId) => node.children.find((child) => child.id === itemId);

describe('generated catalog requirement regressions', () => {
    it('expands Material Processor through Steel Bloom and its selected inputs', () => {
        const result = calculateRequirements({
            selectedItems: [{ id: 'Material_Processor', quantity: 1 }],
            catalog,
            isRawItem,
        });

        const screw = findChild(result.requirementTrees.primary[0], 'Steel_Screw');
        const ingot = findChild(screw, 'Steel_Ingot');
        const bloom = findChild(ingot, 'Steel_Bloom');

        expect(getRecipeIdsForItem(catalog, 'Steel_Bloom')).toHaveLength(5);
        expect(bloom.recipeId).toBe('processor:Steel_Bloom');
        expect(bloom.children.map((child) => child.id)).toEqual(['Metal_Ore', 'Coal_Ore']);
    });

    it('counts Refined Oil as a terminal raw resource in liters', () => {
        const result = calculateRequirements({
            selectedItems: [{ id: 'Plastics', quantity: 1 }],
            catalog,
            recipeOverrides: { Plastics: 'processor:Oil_Plastics' },
            isRawItem,
        });
        const oil = findChild(result.requirementTrees.primary[0], 'Refined_Oil');

        expect(oil).toEqual(expect.objectContaining({ quantity: 0.5, quantityUnit: 'L', isRaw: true, recipeId: null }));
        expect(result.requiredItemData.Refined_Oil).toBe(0.5);
    });

    it('keeps stations on a raw ore using a Noxious Crust recipe', () => {
        const result = calculateRequirements({
            selectedItems: [{ id: 'Metal_Ore', quantity: 5 }],
            catalog,
            recipeOverrides: { Metal_Ore: 'processor:Pyritic_Crust_Iron' },
            isRawItem,
        });
        const ore = result.requirementTrees.primary[0];

        expect(ore.isRaw).toBe(true);
        expect(ore.recipeSetIds).toEqual(['Cleaning_Device', 'Exotic_Processor']);
        expect(ore.children.map((child) => child.id)).toEqual(['Pyritic_Crust_Iron']);
    });
});