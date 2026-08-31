export const CRAFTING_CATALOG_SCHEMA_VERSION = 2;

export const canonicalizeItemId = (catalog, value) => {
    if (!value) return null;
    if (catalog.itemsById?.[value]) return value;

    const aliasedItemId = catalog.itemIdByAlias?.[value];
    if (aliasedItemId) return aliasedItemId;

    const legacyRecipe = catalog.recipesById?.[`processor:${value}`];
    return legacyRecipe?.outputs?.length === 1 ? legacyRecipe.outputs[0].itemId : null;
};

export const getRecipeIdsForItem = (catalog, itemId, { enabledOnly = true } = {}) => {
    const canonicalItemId = canonicalizeItemId(catalog, itemId);
    const recipeIds = catalog.recipeIdsByOutputItemId?.[canonicalItemId] ?? [];
    return enabledOnly ? recipeIds.filter((recipeId) => catalog.recipesById?.[recipeId]?.enabled) : recipeIds;
};

export const resolveRecipeForItem = (catalog, itemId, recipeOverrides = {}) => {
    const canonicalItemId = canonicalizeItemId(catalog, itemId);
    if (!canonicalItemId) return null;

    const recipeIds = getRecipeIdsForItem(catalog, canonicalItemId);
    const overrideId = recipeOverrides[canonicalItemId];
    const recipeId = recipeIds.includes(overrideId)
        ? overrideId
        : catalog.defaultRecipeIdByOutputItemId?.[canonicalItemId] ?? recipeIds[0];
    return catalog.recipesById?.[recipeId] ?? null;
};

export const getRecipeOutputQuantity = (recipe, itemId) => {
    const output = recipe?.outputs?.find((value) => value.itemId === itemId);
    return output?.quantity ?? 1;
};

export const getItemLabel = (catalog, itemId) => catalog.itemsById?.[itemId]?.label ?? itemId?.replace(/_/g, ' ') ?? '';

export const getRecipeLabel = (catalog, recipeId) => {
    const recipe = catalog.recipesById?.[recipeId];
    if (!recipe) return recipeId;
    return recipe.name.replace(/_/g, ' ');
};

export const getCatalogItemOptions = (catalog) => {
    const relevantItemIds = new Set([
        ...Object.keys(catalog.recipeIdsByOutputItemId ?? {}),
        ...Object.keys(catalog.recipeIdsByInputItemId ?? {}),
    ]);
    return [...relevantItemIds]
        .map((itemId) => {
            const item = catalog.itemsById?.[itemId];
            const defaultRecipe = resolveRecipeForItem(catalog, itemId);
            return item
                ? {
                      ...item,
                      recipeCount: getRecipeIdsForItem(catalog, itemId).length,
                      outputQuantity: getRecipeOutputQuantity(defaultRecipe, itemId),
                  }
                : null;
        })
        .filter(Boolean);
};

export const migrateTabToCatalog = (tab, catalog) => {
    const migratedItems = [];
    const seenItemIds = new Set();
    const recipeOverrides = {};

    Object.entries(tab?.recipeOverrides ?? {}).forEach(([legacyItemId, recipeId]) => {
        const itemId = canonicalizeItemId(catalog, legacyItemId);
        if (itemId && getRecipeIdsForItem(catalog, itemId).includes(recipeId)) {
            recipeOverrides[itemId] = recipeId;
        }
    });

    (tab?.items ?? []).forEach((item) => {
        const itemId = canonicalizeItemId(catalog, item.id);
        if (!itemId) return;

        if (item.recipeId && getRecipeIdsForItem(catalog, itemId).includes(item.recipeId)) {
            recipeOverrides[itemId] = item.recipeId;
        } else {
            const legacyRecipeId = `processor:${item.id}`;
            if (getRecipeIdsForItem(catalog, itemId).includes(legacyRecipeId)) {
                recipeOverrides[itemId] = legacyRecipeId;
            }
        }

        if (seenItemIds.has(itemId)) {
            const existingItem = migratedItems.find((value) => value.id === itemId);
            existingItem.quantity += item.quantity ?? 1;
            return;
        }
        seenItemIds.add(itemId);
        migratedItems.push({ id: itemId, quantity: item.quantity ?? 1 });
    });

    return {
        ...tab,
        items: migratedItems,
        recipeOverrides,
        completedNodeKeys: Array.isArray(tab?.completedNodeKeys) ? tab.completedNodeKeys : [],
    };
};