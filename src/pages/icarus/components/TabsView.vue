<template>
    <div>
        <n-spin :show="isLoadingRecipes">
            <n-card class="overflow-hidden" content-style="padding: 1rem;">
                <div v-if="tabs.length === 0" class="empty-tabs-state">
                    <p class="mb-2">No tabs open.</p>
                    <p class="text-muted mb-0">Select an item to open it in a new tab.</p>
                </div>
                <n-tabs v-else ref="tabsInstRef" v-model:value="activeTabId" type="bar" :closable="closable" tab-style="">
                    <!-- `name` acts as ID here -->
                    <n-tab-pane v-for="tab in tabs" :tab="tab.title" :name="tab.id" :key="tab.id">
                        <crafting-calculator :tab="tab" @close-tab="removeTab({ tabId: $event })"></crafting-calculator>
                    </n-tab-pane>
                    <!-- <template #prefix>Prefix</template>
                    <template #suffix>Suffix</template> -->
                </n-tabs>
            </n-card>
        </n-spin>
    </div>
</template>

<script>
import { mapActions, mapState } from 'pinia';
import { useIcarusStore } from '@/store/icarus';

import ManageTab from '@/pages/icarus/components/ManageTab.vue';
import CraftingCalculator from '@/pages/icarus/components/craftingCalculator/CraftingCalculator.vue';

const icarusStore = useIcarusStore();

export default {
    name: 'CraftingToolTabView',
    components: {
        ManageTab,
        CraftingCalculator,
    },
    props: {
        workspaceMode: {
            type: String,
            required: true,
        },
    },
    data() {
        return {
            activeTabId: icarusStore.workspaceState.workspaces[this.workspaceMode]?.activeTabId ?? null,
            closable: true,
        };
    },
    watch: {
        activeTabId: function (newValue) {
            this.setActiveTab(newValue, this.workspaceMode);
        },
        storeActiveTabId(newValue) {
            if (this.activeTabId !== newValue) {
                this.activeTabId = newValue;
                this.syncTabBarPosition();
            }
        },
    },
    computed: {
        ...mapState(useIcarusStore, ['isLoadingRecipes']),
        workspace() {
            return icarusStore.workspaceState.workspaces[this.workspaceMode];
        },
        tabs() {
            return this.workspace?.tabs ?? [];
        },
        storeActiveTabId() {
            return this.workspace?.activeTabId ?? null;
        },
    },
    methods: {
        ...mapActions(useIcarusStore, ['setActiveTab']),
        handleAdd() {},
        handleClose() {},
        removeTab({ tabId } = {}) {
            // update store
            icarusStore.removeTab(tabId, this.workspaceMode);
            this.syncSelectedTab();
        },
        syncSelectedTab() {
            // update component from store
            this.activeTabId = this.workspace?.activeTabId ?? null;
            this.syncTabBarPosition();
        },
        syncTabBarPosition() {
            // fix tab underline position (recommended approach from library docs)
            this.$nextTick(() => {
                this.$refs.tabsInstRef?.syncBarPosition();
            });
        }
    },
};
</script>

<style scoped lang="scss">
.empty-tabs-state {
    padding: 1rem 0.5rem;
    text-align: center;
    color: var(--theme-text-dim);

    p:first-child {
        font-family: var(--font-display);
        font-size: 1.05rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
        color: var(--theme-text);
    }

    p:last-child {
        font-size: 0.9rem;
        letter-spacing: 0.01em;
    }
}
</style>
