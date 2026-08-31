import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { nextTick } from 'vue';

import { WORKSPACE_MODES, createWorkspaceState } from '@/utility/workspaceState';

const storageValues = new Map();
const localStorageStub = {
    getItem: (key) => storageValues.get(key) ?? null,
    setItem: (key, value) => storageValues.set(key, String(value)),
    removeItem: (key) => storageValues.delete(key),
    clear: () => storageValues.clear(),
    key: (index) => [...storageValues.keys()][index] ?? null,
    get length() {
        return storageValues.size;
    },
};

let useIcarusStore;
let saveStateToServer;

beforeAll(async () => {
    vi.stubGlobal('localStorage', localStorageStub);
    ({ saveStateToServer, useIcarusStore } = await import('./icarus'));
});

beforeEach(() => {
    localStorageStub.clear();
    setActivePinia(createPinia());
});

describe('Icarus workspace actions', () => {
    it('routes items and preserves both workspace selections in local storage', async () => {
        const store = useIcarusStore();
        store.workspaceState = createWorkspaceState();
        store.catalog = {
            itemsById: {
                Wall: { id: 'Wall', label: 'Wall', isFood: false },
                Stew: { id: 'Stew', label: 'Stew', isFood: true },
            },
            itemIdByAlias: { Wall: 'Wall', Stew: 'Stew' },
            recipesById: {
                'processor:Wall': {
                    id: 'processor:Wall',
                    enabled: true,
                    outputs: [{ itemId: 'Wall', quantity: 1 }],
                },
                'processor:Stew': {
                    id: 'processor:Stew',
                    enabled: true,
                    outputs: [{ itemId: 'Stew', quantity: 1 }],
                },
            },
            recipeIdsByOutputItemId: {
                Wall: ['processor:Wall'],
                Stew: ['processor:Stew'],
            },
            defaultRecipeIdByOutputItemId: {
                Wall: 'processor:Wall',
                Stew: 'processor:Stew',
            },
        };

        const itemTab = store.openItemTab('Wall');
        store.setRecipeSearch(WORKSPACE_MODES.ITEMS, 'stone');
        const foodTab = store.openItemTab('Stew');
        store.setRecipeSearch(WORKSPACE_MODES.FOOD, 'soup');

        expect(store.activeMode).toBe(WORKSPACE_MODES.FOOD);
        expect(store.workspaceState.workspaces.items).toMatchObject({ activeTabId: itemTab.id, search: 'stone' });
        expect(store.workspaceState.workspaces.food).toMatchObject({ activeTabId: foodTab.id, search: 'soup' });

        store.setActiveMode(WORKSPACE_MODES.ITEMS);
        expect(store.activeTab.id).toBe(itemTab.id);

        await nextTick();
        const persisted = JSON.parse(localStorageStub.getItem('icarusCalculator/workspace-state'));
        expect(persisted.workspaces.items.activeTabId).toBe(itemTab.id);
        expect(persisted.workspaces.food.activeTabId).toBe(foodTab.id);
    });

    it('serializes server state and rejects unsuccessful writes', async () => {
        const store = useIcarusStore();
        store.workspaceState = createWorkspaceState();

        const fetchMock = vi.fn().mockResolvedValueOnce({ ok: true, status: 200 });
        vi.stubGlobal('fetch', fetchMock);
        await saveStateToServer(store);

        expect(fetchMock).toHaveBeenCalledWith('/api/state', expect.objectContaining({ method: 'PUT' }));
        const request = fetchMock.mock.calls[0][1];
        expect(JSON.parse(request.body)).toMatchObject({
            tabs: { version: expect.any(Number), workspaces: expect.any(Object) },
            settings: expect.any(Object),
        });

        fetchMock.mockResolvedValueOnce({ ok: false, status: 503 });
        await expect(saveStateToServer(store)).rejects.toThrow('Server returned 503');
    });
});