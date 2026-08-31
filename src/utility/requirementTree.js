import { getItemLabel, getRecipeLabel, getRecipeOutputQuantity, resolveRecipeForItem } from './recipeCatalog';

const addToTotals = (totals, itemId, quantity) => {
    totals[itemId] = (totals[itemId] ?? 0) + quantity;
};

export const calculateRequirements = ({
    selectedItems,
    catalog,
    recipeOverrides = {},
    completedNodeKeys = [],
    includeStationComponents = false,
    isRawItem = () => false,
}) => {
    const totals = {};
    const requiredRecipeSetIds = new Set();
    const completedKeys = new Set(completedNodeKeys);

    const buildNode = (itemId, quantity, activePath, keyPrefix) => {
        const recipe = resolveRecipeForItem(catalog, itemId, recipeOverrides);
        const recipeId = recipe?.id ?? 'raw';
        const nodeKey = `${keyPrefix}:${recipeId}`;
        const label = getItemLabel(catalog, itemId);
        const item = catalog.itemsById?.[itemId];
        const node = {
            id: itemId,
            nodeKey,
            quantity,
            label,
            imagePath: item?.imagePath,
            isRaw: item?.isResource || isRawItem(label),
            quantityUnit: item?.quantityUnit ?? null,
            children: [],
            completed: completedKeys.has(nodeKey),
            recipeId: recipe?.id ?? null,
            outputQuantity: getRecipeOutputQuantity(recipe, itemId),
            recipeSetIds: recipe?.recipeSetIds ?? [],
        };

        if (!recipe || activePath.has(itemId)) return node;
        if (node.recipeSetIds[0]) requiredRecipeSetIds.add(node.recipeSetIds[0]);

        const nextPath = new Set(activePath);
        nextPath.add(itemId);
        const multiplier = quantity / node.outputQuantity;
        recipe.inputs.forEach((input, index) => {
            const inputQuantity = input.quantity * multiplier;
            addToTotals(totals, input.itemId, inputQuantity);
            const childRecipe = resolveRecipeForItem(catalog, input.itemId, recipeOverrides);
            const childKeyPrefix = `${nodeKey}>${input.itemId}:${index}`;
            const childKey = `${childKeyPrefix}:${childRecipe?.id ?? 'raw'}`;
            const childLabel = getItemLabel(catalog, input.itemId);
            const childItem = catalog.itemsById?.[input.itemId];
            const child = {
                id: input.itemId,
                nodeKey: childKey,
                quantity: inputQuantity,
                label: childLabel,
                imagePath: childItem?.imagePath,
                isRaw: childItem?.isResource || isRawItem(childLabel),
                quantityUnit: childItem?.quantityUnit ?? input.quantityUnit ?? null,
                children: [],
                completed: completedKeys.has(childKey),
                recipeId: childRecipe?.id ?? null,
                outputQuantity: getRecipeOutputQuantity(childRecipe, input.itemId),
                recipeSetIds: childRecipe?.recipeSetIds ?? [],
            };
            node.children.push(child);

            if (childRecipe && !nextPath.has(input.itemId)) {
                node.children[index] = buildNode(input.itemId, inputQuantity, nextPath, childKeyPrefix);
            }
        });
        return node;
    };

    const primary = selectedItems.map((item, index) => buildNode(item.id, item.quantity ?? 1, new Set(), `primary:${item.id}:${index}`));
    const stations = [];
    if (includeStationComponents) {
        const processedRecipeSetIds = new Set();
        while (true) {
            const pendingRecipeSetIds = [...requiredRecipeSetIds].filter((recipeSetId) => !processedRecipeSetIds.has(recipeSetId));
            if (pendingRecipeSetIds.length === 0) break;
            pendingRecipeSetIds.forEach((recipeSetId, index) => {
                processedRecipeSetIds.add(recipeSetId);
                const stationItemId = catalog.recipeSetsById?.[recipeSetId]?.itemId;
                if (stationItemId) {
                    stations.push(buildNode(stationItemId, 1, new Set(), `station:${recipeSetId}:${index}`));
                }
            });
        }
    }

    const requiredComponents = Object.entries(totals)
        .map(([itemId, quantity]) => {
            const label = getItemLabel(catalog, itemId);
            const item = catalog.itemsById?.[itemId];
            return {
                id: itemId,
                quantity: item?.quantityUnit ? quantity : Math.ceil(quantity),
                quantityUnit: item?.quantityUnit ?? null,
                label,
                isRaw: item?.isResource || isRawItem(label),
            };
        })
        .sort((left, right) => right.quantity - left.quantity || left.label.localeCompare(right.label));

    return {
        requirementTrees: { primary, stations },
        requiredItemData: totals,
        requiredComponents,
        requiredRecipeSetIds: [...requiredRecipeSetIds].sort(),
    };
};

export const calculateReverseLookup = ({ selectedItems, catalog }) => {
    const queue = selectedItems.map((item) => ({ itemId: item.id, depth: 0 }));
    const queuedItemIds = new Set(queue.map((item) => item.itemId));
    const seenResults = new Set();
    const results = [];

    while (queue.length > 0) {
        const current = queue.shift();
        const recipeIds = catalog.recipeIdsByInputItemId?.[current.itemId] ?? [];
        recipeIds.forEach((recipeId) => {
            const recipe = catalog.recipesById?.[recipeId];
            if (!recipe?.enabled) return;
            recipe.outputs.forEach((output) => {
                const resultKey = `${recipeId}:${output.itemId}`;
                if (!seenResults.has(resultKey)) {
                    seenResults.add(resultKey);
                    results.push({
                        id: resultKey,
                        recipeId,
                        itemId: output.itemId,
                        label: getItemLabel(catalog, output.itemId),
                        recipeLabel: getRecipeLabel(catalog, recipeId),
                        depth: current.depth + 1,
                    });
                }
                if (!queuedItemIds.has(output.itemId)) {
                    queuedItemIds.add(output.itemId);
                    queue.push({ itemId: output.itemId, depth: current.depth + 1 });
                }
            });
        });
    }

    return results.sort((left, right) => left.depth - right.depth || left.label.localeCompare(right.label));
};