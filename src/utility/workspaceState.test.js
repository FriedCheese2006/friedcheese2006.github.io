import { describe, expect, it } from 'vitest';

import {
    WORKSPACE_MODES,
    WORKSPACE_STATE_VERSION,
    createWorkspaceState,
    getItemWorkspaceMode,
    partitionCatalogItemOptions,
} from './workspaceState';

describe('workspace state', () => {
    it('migrates legacy tabs into the items workspace', () => {
        const tabs = [{ id: 'legacy-plan', title: 'Legacy plan', items: [] }];

        expect(createWorkspaceState(null, tabs)).toEqual({
            version: WORKSPACE_STATE_VERSION,
            activeMode: WORKSPACE_MODES.ITEMS,
            workspaces: {
                items: { tabs, activeTabId: 'legacy-plan', search: '' },
                food: { tabs: [], activeTabId: null, search: '' },
            },
        });
    });

    it('preserves valid independent workspace selections and searches', () => {
        const state = createWorkspaceState({
            version: WORKSPACE_STATE_VERSION,
            activeMode: WORKSPACE_MODES.FOOD,
            workspaces: {
                items: { tabs: [{ id: 'item-plan' }], activeTabId: 'item-plan', search: 'wall' },
                food: { tabs: [{ id: 'food-plan' }], activeTabId: 'food-plan', search: 'stew' },
            },
        });

        expect(state.activeMode).toBe(WORKSPACE_MODES.FOOD);
        expect(state.workspaces.items).toMatchObject({ activeTabId: 'item-plan', search: 'wall' });
        expect(state.workspaces.food).toMatchObject({ activeTabId: 'food-plan', search: 'stew' });
    });

    it('partitions every catalog option into exactly one workspace', () => {
        const options = [
            { id: 'Wall', isFood: false },
            { id: 'Stew', isFood: true },
            { id: 'Unknown' },
        ];

        const partitioned = partitionCatalogItemOptions(options);

        expect(partitioned.items.map((item) => item.id)).toEqual(['Wall', 'Unknown']);
        expect(partitioned.food.map((item) => item.id)).toEqual(['Stew']);
        expect([...partitioned.items, ...partitioned.food]).toHaveLength(options.length);
    });

    it('routes items according to their canonical food classification', () => {
        const catalog = { itemsById: { Wall: { isFood: false }, Stew: { isFood: true } } };

        expect(getItemWorkspaceMode(catalog, 'Wall')).toBe(WORKSPACE_MODES.ITEMS);
        expect(getItemWorkspaceMode(catalog, 'Stew')).toBe(WORKSPACE_MODES.FOOD);
    });
});