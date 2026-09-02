<template>
    <div class="icarus-wrap p-2 pt-3">
        <keep-alive>
            <workspace-view :key="activeMode" :workspace-mode="activeMode"></workspace-view>
        </keep-alive>
    </div>
</template>

<script>
import { mapState } from 'pinia';

import WorkspaceView from '@/pages/icarus/components/WorkspaceView.vue';
import { useIcarusStore } from '@/store/icarus';

const icarusStore = useIcarusStore();
icarusStore.loadRecipeData();

export default {
    name: 'Icarus',
    components: {
        WorkspaceView,
    },
    props: [],
    computed: {
        ...mapState(useIcarusStore, ['activeMode']),
    },
    methods: {},
};
</script>

<style lang="scss">
.icarus-wrap {
    max-width: 100rem;
    margin: 0 auto;
}

.calculator-layout {
    display: flex;
    align-items: flex-start;
    gap: 1rem;
}

.left-panel {
    position: sticky;
    top: calc(var(--app-header-height, 0px) + 0.5rem);
    align-self: flex-start;
    flex: 0 0 auto;
    max-height: calc(100vh - var(--app-header-height, 0px) - 1rem);
    overflow-y: auto;
}

.right-panel {
    flex: 1 1 auto;
    min-width: 20rem;
    max-height: calc(100vh - var(--app-header-height, 0px) - 1rem);
    overflow-y: auto;
}

.left-panel,
.right-panel,
.scroller {
    scrollbar-color: var(--theme-accent-soft) rgba(139, 168, 208, 0.08);
    scrollbar-width: thin;

    &::-webkit-scrollbar {
        width: 8px;
    }

    &::-webkit-scrollbar-track {
        background: rgba(139, 168, 208, 0.08);
        border-radius: 4px;
    }

    &::-webkit-scrollbar-thumb {
        background: var(--theme-accent-soft);
        border-radius: 4px;

        &:hover {
            background: rgba(124, 182, 255, 0.45);
        }
    }
}

.tab-view {
    margin: 0.5rem 0.5rem 0.5rem 0;
}

.item-selector {
    width: 23rem;
    margin: 0.5rem;
}

@media (max-width: 1100px) {
    .calculator-layout {
        flex-direction: column;
        gap: 0;
    }

    .left-panel,
    .right-panel {
        position: static;
        width: 100%;
        max-height: none;
        overflow: visible;
    }

    .tab-view {
        margin: 0.5rem;
    }

    .item-selector {
        width: auto;
    }
}
</style>
