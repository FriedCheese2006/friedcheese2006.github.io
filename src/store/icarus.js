import { reactive, watch } from 'vue';
import { defineStore } from 'pinia';
import { useStorage } from '@vueuse/core';
import { useFuse } from '@vueuse/integrations/useFuse';
import { useAuth } from '@/composables/useAuth';

import { GAME_ASSETS_URL, LOCAL_STORAGE_PREFIX } from '@/constants/common';
import { generateHighlightedText } from '@/utility/icarusUi';
import {
    CRAFTING_CATALOG_SCHEMA_VERSION,
    canonicalizeItemId,
    getCatalogItemOptions,
    getRecipeIdsForItem,
    getRecipeOutputQuantity,
    migrateTabToCatalog,
    resolveRecipeForItem,
} from '@/utility/recipeCatalog';
import {
    WORKSPACE_MODES,
    createWorkspaceState,
    getItemWorkspaceMode,
    partitionCatalogItemOptions,
} from '@/utility/workspaceState';

// utility methods
let tabIdCounter = 0;
const generateTabId = () => `${Date.now()}-${tabIdCounter++}`;
const generateNewTab = (title = 'Planning') =>
    reactive({
        id: generateTabId(),
        title,
        items: [],
        recipeOverrides: {},
        completedNodeKeys: [],
    });
const isDefaultDisplayTab = (tab) => tab?.title === 'Planning' && Array.isArray(tab.items) && tab.items.length === 0;
const sanitizeTabs = (tabs = []) => tabs.filter((tab) => !isDefaultDisplayTab(tab));
const findTabIndex = (id, tabs) => tabs.findIndex((tab) => tab.id === id);
const findTabIndexByItemId = (itemId, tabs) => tabs.findIndex((tab) => tab.items?.some((item) => item.id === itemId));
const getWorkspace = (store, mode = store.activeMode) => store.workspaceState.workspaces[mode];
const serializeWorkspaceState = (state) =>
    createWorkspaceState({
        ...state,
        workspaces: Object.fromEntries(
            Object.entries(state.workspaces).map(([mode, workspace]) => [
                mode,
                {
                    ...workspace,
                    tabs: sanitizeTabs(workspace.tabs),
                },
            ])
        ),
    });
let syncStateTimeoutId = null;

export const saveStateToServer = async (store) => {
    const workspaceState = serializeWorkspaceState(store.workspaceState);
    const response = await fetch('/api/state', {
        method: 'PUT',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            tabs: JSON.parse(JSON.stringify(workspaceState)),
            settings: JSON.parse(JSON.stringify(store.settings)),
        }),
    });
    if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
    }
};

const queueSyncStateToServer = (store) => {
    if (syncStateTimeoutId) {
        clearTimeout(syncStateTimeoutId);
    }

    syncStateTimeoutId = setTimeout(async () => {
        const auth = useAuth();
        if (!auth.isLoggedIn.value) return;

        try {
            console.log('[State Sync] Saving workspaces to server');

            await saveStateToServer(store);
            console.log('[State Sync] Saved successfully');
        } catch (e) {
            console.warn('[State Sync] Could not save state to server:', e);
        }
    }, 1500);
};

// default state
const legacyTabData = useStorage(`${LOCAL_STORAGE_PREFIX}/tabs`, []);
legacyTabData.value = sanitizeTabs(legacyTabData.value);
const workspaceData = useStorage(
    `${LOCAL_STORAGE_PREFIX}/workspace-state`,
    createWorkspaceState(null, legacyTabData.value),
    localStorage,
    { mergeDefaults: false }
);
workspaceData.value = createWorkspaceState(workspaceData.value, legacyTabData.value);

const settingsData = useStorage(
    `${LOCAL_STORAGE_PREFIX}/settings`,
    {
        includeStationComponents: false,
        splitRawComponents: true,
        searchFuzzyMatch: true,
    },
    localStorage,
    { mergeDefaults: true }
);

