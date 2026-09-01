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
                    <div class="brand-copy px-2">
                        <span class="brand-name">PROSPECTOR</span>
                        <span class="brand-expansion">Planetary Resource Order &amp; Surface Prep Engine for Crafting, Tallying, Output &amp; Requisitions</span>
                    </div>
                </div>
                <div class="header-actions flex align-items-center ml-auto px-2">
                    <n-tooltip>
                        <template #trigger>
                            <n-button
                                tag="a"
                                quaternary
                                circle
                                href="https://github.com/FriedCheese2006/friedcheese2006.github.io"
                                target="_blank"
                                rel="noopener noreferrer"
                                aria-label="View PROSPECTOR on GitHub"
                            >
                                <template #icon>
                                    <n-icon><Github /></n-icon>
                                </template>
                            </n-button>
                        </template>
                        View source on GitHub
                    </n-tooltip>
                    <n-tooltip>
                        <template #trigger>
                            <n-button quaternary circle aria-label="About PROSPECTOR" @click="showAbout = true">
                                <template #icon>
                                    <n-icon><InfoCircle /></n-icon>
                                </template>
                            </n-button>
                        </template>
                        About PROSPECTOR
                    </n-tooltip>
                    <div v-if="ssoEnabled" class="auth-section flex align-items-center ml-2">
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
        </div>
        <n-modal v-model:show="showAbout" preset="card" title="About PROSPECTOR" class="about-modal">
            <p class="about-expansion">Planetary Resource Order &amp; Surface Prep Engine for Crafting, Tallying, Output &amp; Requisitions</p>
            <p>An ICARUS crafting planner for building item and food plans, comparing recipes, and tracking requirements.</p>
            <p>
                Based on
                <a href="https://github.com/Drumstix42/drumstix42.github.io" target="_blank" rel="noopener noreferrer">Drumstix42's Icarus Calculator</a>,
                including its game-file export workflow. Licensed under Apache 2.0.
            </p>
            <p class="about-disclaimer">
                This unofficial fan project is not affiliated with, endorsed by, or sponsored by ICARUS, RocketWerkz, or any of their subsidiaries.
                Game names, data, imagery, and related marks remain the property of their respective owners.
            </p>
        </n-modal>
    </header>
</template>

<script>
import { Github, InfoCircle } from '@vicons/fa';
import { GAME_ASSETS_URL } from '@/constants/common';
import { useAuth } from '@/composables/useAuth';

export default {
    name: 'Header',
    components: { Github, InfoCircle },
    props: [],
    setup() {
        const { user, isLoggedIn, ssoEnabled, login, logout } = useAuth();
        return { user, isLoggedIn, ssoEnabled, login, logout };
    },
    data() {
        return {
            gameAssetsUrl: GAME_ASSETS_URL,
            resizeObserver: null,
            showAbout: false,
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
            min-width: 0;
            font-family: var(--font-display);
            font-weight: 700;
            text-transform: uppercase;
            color: var(--theme-text);
        }

        .brand-copy {
            display: flex;
            min-width: 0;
            flex-direction: column;
        }

        .brand-name {
            font-size: 1.08rem;
            letter-spacing: 0.035em;
        }

        .brand-expansion {
            max-width: 44rem;
            font-family: var(--font-body);
            font-size: 0.65rem;
            font-weight: 500;
            line-height: 1.2;
            text-transform: none;
            color: var(--theme-text-dim);
        }

        .user-name {
            font-family: var(--font-body);
            font-size: 0.86rem;
            color: var(--theme-text-dim);
        }
    }
}

.about-modal {
    width: min(36rem, calc(100vw - 2rem));

    .about-expansion {
        font-family: var(--font-display);
        font-weight: 700;
    }

    a {
        color: var(--primary-color);
    }

    .about-disclaimer {
        color: var(--theme-text-dim);
        font-size: 0.85rem;
    }
}

@media (max-width: 42rem) {
    .navbar .inner .brand-expansion {
        font-size: 0.58rem;
    }
}
</style>
