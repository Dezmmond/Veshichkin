<script setup lang="ts">
import { computed } from 'vue'
import type { ItemFilters } from '../../api/items'
import { useCategoriesQuery } from '../../api/categories'
import { useConditionsQuery, usePurposesQuery, useClimatesQuery } from '../../api/referenceData'
import { flattenCategories } from './categoryTree'

const props = defineProps<{ modelValue: ItemFilters; fixedCategory?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [filters: ItemFilters] }>()
const categories = useCategoriesQuery(() => !props.fixedCategory)
const conditions = useConditionsQuery()
const purposes = usePurposesQuery()
const climates = useClimatesQuery()
const options = computed(() => flattenCategories(categories.data.value ?? []))
function change(key: keyof ItemFilters, event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const next = { ...props.modelValue }
  if (!value) delete next[key]
  else if (key === 'tracking_mode') next.tracking_mode = value as 'individual' | 'grouped'
  else next[key] = Number(value)
  emit('update:modelValue', next)
}
</script>

<template>
  <fieldset class="catalog-filters">
    <legend>Фильтры</legend>
    <template v-if="!fixedCategory">
      <label for="filter-category">Категория</label>
      <select id="filter-category" :value="modelValue.category_id ?? ''" @change="change('category_id', $event)">
        <option value="">Все категории</option>
        <option v-for="entry in options" :key="entry.id" :value="entry.id">{{ entry.label }}</option>
      </select>
    </template>
    <label for="filter-condition">Состояние</label>
    <select id="filter-condition" :value="modelValue.condition_id ?? ''" @change="change('condition_id', $event)">
      <option value="">Все состояния</option><option v-for="entry in conditions.data.value" :key="entry.id" :value="entry.id">{{ entry.name }}</option>
    </select>
    <label for="filter-purpose">Назначение</label>
    <select id="filter-purpose" :value="modelValue.purpose_id ?? ''" @change="change('purpose_id', $event)">
      <option value="">Все назначения</option><option v-for="entry in purposes.data.value" :key="entry.id" :value="entry.id">{{ entry.name }}</option>
    </select>
    <label for="filter-climate">Климат</label>
    <select id="filter-climate" :value="modelValue.climate_id ?? ''" @change="change('climate_id', $event)">
      <option value="">Любой климат</option><option v-for="entry in climates.data.value" :key="entry.id" :value="entry.id">{{ entry.name }}</option>
    </select>
    <label for="filter-tracking">Тип учёта</label>
    <select id="filter-tracking" :value="modelValue.tracking_mode ?? ''" @change="change('tracking_mode', $event)">
      <option value="">Все</option><option value="individual">Индивидуальные</option><option value="grouped">Группы</option>
    </select>
    <button type="button" @click="emit('update:modelValue', {})">Сбросить фильтры</button>
  </fieldset>
</template>
