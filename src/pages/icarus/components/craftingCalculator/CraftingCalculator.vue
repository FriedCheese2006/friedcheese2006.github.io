<template>
    <div>
        <div v-if="!isLoadingRecipes && tab.items.length > 0">
            <div class="flex align-items-center" style="justify-content: space-between;">
                <h3 class="panel-title">{{ isReverseLookupMode ? 'Used In' : 'Crafting Requirements' }}</h3>
                <n-button circle size="small" quaternary @click="closeTab">
                    <template #icon>
                        <n-icon>
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </n-icon>
                    </template>
                </n-button>
            </div>
            <div v-if="!isReverseLookupMode" class="p-1 requirement-flow">
                <em v-if="requirementTrees.primary.length === 0" class="empty-subcategory-label">No crafting requirements available</em>
                <div v-else class="requirement-flow__list">
                    <div v-for="(node, index) in requirementTrees.primary" :key="`${node.id}-${node.quantity}`" class="requirement-section">
                        <div class="requirement-section__header">
                            <div class="requirement-section__item">
                                <n-image
                                    class="requirement-section__icon"
                                    width="48"
                                    height="48"
                                    :src="node.imagePath"
                                    :fallback-src="`${gameAssetsUrl}/Images/question-mark.png`"
                                    :preview-disabled="true"
                                />
                                <div class="requirement-section__details">
                                    <div class="requirement-section__label">{{ node.label ?? node.id }}</div>
                                    <recipe-selector
                                        v-if="hasRecipeAlternatives(node.id)"
                                        :catalog="catalog"
                                        :item-id="node.id"
                                        :selected-recipe-id="node.recipeId"
                                        @change="handleRecipeChange(node.id, $event)"
                                    />
                                </div>
                            </div>
                            <div class="requirement-section__quantity-input">
                                <n-input-number
                                    :value="getDraftQuantity(node.id)"
                                    placeholder="Quantity"
                                    :min="1"
                                    :max="100000"
                                    :step="node.outputQuantity ?? 1"
                                    :validator="validateQuantity"
                                    @update:value="onQuantityInput(node.id, $event)"
                                    @blur="onQuantityBlur(node.id)"
                                    size="medium"
                                />
                            </div>
                            <div v-if="getRecipeSets(node).length > 0" class="requirement-section__stations">
                                <div class="requirement-section__stations-label">Crafted at:</div>
                                <div class="requirement-section__stations-list">
                                    <div 
                                        v-for="station in getRecipeSets(node)" 
                                        :key="station.id"
                                        class="crafting-station"
                                    >
                                        <n-image
                                            class="crafting-station__icon"
                                            width="32"
                                            height="32"
                                            :src="station.imagePath"
                                            :fallback-src="`${gameAssetsUrl}/Images/question-mark.png`"
                                            :preview-disabled="true"
                                        />
                                        <div class="crafting-station__label">{{ station.label }}</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div v-if="node.children?.length > 0" class="requirement-section__ingredients">
                            <div class="requirement-section__ingredients-label">Ingredients:</div>
                            <requirement-tree-node 
                                v-for="child in node.children"
                                :key="child.nodeKey ?? `${node.id}-${child.id}-${child.quantity}`" 
                                :node="child"
                                :catalog="catalog"
                                :recipe-overrides="tab.recipeOverrides"
                                :game-assets-url="gameAssetsUrl"
                                @toggle-complete="handleToggleComplete"
                                @recipe-change="handleRecipeChange($event.itemId, $event.recipeId)"
                            ></requirement-tree-node>
                        </div>
                    </div>
                </div>
            </div>

            <div v-if="isReverseLookupMode || directReverseLookupResults.length > 0" class="p-1 reverse-lookup">
                <h3 v-if="!isReverseLookupMode" class="panel-title reverse-lookup__title">Used In</h3>
                <div v-if="directReverseLookupResults.length === 0" class="empty-subcategory-label">
                    This item is not used in any recipes.
                </div>
                <div v-else class="reverse-lookup__list">
                    <div 
                        v-for="result in directReverseLookupResults" 
                        :key="result.id"
                        class="reverse-lookup-item"
                        @click="openItemTab(result.itemId, result.recipeId)"
                    >
                        <n-image
                            class="reverse-lookup-item__icon"
                            width="40"
                            height="40"
                            :src="catalog.itemsById[result.itemId]?.imagePath"
                            :fallback-src="`${gameAssetsUrl}/Images/question-mark.png`"
                            :preview-disabled="true"
                        />
                        <div class="reverse-lookup-item__label">
                            {{ result.label }}
                            <div class="text-muted">{{ result.recipeLabel }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div v-else class="mb-3">
            <h3 class="panel-title">No Items</h3>
            <n-text type="info">You haven't added any items to this list yet.</n-text>
        </div>
    </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from 'pinia';

import RequirementTreeNode from './RequirementTreeNode.vue';
import RecipeSelector from './RecipeSelector.vue';
import { useIcarusStore } from '@/store/icarus';
import { isRawItem } from '@/utility/icarusUi';
import { getCraftingStations, getItemLabel, getRecipeIdsForItem, getRecipeOutputQuantity, resolveRecipeForItem } from '@/utility/recipeCatalog';
import { calculateRequirements, calculateReverseLookup } from '@/utility/requirementTree';
import { GAME_ASSETS_URL } from '@/constants/common';

export default {
    name: 'CraftingToolCalculator',
    components: {
        RequirementTreeNode,
        RecipeSelector,
    },
    props: {
        tab: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            gameAssetsUrl: GAME_ASSETS_URL,
            requiredItemData: {},
            requiredCraftingStations: [],
            requiredComponents: [],
            reverseLookupResults: [],
            requirementTrees: {
                primary: [],
                stations: [],
            },
            quantityDrafts: {},
            calcTimeoutId: null,
        };
    },
    watch: {
        includeStationComponents() {
            this.triggerCalc();
        },
        'tab.items': {
            handler() {
                this.syncQuantityDrafts();
                this.triggerCalc();
            },
            deep: true,
        },
    },
    computed: {
        ...mapState(useIcarusStore, ['catalog', 'isLoadingRecipes', 'settings']),
        ...mapGetters(useIcarusStore, ['includeStationComponents', 'splitRawComponents']),
        craftableComponents() {
            return this.requiredComponents.filter((item) => !item.isRaw);
        },
        rawComponents() {
            return this.requiredComponents.filter((item) => item.isRaw);
        },
        isReverseLookupMode() {
            const selectedItems = this.tab.items || [];
            if (selectedItems.length === 0) {
                return false;
            }
            return selectedItems.every((item) => getRecipeIdsForItem(this.catalog, item.id).length === 0);
        },
        directReverseLookupResults() {
            return this.reverseLookupResults.filter((item) => item.depth === 1);
        },
        downstreamReverseLookupResults() {
            return this.reverseLookupResults.filter((item) => item.depth > 1);
        },
    },
    methods: {
        ...mapActions(useIcarusStore, [
            'setIncludeStationComponents',
            'setSplitRawComponents',
            'setRecipeOverride',
            'openItemTab',
        ]),
        ensureTabCompletionState() {
            if (!Array.isArray(this.tab.completedNodeKeys)) {
                this.tab.completedNodeKeys = [];
            }
        },
        getCompletedNodeKeySet() {
            this.ensureTabCompletionState();
            return new Set(this.tab.completedNodeKeys);
        },
        getComponentLabel(componentId) {
            return getItemLabel(this.catalog, componentId);
        },
        getRecipeSets(node) {
            return getCraftingStations(this.catalog, node.recipeSetIds);
        },
        resolveRecipeForItemId(itemId) {
            return resolveRecipeForItem(this.catalog, itemId, this.tab.recipeOverrides ?? {});
        },
        sortInputs() {
            this.tab.items.sort((a, b) => {
                const aLabel = this.getComponentLabel(a.id);
                const bLabel = this.getComponentLabel(b.id);
                return aLabel.localeCompare(bLabel);
            });
        },
        getTabItem(itemId) {
            return (this.tab.items || []).find((item) => item.id === itemId);
        },
        getDefaultQuantity(itemId) {
            const recipe = this.resolveRecipeForItemId(itemId);
            return getRecipeOutputQuantity(recipe, itemId);
        },
        hasRecipeAlternatives(itemId) {
            return getRecipeIdsForItem(this.catalog, itemId).length > 1;
        },
        handleRecipeChange(itemId, recipeId) {
            this.setRecipeOverride(this.tab.id, itemId, recipeId);
            this.syncQuantityDrafts();
            this.triggerCalc();
        },
        syncQuantityDrafts() {
            const nextDrafts = {};

            (this.tab.items || []).forEach((item) => {
                const existingDraft = this.quantityDrafts[item.id];
                if (existingDraft === null || existingDraft === undefined) {
                    nextDrafts[item.id] = item.quantity ?? this.getDefaultQuantity(item.id);
                    return;
                }

                nextDrafts[item.id] = existingDraft;
            });

            this.quantityDrafts = nextDrafts;
        },
        getDraftQuantity(itemId) {
            if (this.quantityDrafts[itemId] === undefined) {
                return this.getTabItem(itemId)?.quantity ?? this.getDefaultQuantity(itemId);
            }

            return this.quantityDrafts[itemId];
        },
        onQuantityInput(itemId, value) {
            this.quantityDrafts = {
                ...this.quantityDrafts,
                [itemId]: value,
            };
        },
        onQuantityBlur(itemId) {
            const item = this.getTabItem(itemId);
            if (!item) {
                return;
            }

            const defaultQuantity = this.getDefaultQuantity(itemId);
            const draftValue = this.quantityDrafts[itemId];
            const normalizedValue = Number.isInteger(draftValue) && draftValue >= 1 ? draftValue : defaultQuantity;

            this.quantityDrafts = {
                ...this.quantityDrafts,
                [itemId]: normalizedValue,
            };

            if (item.quantity !== normalizedValue) {
                item.quantity = normalizedValue;
            }
        },
        validateQuantity(value) {
            return Number.isInteger(value);
        },
        removeItem(item) {
            const itemIndex = (this.tab.items || []).findIndex((i) => i.id === item.id);
            if (itemIndex > -1) {
                this.tab.items.splice(itemIndex, 1);
            }
        },
        closeTab() {
            this.$emit('close-tab', this.tab.id);
        },
        handleToggleComplete({ nodeKey, completed, childNodeKeys }) {
            if (!nodeKey) {
                return;
            }

            this.ensureTabCompletionState();
            const completedNodeKeySet = new Set(this.tab.completedNodeKeys);

            if (completed) {
                // Mark this node and its descendants as completed.
                completedNodeKeySet.add(nodeKey);
                childNodeKeys.forEach((key) => completedNodeKeySet.add(key));
            } else {
                // Unmark this node and its descendants.
                completedNodeKeySet.delete(nodeKey);
                childNodeKeys.forEach((key) => completedNodeKeySet.delete(key));
            }

            this.tab.completedNodeKeys = [...completedNodeKeySet];

            // Rebuild tree so `node.completed` flags reflect the latest completion Set.
            this.triggerCalc();
        },
        triggerCalc() {
            if (this.calcTimeoutId) {
                clearTimeout(this.calcTimeoutId);
            }

            this.calcTimeoutId = setTimeout(() => {
                this.calculateCatalogRequirements();
            }, 100);
        },
        calculateCatalogRequirements() {
            const selectedItems = this.tab.items || [];
            this.reverseLookupResults = calculateReverseLookup({ selectedItems, catalog: this.catalog });

            if (this.isReverseLookupMode) {
                this.requiredCraftingStations = [];
                this.requiredItemData = {};
                this.requiredComponents = [];
                this.requirementTrees = { primary: [], stations: [] };
                return;
            }

            const result = calculateRequirements({
                selectedItems,
                catalog: this.catalog,
                recipeOverrides: this.tab.recipeOverrides ?? {},
                completedNodeKeys: this.tab.completedNodeKeys ?? [],
                includeStationComponents: this.includeStationComponents,
                isRawItem,
            });
            this.requirementTrees = result.requirementTrees;
            this.requiredItemData = result.requiredItemData;
            this.requiredComponents = result.requiredComponents;
            this.requiredCraftingStations = result.requiredRecipeSetIds;
        },
    },
    mounted() {
        this.ensureTabCompletionState();
        this.syncQuantityDrafts();
        this.triggerCalc();
    },
};
</script>

