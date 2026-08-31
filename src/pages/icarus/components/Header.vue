<template>
    <header class="header">
        <div class="navbar">
            <div class="inner px-2 flex justify-content-between align-items-center">
                <div class="mx-2 title flex align-items-center">
                    <n-image
                        class="icon"
                        width="24"
                        :src="`${gameAssetsUrl}/ItemIcons/Tools/ITEM_Building_RepairTool.png`"
                        :preview-disabled="true"
                    />
                    <span class="px-2">Icarus Crafting Calculator</span>
                </div>
                <div v-if="ssoEnabled" class="auth-section flex align-items-center ml-auto px-2">
                    <template v-if="isLoggedIn">
                        <span class="user-name mr-2">{{ user.name || user.email }}</span>
                        <n-button size="small" @click="logout">Sign out</n-button>
                    </template>
                    <template v-else>
                        <n-button size="small" type="primary" @click="login">Sign in</n-button>
                    </template>
                </div>
            </div>
        </div>
    </header>
</template>

<script>
import { GAME_ASSETS_URL } from '@/constants/common';
import { useAuth } from '@/composables/useAuth';

export default {
    name: 'Header',
    components: {},
    props: [],
    setup() {
        const { user, isLoggedIn, ssoEnabled, login, logout } = useAuth();
        return { user, isLoggedIn, ssoEnabled, login, logout };
    },
    data() {
        return {
            gameAssetsUrl: GAME_ASSETS_URL,
            resizeObserver: null,
        };
    },
    mounted() {
        this.syncHeaderHeight();
        window.addEventListener('resize', this.syncHeaderHeight);

        this.resizeObserver = new ResizeObserver(() => {
            this.syncHeaderHeight();
        });
        this.resizeObserver.observe(this.$el);
    },
    beforeUnmount() {
        window.removeEventListener('resize', this.syncHeaderHeight);
        this.resizeObserver?.disconnect();
    },
    methods: {
        syncHeaderHeight() {
            const headerHeight = this.$el?.offsetHeight || 0;
            document.documentElement.style.setProperty('--app-header-height', `${headerHeight}px`);
        },
    },
};
</script>

<style lang="scss">
.header {
    position: sticky;
    top: 0;
    z-index: 999;
}

.navbar {
    padding: 0.25rem;
    background-color: var(--navbar-bg-color);
    border-bottom: 1px solid var(--navbar-border-color);

    .inner {
        margin: 0 auto;
        max-width: 100rem;

        .title {
            min-height: 2rem;
            font-family: var(--font-display);
            font-weight: 700;
            font-size: 1.08rem;
            letter-spacing: 0.035em;
            text-transform: uppercase;
            color: var(--theme-text);
        }

        .user-name {
            font-family: var(--font-body);
            font-size: 0.86rem;
            color: var(--theme-text-dim);
        }
    }
}
</style>
