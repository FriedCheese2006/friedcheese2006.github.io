<template>
    <div class="calculator-layout">
        <aside class="left-panel">
            <item-search-view class="item-selector" :workspace-mode="workspaceMode"></item-search-view>
        </aside>
        <section class="right-panel">
            <tabs-view class="tab-view" :workspace-mode="workspaceMode"></tabs-view>
        </section>
    </div>
</template>

<script>
import ItemSearchView from '@/pages/icarus/components/craftingCalculator/ItemSearchView.vue';
import TabsView from '@/pages/icarus/components/TabsView.vue';

export default {
    name: 'IcarusWorkspaceView',
    components: {
        ItemSearchView,
        TabsView,
    },
    props: {
        workspaceMode: {
            type: String,
            required: true,
        },
    },
};
</script>