<style scoped lang="scss">
.items-scroll-area {
    max-height: 390px;
    overflow-y: auto;
    padding-right: 0.25rem;
}

.text-muted {
    font-size: 0.75rem;
    opacity: 0.6;
    line-height: 1.1rem;
    vertical-align: middle;
}

.panel-title {
    margin: 0;
    font-family: var(--font-display);
    font-size: 1.35rem;
    letter-spacing: 0.035em;
    text-transform: uppercase;
    color: var(--theme-text);
}
.recipe-item {
    min-height: 60px;
    padding: 0.3rem 0.3rem 0.4rem 0.3rem;
    border-radius: 4px;

    &.stations {
        min-height: 35px;
    }

    .input-quantity {
        width: 5.5rem;
        margin-right: 0.5rem;
    }

    .icon {
        margin: 0 0.5rem 0 0;
    }

    .label-wrap {
        width: 9rem;
        min-width: 2.5rem;
    }

    .label {
        font-weight: 600;
        line-height: 18px;
    }

    .hover-button {
        visibility: hidden;
    }

    &:hover {
        background-color: rgba(222, 222, 255, 0.03);

        .hover-button {
            visibility: visible;
        }
    }
}

.list-enter-active,
.list-leave-active {
    transition: all 0.2s ease;
}
.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateX(-30px);
}
.list-move {
    transition: transform 0.5s ease;
}

