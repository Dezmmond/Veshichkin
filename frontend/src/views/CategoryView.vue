<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useCategoriesQuery } from '../api/categories'
import { useItemsQuery } from '../api/items'
import { useConditionsQuery, usePurposesQuery, useClimatesQuery } from '../api/referenceData'
import { findCategoryPath, parseCategoryId } from '../features/catalog/categoryTree'

const route = useRoute()
const categoryId = computed(() => parseCategoryId(route.params.categoryId))
const categories = useCategoriesQuery(() => categoryId.value !== undefined)
const path = computed(() => categoryId.value === undefined ? undefined
  : findCategoryPath(categories.data.value ?? [], categoryId.value))
const category = computed(() => path.value?.at(-1))
const enabled = computed(() => !!category.value)
const items = useItemsQuery(() => ({ category_id: categoryId.value }), enabled)
const conditions = useConditionsQuery(enabled)
const purposes = usePurposesQuery(enabled)
const climates = useClimatesQuery(enabled)
const listQueries = [items, conditions, purposes, climates]
const listError = computed(() => listQueries.some((query) => query.isError.value))
const listPending = computed(() => listQueries.some((query) => query.isPending.value))
const conditionNames = computed(() => new Map(conditions.data.value?.map((row) => [row.id, row.name])))
const purposeNames = computed(() => new Map(purposes.data.value?.map((row) => [row.id, row.name])))
const climateNames = computed(() => new Map(climates.data.value?.map((row) => [row.id, row.name])))
const trackingNames = { individual: 'Индивидуальная', grouped: 'Группа' }
function names(ids: number[] | undefined, lookup: Map<number, string>) {
  return ids?.length ? ids.map((id) => lookup.get(id) ?? 'Неизвестное значение').join(', ') : 'Не указаны'
}
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
      <div class="item-actions"><RouterLink :to="`/catalog/items/new?category_id=${category.id}`">Добавить вещь</RouterLink></div>
      <section v-if="category.children?.length" aria-label="Подкатегории">
        <h2>Подкатегории</h2>
        <ul class="category-links">
          <li v-for="child in category.children" :key="child.id">
            <RouterLink :to="`/catalog/categories/${child.id}`">{{ child.name }}</RouterLink>
          </li>
        </ul>
      </section>
      <section aria-label="Вещи категории">
        <h2>Вещи</h2>
        <p v-if="listError" role="alert">Не удалось загрузить каталог.</p>
        <p v-else-if="listPending" role="status">Загрузка каталога…</p>
        <p v-else-if="!items.data.value?.length">В этой категории пока нет вещей.</p>
        <ul v-else class="catalog-items">
          <li v-for="item in items.data.value" :key="item.id" class="catalog-item">
            <h3><RouterLink :to="`/catalog/items/${item.id}`">{{ item.name }}</RouterLink></h3>
            <dl>
              <div><dt>Учёт</dt><dd>{{ trackingNames[item.tracking_mode] }}</dd></div>
              <div><dt>Количество</dt><dd>{{ item.quantity }}</dd></div>
              <div><dt>Состояние</dt><dd>{{ item.condition_id === null ? 'Не указано' : conditionNames.get(item.condition_id) ?? 'Неизвестное значение' }}</dd></div>
              <div><dt>Назначения</dt><dd>{{ names(item.purpose_ids, purposeNames) }}</dd></div>
              <div><dt>Климат</dt><dd>{{ names(item.climate_ids, climateNames) }}</dd></div>
              <div v-if="item.brand"><dt>Бренд</dt><dd>{{ item.brand }}</dd></div>
              <div v-if="item.model"><dt>Модель</dt><dd>{{ item.model }}</dd></div>
              <div v-if="item.color"><dt>Цвет</dt><dd>{{ item.color }}</dd></div>
              <div v-if="item.size"><dt>Размер</dt><dd>{{ item.size }}</dd></div>
              <div v-if="item.material"><dt>Материал</dt><dd>{{ item.material }}</dd></div>
            </dl>
          </li>
        </ul>
      </section>
    </template>
  </section>
</template>
