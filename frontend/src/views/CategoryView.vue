<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useCategoriesQuery } from '../api/categories'
import type { ItemFilters } from '../api/items'
import CatalogItemList from '../features/catalog/CatalogItemList.vue'
import { findCategoryPath, parseCategoryId } from '../features/catalog/categoryTree'

const route = useRoute()
const categoryId = computed(() => parseCategoryId(route.params.categoryId))
const categories = useCategoriesQuery(() => categoryId.value !== undefined)
const path = computed(() => categoryId.value === undefined ? undefined
  : findCategoryPath(categories.data.value ?? [], categoryId.value))
const category = computed(() => path.value?.at(-1))
const filters = ref<ItemFilters>({})
const itemFilters = computed(() => ({ ...filters.value, category_id: categoryId.value }))
</script>

<template>
  <section class="catalog-category">
    <template v-if="categoryId === undefined">
      <h1>Категория не найдена</h1>
      <RouterLink to="/catalog">Вернуться в каталог</RouterLink>
    </template>
    <template v-else-if="categories.isError.value">
      <h1>Каталог</h1>
      <p role="alert">Не удалось загрузить каталог.</p>
    </template>
    <template v-else-if="categories.isPending.value">
      <h1>Каталог</h1>
      <p role="status">Загрузка каталога…</p>
    </template>
    <template v-else-if="!category">
      <h1>Категория не найдена</h1>
      <RouterLink to="/catalog">Вернуться в каталог</RouterLink>
    </template>
    <template v-else>
      <nav aria-label="Путь категории" class="catalog-breadcrumb">
        <ol>
          <li><RouterLink to="/catalog">Каталог</RouterLink></li>
          <li v-for="entry in path" :key="entry.id">
            <span v-if="entry.id === category.id" aria-current="page">{{ entry.name }}</span>
            <RouterLink v-else :to="`/catalog/categories/${entry.id}`">{{ entry.name }}</RouterLink>
          </li>
        </ol>
      </nav>
      <h1>{{ category.name }}</h1>
      <div class="item-actions">
        <RouterLink :to="`/catalog/categories/new?parent_id=${category.id}`">Добавить подкатегорию</RouterLink>
        <RouterLink :to="`/catalog/categories/${category.id}/edit`">Редактировать категорию</RouterLink>
      </div>
      <div class="item-actions"><RouterLink :to="`/catalog/items/new?category_id=${category.id}`">Добавить вещь</RouterLink></div>
      <section v-if="category.children?.length" aria-label="Подкатегории">
        <h2>Подкатегории</h2>
        <ul class="category-links">
          <li v-for="child in category.children" :key="child.id">
            <RouterLink :to="`/catalog/categories/${child.id}`">{{ child.name }}</RouterLink>
          </li>
        </ul>
      </section>
      <CatalogItemList :model-value="itemFilters" fixed-category @update:model-value="filters = $event" />
    </template>
  </section>
</template>