.component-row {
    min-height: 1.7rem;
    border-radius: 4px;

    .quantity {
        min-width: 2rem;
        text-align: right;
        margin-right: 0.5rem;
        flex-shrink: 0;
        font-weight: 500;
    }

    .label {
        min-width: 12rem;
    }

    &:hover {
        background-color: rgba(222, 222, 255, 0.03);
    }
}

.components-section--label {
    font-size: 1rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    opacity: 0.5;
    margin-bottom: 0.25rem;
}

.empty-subcategory-label {
    font-size: 0.85rem;
    opacity: 0.6;
    margin-left: 1rem;
}

.requirement-section {
    margin-bottom: 2rem;
    padding: 1rem;
    background: var(--theme-panel-gradient);
    border: 1px solid var(--theme-border);
    border-radius: 10px;
}

.requirement-section__header {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--theme-border);
}

.requirement-section__item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1 1 20rem;
    min-width: 0;
}

.requirement-section__details {
    flex: 1 1 auto;
    min-width: 0;
}

.requirement-section__quantity-input {
    display: flex;
    align-items: center;
    flex: 0 0 auto;
    
    :deep(.n-input-number) {
        width: 7rem;
    }
}

.requirement-section__quantity {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--theme-text);
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
    min-width: 3rem;
    text-align: right;
}

