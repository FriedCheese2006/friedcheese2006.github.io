<template>
    <div class="ingredient-card" :class="{ 'completed': node.completed }">
        <div class="ingredient-card__main">
            <div class="ingredient-card__expand-icon" v-if="hasExpandableContent" @click.stop="toggleExpand">
                <n-icon size="16" :class="{ 'rotated': isExpanded }">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                    </svg>
                </n-icon>
            </div>
            <div class="ingredient-card__content" @click="toggleExpand">
                <div class="ingredient-card__identity">
                    <div class="ingredient-card__quantity">{{ formatQuantity(node.quantity, node.quantityUnit) }}</div>
                    <n-image
                        class="ingredient-card__icon"
                        width="40"
                        height="40"
                        :src="node.imagePath"
                        :fallback-src="`${gameAssetsUrl}/Images/question-mark.png`"
                        :preview-disabled="true"
                    />
                    <div class="ingredient-card__info">
                        <div class="ingredient-card__label">{{ node.label ?? node.id }}</div>
                        <recipe-selector
                            v-if="hasRecipeAlternatives"
                            :catalog="catalog"
                            :item-id="node.id"
                            :selected-recipe-id="node.recipeId"
                            @change="$emit('recipe-change', { itemId: node.id, recipeId: $event })"
                        />
                        <div v-if="node.isRaw" class="ingredient-card__badge">Raw Material</div>
                    </div>
                </div>
                <div v-if="!node.isRaw && craftingStations.length > 0" class="ingredient-card__stations">
                    <div class="ingredient-card__stations-label">Crafted at:</div>
                    <div class="ingredient-card__stations-list">
                        <n-tooltip v-for="station in craftingStations" :key="station.id" placement="top">
                            <template #trigger>
                                <n-image
                                    class="ingredient-card__station-icon"
                                    width="24"
                                    height="24"
                                    :src="station.imagePath"
                                    :fallback-src="`${gameAssetsUrl}/Images/question-mark.png`"
                                    :preview-disabled="true"
                                />
                            </template>
                            {{ station.label }}
                        </n-tooltip>
                    </div>
                </div>
            </div>
            <div class="ingredient-card__complete-btn" @click.stop="toggleComplete">
                <n-icon size="20" :class="{ 'checked': node.completed }">
                    <svg v-if="node.completed" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/>
                    </svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                    </svg>
                </n-icon>
            </div>
        </div>

        <div v-if="hasExpandableContent && isExpanded" class="ingredient-card__children">
            <requirement-tree-node
                v-for="child in expandedChildren"
                :key="child.nodeKey ?? `${node.id}-${child.id}-${child.quantity}`"
                :node="child"
                :depth="depth + 1"
                :catalog="catalog"
                :recipe-overrides="recipeOverrides"
                :game-assets-url="gameAssetsUrl"
                @toggle-complete="$emit('toggle-complete', $event)"
                @recipe-change="$emit('recipe-change', $event)"
            ></requirement-tree-node>
        </div>
    </div>
</template>

<script>
import RecipeSelector from './RecipeSelector.vue';
import { getRecipeIdsForItem } from '@/utility/recipeCatalog';

export default {
    name: 'RequirementTreeNode',
    components: {
        RecipeSelector,
    },
    props: {
        node: {
            type: Object,
            required: true,
        },
        depth: {
            type: Number,
            default: 0,
        },
        catalog: {
            type: Object,
            required: true,
        },
        recipeOverrides: {
            type: Object,
            default: () => ({}),
        },
        gameAssetsUrl: {
            type: String,
            required: true,
        },
    },
    emits: ['toggle-complete', 'recipe-change'],
    data() {
        return {
            isExpanded: false,
        };
    },
    computed: {
        hasExpandableContent() {
            return this.node.children?.length > 0;
        },
        expandedChildren() {
            return this.node.children || [];
        },
        hasRecipeAlternatives() {
            return getRecipeIdsForItem(this.catalog, this.node.id).length > 1;
        },
        craftingStations() {
            return (this.node.recipeSetIds ?? []).map((recipeSetId) => this.catalog.recipeSetsById[recipeSetId]).filter(Boolean);
        },
    },
    methods: {
        formatQuantity(value, unit) {
            const quantity = unit ? Math.round(value * 1000) / 1000 : Math.ceil(value);
            return unit ? `${quantity} ${unit}` : quantity;
        },
        toggleExpand(event) {
            if (this.hasExpandableContent) {
                this.isExpanded = !this.isExpanded;
            }
        },
        toggleComplete() {
            const childNodeKeys = this.collectChildNodeKeys(this.node);
            this.$emit('toggle-complete', {
                nodeKey: this.node.nodeKey,
                completed: !this.node.completed,
                childNodeKeys,
            });
        },
        collectChildNodeKeys(node) {
            const nodeKeys = [];
            
            const children = node.children || [];
            children.forEach(child => {
                if (child.nodeKey) {
                    nodeKeys.push(child.nodeKey);
                }
                if (child.children) {
                    nodeKeys.push(...this.collectChildNodeKeys(child));
                }
            });
            
            return nodeKeys;
        },
    },
};
</script>

