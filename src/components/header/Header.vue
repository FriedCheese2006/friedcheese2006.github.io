<template>
    <header>
        <div class="navbar">
            <div class="inner">
                <router-link custom v-for="item in routeItems" :to="item.path" v-slot="{ href, route, navigate, isActive, isExactActive }">
                    <n-button quaternary size="large" :type="isActive || isExactActive ? 'info' : 'default'" :href="href" @click="navigate">
                        {{ item.title }}
                    </n-button>
                </router-link>
            </div>
        </div>
    </header>
</template>

<script>
export default {
    name: 'Header',
    components: {},
    props: [],
    data() {
        return {};
    },
    computed: {
        routeItems() {
            const items = [];
            const routes = this.$router.options.routes || [];

            // build array of Routes that contain a "title"
            routes.forEach((record) => {
                if (record.title) {
                    items.push(record);
                }
            });

            return items;
        },
    },
};
</script>

<style lang="scss">
.navbar {
    padding: 0.5rem;
    background: linear-gradient(135deg, rgba(25, 30, 45, 0.95) 0%, rgba(18, 22, 35, 0.95) 100%);
    border-bottom: 1px solid rgba(100, 150, 255, 0.2);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);

    .inner {
        margin: 0 auto;
        max-width: 100rem;
    }
}
</style>
