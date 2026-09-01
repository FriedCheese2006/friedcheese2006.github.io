<template>
    <div>
        <n-tabs class="workspace-tabs" :value="workspaceMode" type="segment" @update:value="onWorkspaceChange">
            <n-tab-pane name="items">
                <template #tab>Items</template>
            </n-tab-pane>
            <n-tab-pane name="food">
                <template #tab>Food</template>
            </n-tab-pane>
        </n-tabs>
        <div class="mb-3 flex align-items-center">
            <n-input type="text" v-model:value="searchValue" placeholder="Search..." clearable @input="onSearch" />
            <div class="flex-shrink-0 ml-3">
                <n-tooltip trigger="hover" placement="right">
                    <template #trigger>
                        <n-checkbox v-model:checked="settings.searchFuzzyMatch">Fuzzy search</n-checkbox>
                    </template>
                    Allows partial text matches, sorted by match quality
                </n-tooltip>
            </div>
        </div>
        <n-spin :show="isLoadingRecipes">
            <n-card class="scroll-wrap" content-style="padding: 0;">
                <div v-if="filteredRecipeOptions.length === 0" class="p-3 font-italic">No matching items found.</div>

                <RecycleScroller class="scroller" :items="filteredRecipeOptions" :item-size="40" key-field="id" v-slot="{ index, item }">
                    <div class="recipe-item flex align-items-center" @click="openItemTab(item.id)">
                        <div class="relative flex align-items-center">
                            <n-image
                                class="icon"
                                width="32"
                                :src="item.imagePath"
                                :fallback-src="`${gameAssetsUrl}/Images/question-mark.png`"
                                :preview-disabled="true"
                            />
                            <div v-if="item.outputQuantity > 1" class="item-counter">x{{ item.outputQuantity }}</div>
                        </div>
                        <div class="flex-shrink" style="min-width: 0">
                            <div class="label text-overflow-ellipsis" v-bind:item-id="item.id">
                                <span v-if="item.highlightedLabel" v-html="item.highlightedLabel"></span>
                                <span v-else>{{ item.label }}</span>
                                <span v-if="item.recipeCount > 1" class="recipe-count">{{ item.recipeCount }} recipes</span>
                            </div>
                        </div>
                        <n-tooltip trigger="hover">
                            <template #trigger>
                                <n-button class="hover-button ml-auto" secondary type="default" size="small">
                                    <n-icon size="13">
                                        <Plus></Plus>
                                    </n-icon>
                                </n-button>
                            </template>
                            Open in new tab
                        </n-tooltip>
                    </div>
                </RecycleScroller>
            </n-card>
        </n-spin>
    </div>
</template>

<script>
import debounce from 'debounce';
import { mapActions, mapState } from 'pinia';
import { Plus } from '@vicons/fa';

import { useIcarusStore } from '@/store/icarus';
import { GAME_ASSETS_URL } from '@/constants/common';
const icarusStore = useIcarusStore();

export default {
    name: 'CraftingToolItemSelector',
    components: {
        Plus,
    },
    props: {
        workspaceMode: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            searchValue: icarusStore.workspaceState.workspaces[this.workspaceMode]?.search ?? '',
            gameAssetsUrl: GAME_ASSETS_URL,
        };
    },
    computed: {
        ...mapState(useIcarusStore, ['isLoadingRecipes', 'settings']),
        filteredRecipeOptions() {
            return icarusStore.filteredRecipeOptionsForMode(this.workspaceMode);
        },
        workspaceSearch() {
            return icarusStore.workspaceState.workspaces[this.workspaceMode]?.search ?? '';
        },
    },
    watch: {
        workspaceSearch(value) {
            if (value !== this.searchValue) {
                this.searchValue = value;
            }
        },
    },
    methods: {
        ...mapActions(useIcarusStore, ['openItemTab']),
        onWorkspaceChange(value) {
            icarusStore.setActiveMode(value);
        },
        onSearch: debounce(function (value) {
            icarusStore.setRecipeSearch(this.workspaceMode, value);
        }, 250),
    },
};
</script>

<style scoped lang="scss">
.workspace-tabs {
    margin-bottom: 0.75rem;

    :deep(.n-tabs-rail) {
        padding: 3px;
        background: var(--theme-panel-gradient);
        border: 1px solid var(--theme-border);
        border-radius: 7px;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025);
    }

    :deep(.n-tabs-capsule) {
        box-sizing: border-box;
        background: linear-gradient(145deg, rgba(124, 182, 255, 0.22), rgba(76, 131, 204, 0.13));
        border: 1px solid var(--theme-border-strong);
        border-radius: 5px;
        box-shadow: 0 2px 8px rgba(3, 9, 18, 0.28);
    }

    :deep(.n-tabs-tab) {
        color: var(--theme-text-dim);
        transition: color 0.2s ease;
    }

    :deep(.n-tabs-tab:hover),
    :deep(.n-tabs-tab--active) {
        color: var(--theme-accent-strong);
    }

    :deep(.n-tabs-pane-wrapper) {
        display: none;
    }
}

.scroll-wrap {
    padding: 0;
    height: 30rem;
    background: var(--theme-panel-gradient);
    border: 1px solid var(--theme-border);
    border-radius: 10px;
    overflow: hidden;
}
.scroller {
    height: 30rem;
}

.recipe-item {
    height: 40px;
    padding: 0.4rem 1rem 0.4rem 0.8rem;
    cursor: pointer;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;

    .icon {
        margin-right: 0.75rem;
        border-radius: 6px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
        border: 1px solid var(--theme-border);
    }

    .label {
        font-weight: 600;
        line-height: 1rem;
        color: var(--theme-text);
    }

    .recipe-count {
        margin-left: 0.5rem;
        font-size: 0.72rem;
        font-weight: 500;
        color: var(--theme-text-dim);
    }

    .hover-button {
        visibility: hidden;
        transition: all 0.2s ease;
    }

    .plus {
        font-weight: bold;
        font-size: 16px;
    }

    &:hover {
        background: linear-gradient(90deg, rgba(124, 182, 255, 0.2) 0%, rgba(68, 112, 176, 0.1) 100%);
        border-left-color: var(--theme-accent);
        transform: translateX(2px);

        .label {
            color: #f4f8ff;
        }

        .hover-button {
            visibility: visible;
        }
    }
}
</style>
