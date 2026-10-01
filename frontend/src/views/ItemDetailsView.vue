<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useItemQuery } from '../api/items'
import { useCategoriesQuery } from '../api/categories'
import { useConditionsQuery, usePurposesQuery, useClimatesQuery } from '../api/referenceData'
import { findCategoryById, parseCategoryId } from '../features/catalog/categoryTree'

const route = useRoute()
const id = computed(() => parseCategoryId(route.params.itemId))
const query = useItemQuery(id)
const item = query.data
const enabled = computed(() => !!item.value)
const categories = useCategoriesQuery(enabled)
const conditions = useConditionsQuery(enabled)
const purposes = usePurposesQuery(enabled)
const climates = useClimatesQuery(enabled)
const references = [categories, conditions, purposes, climates]
const error = computed(() => query.isError.value || references.some((q) => q.isError.value))
const loading = computed(() => query.isPending.value || references.some((q) => q.isPending.value))
const category = computed(() => item.value ? findCategoryById(categories.data.value ?? [], item.value.category_id) : undefined)
const condition = computed(() => conditions.data.value?.find((row) => row.id === item.value?.condition_id)?.name ?? 'Не указано')
const purposeNames = computed(() => new Map(purposes.data.value?.map((row) => [row.id, row.name])))
const climateNames = computed(() => new Map(climates.data.value?.map((row) => [row.id, row.name])))
function names(ids: number[] | undefined, lookup: Map<number, string>) {
  return ids?.length ? ids.map((id) => lookup.get(id) ?? 'Неизвестное значение').join(', ') : 'Не указаны'
}
const optionalFields = [ ['brand', 'Бренд'], ['model', 'Модель'], ['color', 'Цвет'],
  ['size', 'Размер'], ['material', 'Материал'], ['notes', 'Заметки'] ] as const
</script>

<template>
  <section class="item-details">
    <template v-if="id === undefined || item === null">
      <h1>Вещь не найдена</h1><RouterLink to="/catalog">Вернуться в каталог</RouterLink>
    </template>
    <template v-else-if="error"><h1>Вещь</h1><p role="alert">Не удалось загрузить вещь.</p></template>
    <template v-else-if="loading"><h1>Вещь</h1><p role="status">Загрузка вещи…</p></template>
    <template v-else-if="item">
      <h1>{{ item.name }}</h1>
      <p v-if="!item.is_active" role="status">Не в текущем каталоге</p>
      <dl>
        <dt>Категория</dt><dd><RouterLink v-if="category" :to="`/catalog/categories/${category.id}`">{{ category.name }}</RouterLink><span v-else>Категория недоступна</span></dd>
        <dt>Учёт</dt><dd>{{ item.tracking_mode === 'individual' ? 'Индивидуальная вещь' : 'Группа одинаковых вещей' }}</dd>
        <template v-if="item.tracking_mode === 'grouped'"><dt>Количество</dt><dd>{{ item.quantity }}</dd></template>
        <dt>Состояние</dt><dd>{{ condition }}</dd>
        <dt>Назначения</dt><dd>{{ names(item.purpose_ids, purposeNames) }}</dd>
        <dt>Климат</dt><dd>{{ names(item.climate_ids, climateNames) }}</dd>
        <template v-for="[key, label] in optionalFields" :key="key">
          <template v-if="item[key]"><dt>{{ label }}</dt><dd class="item-text">{{ item[key] }}</dd></template>
        </template>
        <dt>Дополнительные свойства</dt><dd><pre>{{ JSON.stringify(item.extra_attributes, null, 2) }}</pre></dd>
      </dl>
      <div class="item-actions">
        <RouterLink :to="`/catalog/items/${item.id}/edit`">Редактировать</RouterLink>
        <RouterLink to="/catalog">Вернуться в каталог</RouterLink>
      </div>
    </template>
  </section>
</template>
