<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useItemsQuery, type ItemFilters } from '../../api/items'
import { useConditionsQuery, usePurposesQuery, useClimatesQuery } from '../../api/referenceData'
import CatalogFilters from './CatalogFilters.vue'

const props = withDefaults(defineProps<{ modelValue: ItemFilters; fixedCategory?: boolean; title?: string }>(), { title: 'Вещи' })
const emit = defineEmits<{ 'update:modelValue': [filters: ItemFilters] }>()
const selected = computed({ get: () => props.modelValue, set: (value: ItemFilters) => emit('update:modelValue', value) })
const filtered = computed(() => Object.entries(props.modelValue).some(([key, value]) =>
  value !== undefined && value !== null && !(props.fixedCategory && key === 'category_id')))
const items = useItemsQuery(() => props.modelValue)
const conditions = useConditionsQuery()
const purposes = usePurposesQuery()
const climates = useClimatesQuery()
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
  <section :aria-label="fixedCategory ? 'Вещи категории' : 'Все вещи'">
    <h2>{{ title }}</h2>
    <CatalogFilters v-model="selected" :fixed-category="fixedCategory" />
    <p v-if="listError" role="alert">Не удалось загрузить каталог.</p>
    <p v-else-if="listPending" role="status">Загрузка каталога…</p>
    <template v-else-if="!items.data.value?.length">
      <p v-if="filtered">По выбранным фильтрам ничего не найдено.</p>
      <p v-else>{{ fixedCategory ? 'В этой категории пока нет вещей.' : 'В каталоге пока нет вещей.' }}</p>
    </template>
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
