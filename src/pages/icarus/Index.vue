<template>
    <n-config-provider :theme="darkTheme" :theme-overrides="themeOverrides">
        <div>
            <Header></Header>
            <Icarus></Icarus>
        </div>
        <n-global-style></n-global-style>
    </n-config-provider>
</template>

<script>
import { defineAsyncComponent } from 'vue';
import { NConfigProvider, NGlobalStyle } from 'naive-ui';
import { darkTheme } from 'naive-ui';

import Header from '@/pages/icarus//components/Header.vue';

// async import so that the Pinia store can be initialized before being referenced (workaround for now)
const Icarus = defineAsyncComponent(() => import('@/pages/icarus/Icarus.vue'));

export default {
    name: 'App',
    components: {
        Icarus: Icarus,
        NConfigProvider,
        NGlobalStyle,
        Header,
    },
    props: {},
    data() {
        return {
            darkTheme,
            themeOverrides: {
                common: {
                    primaryColor: '#7cb6ff',
                    primaryColorHover: '#9bc9ff',
                    primaryColorPressed: '#649ee4',
                    primaryColorSuppl: '#7cb6ff',
                    infoColor: '#7cb6ff',
                    infoColorHover: '#9bc9ff',
                    infoColorPressed: '#649ee4',
                    successColor: '#74d19a',
                    borderColor: '#2f435f',
                    bodyColor: '#0c1119',
                    cardColor: '#121c2c',
                    modalColor: '#121c2c',
                    textColorBase: '#e9f0fb',
                },
                Input: {
                    color: '#132032',
                    colorFocus: '#18273c',
                    border: '#2f435f',
                    borderHover: '#48658d',
                    borderFocus: '#7cb6ff',
                    textColor: '#e9f0fb',
                    placeholderColor: '#8ea4c4',
                },
                Select: {
                    menuBoxShadow: '0 14px 36px rgba(2, 8, 16, 0.55)',
                    peers: {
                        InternalSelection: {
                            color: '#132032',
                            colorActive: '#18273c',
                            border: '1px solid #2f435f',
                            borderHover: '1px solid #48658d',
                            borderActive: '1px solid #7cb6ff',
                            borderFocus: '1px solid #7cb6ff',
                            textColor: '#e9f0fb',
                            arrowColor: '#8ea4c4',
                        },
                        InternalSelectMenu: {
                            color: '#121c2c',
                            borderRadius: '6px',
                            optionTextColor: '#d6e6fb',
                            optionTextColorPressed: '#e9f0fb',
                            optionTextColorActive: '#9bc9ff',
                            optionCheckColor: '#7cb6ff',
                            optionColorPending: 'rgba(124, 182, 255, 0.12)',
                            optionColorActive: 'rgba(124, 182, 255, 0.08)',
                            optionColorActivePending: 'rgba(124, 182, 255, 0.18)',
                        },
                    },
                },
                Card: {
                    color: '#121c2c',
                    borderColor: '#2f435f',
                    titleTextColor: '#e9f0fb',
                    borderRadius: '10px',
                },
                Tabs: {
                    tabTextColorBar: '#a7bfdc',
                    tabTextColorActiveBar: '#d6e6fb',
                    barColor: '#7cb6ff',
                },
            },
        };
    },
    computed: {},
    methods: {},
};
</script>

<style lang="scss"></style>