<style scoped lang="scss">
.ingredient-card {
    margin-bottom: 0.5rem;
    background: linear-gradient(145deg, rgba(32, 45, 67, 0.62) 0%, rgba(17, 28, 43, 0.88) 100%);
    border: 1px solid var(--theme-border);
    border-radius: 8px;
    overflow: hidden;
    transition: all 0.2s ease;

    &:hover {
        border-color: var(--theme-border-strong);
        background: linear-gradient(145deg, rgba(36, 52, 78, 0.72) 0%, rgba(21, 35, 52, 0.92) 100%);
        transform: translateX(2px);
    }

    &.completed {
        opacity: 0.5;
        
        .ingredient-card__label {
            text-decoration: line-through;
            opacity: 0.7;
        }
        
        .ingredient-card__icon {
            opacity: 0.6;
        }
    }
}

.ingredient-card__main {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    position: relative;
}

.ingredient-card__content {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.75rem;
    flex: 1;
    min-width: 0;
    cursor: pointer;
    border-radius: 4px;
    padding: 0.25rem;
    margin: -0.25rem;
    transition: background 0.2s ease;

    &:hover {
        background: rgba(151, 196, 255, 0.08);
    }
}

.ingredient-card__identity {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex: 1 1 20rem;
    min-width: 0;
}

.ingredient-card__expand-icon {
    flex: 0 0 auto;
    color: var(--theme-text-dim);
    display: flex;
    align-items: center;
    cursor: pointer;
    transition: color 0.2s ease;

    .n-icon {
        transition: transform 0.25s ease;

        &.rotated {
            transform: rotate(90deg);
        }
    }

    &:hover {
        color: var(--theme-accent-strong);
    }
}

.ingredient-card__quantity {
    flex: 0 0 auto;
    min-width: 3rem;
    text-align: right;
    font-weight: 700;
    font-size: 1.1rem;
    color: var(--theme-text);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
}

.ingredient-card__icon {
    flex: 0 0 auto;
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    border: 1px solid var(--theme-border);
}

.ingredient-card__info {
    flex: 1;
    min-width: 0;
}

.ingredient-card__label {
    font-weight: 600;
    font-size: 0.95rem;
    line-height: 1.3;
    color: var(--theme-text);
    margin-bottom: 0.15rem;
    transition: all 0.2s ease;
}

.ingredient-card__badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 12px;
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    background: linear-gradient(135deg, rgba(116, 209, 154, 0.22) 0%, rgba(69, 165, 115, 0.22) 100%);
    color: rgba(191, 245, 213, 0.95);
    border: 1px solid rgba(116, 209, 154, 0.42);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.ingredient-card__stations {
    display: flex;
    flex: 1 1 14rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 0.35rem;
    min-width: 0;
}

.ingredient-card__stations-label {
    font-size: 0.7rem;
    color: var(--theme-text-dim);
    font-weight: 600;
    font-family: var(--font-display);
    text-transform: uppercase;
    letter-spacing: 0.07em;
}

.ingredient-card__stations-list {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    width: 100%;
}

.ingredient-card__station-icon {
    flex: 0 0 auto;
    border-radius: 4px;
    border: 1px solid var(--theme-border);
}

.ingredient-card__complete-btn {
    flex: 0 0 auto;
    cursor: pointer;
    padding: 0.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(189, 206, 228, 0.45);
    transition: all 0.2s ease;
    border-radius: 4px;

    &:hover {
        color: var(--theme-accent-strong);
        background: rgba(124, 182, 255, 0.12);
    }

    .n-icon.checked {
        color: var(--theme-success);
    }
}

.ingredient-card__children {
    padding: 0.5rem 0.5rem 0.5rem 2rem;
    position: relative;

    &::before {
        content: '';
        position: absolute;
        left: 1.5rem;
        top: 0;
        bottom: 0.5rem;
        width: 2px;
        background: linear-gradient(180deg, rgba(145, 178, 220, 0.28) 0%, transparent 100%);
    }
}
</style>