// * data store
export const useIcarusStore = defineStore('icarus', {
    state: () => ({
        workspaceState: workspaceData,
        settings: settingsData,

        catalog: {
            schemaVersion: null,
            itemsById: {},
            itemIdByAlias: {},
            recipesById: {},
            recipeIdsByOutputItemId: {},
            recipeIdsByInputItemId: {},
            defaultRecipeIdByOutputItemId: {},
            recipeSetsById: {},
        },
        recipeOptionsByMode: {
            [WORKSPACE_MODES.ITEMS]: [],
            [WORKSPACE_MODES.FOOD]: [],
        },
        isLoadingRecipes: false,
    }),
    getters: {
        activeMode: (state) => state.workspaceState.activeMode,
        activeWorkspace: (state) => state.workspaceState.workspaces[state.workspaceState.activeMode],
        tabs() {
            return this.activeWorkspace.tabs;
        },
        activeTabId() {
            return this.activeWorkspace.activeTabId;
        },
        recipeSearch() {
            return this.activeWorkspace.search;
        },
        activeTab() {
            return this.tabs.find((tab) => tab.id === this.activeTabId);
        },
        tabCount() {
            return this.tabs.length;
        },
        includeStationComponents(state) {
            return state.settings.includeStationComponents;
        },
        splitRawComponents(state) {
            return state.settings.splitRawComponents;
        },
        sortedRecipeOptionsForMode: (state) => (mode) => {
            return [...(state.recipeOptionsByMode[mode] ?? [])].sort((a, b) => a.label.localeCompare(b.label));
        },
        sortedRecipeOptions() {
            return this.sortedRecipeOptionsForMode(this.activeMode);
        },
        filteredRecipeOptionsForMode: (state) => (mode) => {
            const recipeSearch = state.workspaceState.workspaces[mode]?.search ?? '';
            const sortedRecipeOptions = [...(state.recipeOptionsByMode[mode] ?? [])].sort((a, b) => a.label.localeCompare(b.label));
            if (recipeSearch) {

                const searchOptions = {
                    fuseOptions: {
                        keys: ['label'],
                        isCaseSensitive: false,
                        location: 0,
                        threshold: state.settings.searchFuzzyMatch ? undefined : 0,
                        distance: 100,
                        includeScore: true,
                        includeMatches: true,
                    },
                    resultLimit: undefined,
                    matchAllWhenSearchEmpty: true,
                };
                const { results } = useFuse(recipeSearch, sortedRecipeOptions, searchOptions);

                // map { item, refIndex } to an array of items
                return results.value.map((result) => ({
                    ...result.item,
                    highlightedLabel: result.matches ? generateHighlightedText(result.item.label, result.matches?.[0]?.indices) : result.item.label,
                }));
            }
            return sortedRecipeOptions;
        },
        filteredRecipeOptions() {
            return this.filteredRecipeOptionsForMode(this.activeMode);
        },
    },
    actions: {
        setActiveMode(mode) {
            if (Object.values(WORKSPACE_MODES).includes(mode)) {
                this.workspaceState.activeMode = mode;
            }
        },
        setRecipeSearch(mode, value) {
            const workspace = getWorkspace(this, mode);
            if (workspace) {
                workspace.search = value ?? '';
            }
        },
        // * tab methods
        addTab(mode = this.activeMode) {
            const workspace = getWorkspace(this, mode);
            const tab = generateNewTab();
            workspace.tabs.push(tab);
            workspace.activeTabId = tab.id;
            return tab;
        },
        removeTab(id, mode = this.activeMode) {
            const workspace = getWorkspace(this, mode);
            const tabIndex = findTabIndex(id, workspace.tabs);

            if (tabIndex !== -1) {
                workspace.tabs.splice(tabIndex, 1);
            } else {
                console.error(`Could not find tab with id ${id}`, this.tabs);
                return;
            }

            const newTabIndex = Math.min(tabIndex, workspace.tabs.length - 1);
            const newActiveTab = workspace.tabs[newTabIndex];

            workspace.activeTabId = newActiveTab?.id ?? null;
        },
        setActiveTab(id, mode = this.activeMode) {
            const workspace = getWorkspace(this, mode);
            if (workspace?.tabs.some((tab) => tab.id === id)) {
                workspace.activeTabId = id;
            }
        },
        setTabTitle(id, title, mode = this.activeMode) {
            const workspace = getWorkspace(this, mode);
            const matchingId = findTabIndex(id, workspace.tabs);
            if (matchingId !== -1) {
                workspace.tabs[matchingId].title = title;
            }
        },
        openItemTab(itemId, recipeId = null) {
            const canonicalItemId = canonicalizeItemId(this.catalog, itemId);
            if (!canonicalItemId) return null;
            const mode = getItemWorkspaceMode(this.catalog, canonicalItemId);
            const workspace = getWorkspace(this, mode);
            this.setActiveMode(mode);

            const existingTabIndex = findTabIndexByItemId(canonicalItemId, workspace.tabs);

            if (existingTabIndex !== -1) {
                if (recipeId && getRecipeIdsForItem(this.catalog, canonicalItemId).includes(recipeId)) {
                    workspace.tabs[existingTabIndex].recipeOverrides[canonicalItemId] = recipeId;
                    workspace.tabs[existingTabIndex].completedNodeKeys = [];
                }
                workspace.activeTabId = workspace.tabs[existingTabIndex].id;
                return workspace.tabs[existingTabIndex];
            }

            const itemData = this.catalog.itemsById[canonicalItemId];
            const tab = generateNewTab();
            if (recipeId && getRecipeIdsForItem(this.catalog, canonicalItemId).includes(recipeId)) {
                tab.recipeOverrides[canonicalItemId] = recipeId;
            }
            const recipe = resolveRecipeForItem(this.catalog, canonicalItemId, tab.recipeOverrides);
            const outputQuantity = getRecipeOutputQuantity(recipe, canonicalItemId);

            tab.title = itemData?.label ?? tab.title;
            tab.items.push({
                id: canonicalItemId,
                quantity: outputQuantity,
            });

            workspace.tabs.push(tab);
            workspace.activeTabId = tab.id;

            return tab;
        },

        // * item list methods
        addItem(itemId, quantity = 1) {
            // implicitly adds or updates item to currently selected tab
            const workspace = getWorkspace(this);
            const currentTab = workspace.tabs.find((tab) => tab.id === workspace.activeTabId);

            if (currentTab) {
                const canonicalItemId = canonicalizeItemId(this.catalog, itemId);
                if (!canonicalItemId) return;
                const matchingItem = currentTab.items.find((item) => item.id === canonicalItemId);
                const recipe = resolveRecipeForItem(this.catalog, canonicalItemId, currentTab.recipeOverrides);
                const outputQuantity = getRecipeOutputQuantity(recipe, canonicalItemId);

                if (matchingItem) {
                    matchingItem.quantity += outputQuantity;
                } else {
                    currentTab.items.push({
                        id: canonicalItemId,
                        quantity: quantity ?? outputQuantity,
                    });
                }
            } else {
                console.error(`Could not find tab with id ${this.activeTabId}`, this.tabs);
            }
        },
        removeItem(itemId) {
            // implicitly removes item from currently selected tab
            const workspace = getWorkspace(this);
            const currentTab = workspace.tabs.find((tab) => tab.id === workspace.activeTabId);

            if (currentTab) {
                const matchingItemIndex = currentTab.items.findIndex((item) => item.id === itemId);
                currentTab.items.splice(matchingItemIndex, 1);
            } else {
                console.error(`Could not find tab with id ${this.activeTabId}`, this.tabs);
            }
        },
        setIncludeStationComponents(value) {
            this.settings.includeStationComponents = value;
        },
        setSplitRawComponents(value) {
            this.settings.splitRawComponents = value;
        },
        setRecipeOverride(tabId, itemId, recipeId) {
            const tab = Object.values(this.workspaceState.workspaces)
                .flatMap((workspace) => workspace.tabs)
                .find((value) => value.id === tabId);
            const canonicalItemId = canonicalizeItemId(this.catalog, itemId);
            if (!tab || !canonicalItemId || !getRecipeIdsForItem(this.catalog, canonicalItemId).includes(recipeId)) return;
            tab.recipeOverrides = {
                ...(tab.recipeOverrides ?? {}),
                [canonicalItemId]: recipeId,
            };
            tab.completedNodeKeys = [];
        },

        // * recipe data
        async loadRecipeData() {
            this.isLoadingRecipes = true;
            const catalogResponse = await fetch(`${GAME_ASSETS_URL}/Data/D_CraftingCatalog.json`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });
            if (!catalogResponse.ok) {
                this.isLoadingRecipes = false;
                throw new Error(`Unable to load crafting catalog: ${catalogResponse.status}`);
            }
            const catalog = await catalogResponse.json();
            if (catalog.schemaVersion !== CRAFTING_CATALOG_SCHEMA_VERSION) {
                this.isLoadingRecipes = false;
                throw new Error(`Unsupported crafting catalog schema: ${catalog.schemaVersion}`);
            }

            const startTime = performance.now();
            this.catalog = catalog;
            this.recipeOptionsByMode = partitionCatalogItemOptions(getCatalogItemOptions(catalog));
            Object.values(this.workspaceState.workspaces).forEach((workspace) => {
                workspace.tabs.splice(0, workspace.tabs.length, ...workspace.tabs.map((tab) => migrateTabToCatalog(tab, catalog)));
                if (!workspace.tabs.some((tab) => tab.id === workspace.activeTabId)) {
                    workspace.activeTabId = workspace.tabs[0]?.id ?? null;
                }
            });
            this.isLoadingRecipes = false;

            console.log(`Processed data in ${performance.now() - startTime}ms`);

            // Sync state from server if the user is logged in
            const auth = useAuth();
            await auth.init();
            console.log('[State Sync] Auth initialized:', { isLoggedIn: auth.isLoggedIn.value });
            
            if (auth.isLoggedIn.value) {
                await this.syncStateFromServer();
                
                // Immediately push current state to server to ensure sync
                // (handles case where local tabs existed before login)
                console.log('[State Sync] Pushing current state to server...');
                await this.syncStateToServer();
            } else {
                console.log('[State Sync] User not logged in, skipping server sync');
            }

            // Watch for local changes and sync to server when logged in
            watch(
                () => [JSON.stringify(this.workspaceState), JSON.stringify(this.settings)],
                () => {
                    queueSyncStateToServer(this);
                },
                { deep: true }
            );
        },

        async syncStateFromServer() {
            try {
                console.log('[State Sync] Fetching state from server...');
                const response = await fetch('/api/state', { credentials: 'same-origin' });
                if (!response.ok) {
                    console.warn(`[State Sync] Server returned ${response.status}`);
                    return;
                }
                const { tabs, settings } = await response.json();
                console.log('[State Sync] Received from server:', { 
                    tabCount: tabs?.length ?? 'null', 
                    hasSettings: !!settings 
                });
                
                if (Array.isArray(tabs)) {
                    const workspace = getWorkspace(this, WORKSPACE_MODES.ITEMS);
                    const cleanTabs = sanitizeTabs(tabs).map((tab) => migrateTabToCatalog(tab, this.catalog));
                    workspace.tabs.splice(0, workspace.tabs.length, ...cleanTabs);
                    workspace.activeTabId = cleanTabs[0]?.id ?? null;
                    console.log('[State Sync] Migrated legacy server tabs into Items');
                } else if (tabs?.version) {
                    const serverState = createWorkspaceState(tabs);
                    this.workspaceState.activeMode = serverState.activeMode;
                    Object.entries(serverState.workspaces).forEach(([mode, serverWorkspace]) => {
                        const workspace = getWorkspace(this, mode);
                        const cleanTabs = sanitizeTabs(serverWorkspace.tabs).map((tab) => migrateTabToCatalog(tab, this.catalog));
                        workspace.tabs.splice(0, workspace.tabs.length, ...cleanTabs);
                        workspace.activeTabId = cleanTabs.some((tab) => tab.id === serverWorkspace.activeTabId)
                            ? serverWorkspace.activeTabId
                            : cleanTabs[0]?.id ?? null;
                        workspace.search = serverWorkspace.search;
                    });
                    console.log('[State Sync] Workspaces synced');
                } else {
                    console.log('[State Sync] No workspace data on server, keeping local state');
                }
                
                if (settings && typeof settings === 'object') {
                    Object.assign(this.settings, settings);
                    console.log('[State Sync] Settings updated');
                }
            } catch (e) {
                console.error('[State Sync] Failed to load state from server:', e);
            }
        },

        async syncStateToServer() {
            try {
                console.log('[State Sync] Pushing workspaces to server');

                await saveStateToServer(this);
                console.log('[State Sync] Pushed successfully');
            } catch (e) {
                console.error('[State Sync] Failed to push state to server:', e);
            }
        },

    },
});
