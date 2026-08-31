export const WORKSPACE_STATE_VERSION = 2;
export const WORKSPACE_MODES = Object.freeze({
    ITEMS: 'items',
    FOOD: 'food',
});

const workspaceModes = Object.values(WORKSPACE_MODES);

const normalizeWorkspace = (workspace = {}) => {
    const tabs = Array.isArray(workspace.tabs) ? workspace.tabs : [];
    const requestedActiveTabId = workspace.activeTabId ?? null;
    const activeTabId = tabs.some((tab) => tab.id === requestedActiveTabId) ? requestedActiveTabId : tabs[0]?.id ?? null;

    return {
        tabs,
        activeTabId,
        search: typeof workspace.search === 'string' ? workspace.search : '',
    };
};

export const createWorkspaceState = (value, legacyTabs = []) => {
    const isCurrentState = value?.version === WORKSPACE_STATE_VERSION && value.workspaces;
    const workspaces = isCurrentState
        ? value.workspaces
        : {
              [WORKSPACE_MODES.ITEMS]: { tabs: Array.isArray(value) ? value : legacyTabs },
              [WORKSPACE_MODES.FOOD]: {},
          };

    return {
        version: WORKSPACE_STATE_VERSION,
        activeMode: workspaceModes.includes(value?.activeMode) ? value.activeMode : WORKSPACE_MODES.ITEMS,
        workspaces: {
            [WORKSPACE_MODES.ITEMS]: normalizeWorkspace(workspaces[WORKSPACE_MODES.ITEMS]),
            [WORKSPACE_MODES.FOOD]: normalizeWorkspace(workspaces[WORKSPACE_MODES.FOOD]),
        },
    };
};

export const partitionCatalogItemOptions = (options) => ({
    [WORKSPACE_MODES.ITEMS]: options.filter((item) => !item.isFood),
    [WORKSPACE_MODES.FOOD]: options.filter((item) => item.isFood),
});

export const getItemWorkspaceMode = (catalog, itemId) =>
    catalog.itemsById?.[itemId]?.isFood ? WORKSPACE_MODES.FOOD : WORKSPACE_MODES.ITEMS;