.requirement-section__icon {
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
    border: 2px solid var(--theme-border);
}

.requirement-section__label {
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.01em;
    color: var(--theme-text);
}

.requirement-section__stations {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.requirement-section__stations-label {
    font-size: 0.75rem;
    font-weight: 600;
    font-family: var(--font-display);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--theme-text-dim);
}

.requirement-section__stations-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
}

.crafting-station {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.75rem;
    background: linear-gradient(135deg, rgba(124, 182, 255, 0.2) 0%, rgba(64, 106, 166, 0.26) 100%);
    border: 1px solid var(--theme-border-strong);
    border-radius: 6px;
    transition: all 0.2s ease;

    &:hover {
        background: linear-gradient(135deg, rgba(140, 193, 255, 0.28) 0%, rgba(71, 118, 184, 0.32) 100%);
        border-color: var(--theme-accent);
        transform: translateY(-1px);
    }
}

.crafting-station__icon {
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
}

.crafting-station__label {
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.015em;
    color: var(--theme-text);
}

.requirement-section__ingredients {
    margin-top: 1rem;
}

.requirement-section__ingredients-label {
    font-size: 0.85rem;
    font-weight: 600;
    font-family: var(--font-display);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--theme-text-dim);
    margin-bottom: 0.75rem;
}

.reverse-lookup {
    margin-top: 2rem;
}

.reverse-lookup__title {
    margin-bottom: 1rem;
}

.reverse-lookup__list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 0.75rem;
}

.reverse-lookup-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: linear-gradient(135deg, rgba(40, 45, 70, 0.4) 0%, rgba(30, 35, 55, 0.4) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    transition: all 0.2s ease;
    cursor: pointer;

    &:hover {
        border-color: rgba(255, 255, 255, 0.15);
        background: linear-gradient(135deg, rgba(45, 50, 80, 0.5) 0%, rgba(35, 40, 65, 0.5) 100%);
        transform: translateX(2px);
    }
}

.reverse-lookup-item__icon {
    flex: 0 0 auto;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
    border: 2px solid rgba(255, 255, 255, 0.1);
}

.reverse-lookup-item__label {
    flex: 1;
    font-weight: 600;
    font-size: 1rem;
    color: rgba(255, 255, 255, 0.95);
}
</style>
