<template>
    <n-select
        class="recipe-selector"
        size="small"
        :value="selectedRecipeId"
        :options="options"
        @click.stop
        @update:value="$emit('change', $event)"
    />
</template>

<script>
import { getItemLabel, getRecipeIdsForItem, getRecipeLabel } from '@/utility/recipeCatalog';

export default {
    name: 'CraftingRecipeSelector',
    props: {
        catalog: {
            type: Object,
            required: true,
        },
        itemId: {
            type: String,
            required: true,
        },
        selectedRecipeId: {
            type: String,
            default: null,
        },
    },
    emits: ['change'],
    computed: {
        options() {
            return getRecipeIdsForItem(this.catalog, this.itemId).map((recipeId) => {
                const recipe = this.catalog.recipesById[recipeId];
                const inputSummary = recipe.inputs
                    .map((input) => {
                        const unit = input.quantityUnit ?? this.catalog.itemsById[input.itemId]?.quantityUnit ?? '';
                        return `${input.quantity}${unit ? ` ${unit}` : ''} ${getItemLabel(this.catalog, input.itemId)}`;
                    })
                    .join(' + ');
                return {
                    label: inputSummary || getRecipeLabel(this.catalog, recipeId),
                    value: recipeId,
                };
            });
        },
    },
};
</script>

<style scoped>
.recipe-selector {
    width: min(28rem, 100%);
    margin-top: 0.35rem;
}
</style>