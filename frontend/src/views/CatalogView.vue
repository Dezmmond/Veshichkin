<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useCategoriesQuery } from '../api/categories'
import { ref } from 'vue'
import type { ItemFilters } from '../api/items'
import CatalogItemList from '../features/catalog/CatalogItemList.vue'

const { data: categories, isPending, isError } = useCategoriesQuery()
const filters = ref<ItemFilters>({})
</script>

<template>
  <section>
    <h1>Каталог</h1>
    <div class="item-actions"><RouterLink to="/catalog/categories/new">Добавить категорию</RouterLink></div>
    <p v-if="isError" role="alert">Не удалось загрузить каталог.</p>
    <p v-else-if="isPending" role="status">Загрузка каталога…</p>
    <p v-else-if="!categories?.length">Категории пока отсутствуют.</p>
    <ul v-else class="category-links" aria-label="Корневые категории">
      <li v-for="category in categories" :key="category.id">
        <RouterLink :to="`/catalog/categories/${category.id}`">{{ category.name }}</RouterLink>
      </li>
    </ul>
    <CatalogItemList v-model="filters" title="Все вещи" />
  </section>
</template>
