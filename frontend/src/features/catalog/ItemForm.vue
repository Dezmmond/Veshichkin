<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { components } from '../../api/generated/schema'
import type { ItemCreate, ItemPatch } from '../../api/items'
import { useCategoriesQuery } from '../../api/categories'
import { useConditionsQuery, usePurposesQuery, useClimatesQuery } from '../../api/referenceData'
import { findCategoryById } from './categoryTree'

const props = defineProps<{
  item?: components['schemas']['ItemResponse']; categoryId?: number; pending: boolean; error: boolean
}>()
const emit = defineEmits<{ create: [body: ItemCreate]; update: [body: ItemPatch] }>()
const categories = useCategoriesQuery()
const conditions = useConditionsQuery()
const purposes = usePurposesQuery()
const climates = useClimatesQuery()
const queries = [categories, conditions, purposes, climates]
const loading = computed(() => queries.some((q) => q.isPending.value))
const loadError = computed(() => queries.some((q) => q.isError.value))
const selectedCategory = ref(props.item?.category_id ?? '')
const categoryTouched = ref(false)
const preselected = computed(() => props.categoryId !== undefined && findCategoryById(categories.data.value ?? [], props.categoryId)
  ? props.categoryId : '')
const categoryValue = computed({ get: () => categoryTouched.value || props.item ? selectedCategory.value : preselected.value,
  set: (value: number | string) => { categoryTouched.value = true; selectedCategory.value = value } })
const fields = reactive({
  name: props.item?.name ?? '', tracking_mode: props.item?.tracking_mode ?? 'individual',
  quantity: props.item?.quantity ?? '', condition_id: props.item?.condition_id ?? '',
  purpose_ids: [...(props.item?.purpose_ids ?? [])], climate_ids: [...(props.item?.climate_ids ?? [])],
  brand: props.item?.brand ?? '', model: props.item?.model ?? '', color: props.item?.color ?? '',
  size: props.item?.size ?? '', material: props.item?.material ?? '', notes: props.item?.notes ?? '',
})
const optionalFields = [ ['brand', 'Бренд'], ['model', 'Модель'], ['color', 'Цвет'],
  ['size', 'Размер'], ['material', 'Материал'], ['notes', 'Заметки'] ] as const
const extra = ref(props.item ? JSON.stringify(props.item.extra_attributes, null, 2) : '')
const validation = ref('')
function flatten(tree: components['schemas']['CategoryTree'][], depth = 0): { id: number; label: string }[] {
  return tree.flatMap((entry) => [{ id: entry.id, label: `${'↳ '.repeat(depth)}${entry.name}` },
    ...flatten(entry.children ?? [], depth + 1)])
}
const options = computed(() => flatten(categories.data.value ?? []))
const cancel = computed(() => props.item ? `/catalog/items/${props.item.id}`
  : preselected.value ? `/catalog/categories/${preselected.value}` : '/catalog')

function submit() {
  if (props.pending || loading.value || loadError.value) return
  validation.value = ''
  if (!fields.name.trim() || !categoryValue.value || !fields.condition_id
    || !['individual', 'grouped'].includes(fields.tracking_mode)) {
    validation.value = 'Заполните название, категорию, тип учёта и состояние.'
    return
  }
  const quantity = Number(fields.quantity)
  if (fields.tracking_mode === 'grouped' && (fields.quantity === '' || !Number.isInteger(quantity) || quantity < 0)) {
    validation.value = 'Количество должно быть целым числом не меньше 0.'
    return
  }
  let extraAttributes: ItemCreate['extra_attributes']
  try {
    const parsed: unknown = extra.value.trim() ? JSON.parse(extra.value) : {}
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
    extraAttributes = parsed as ItemCreate['extra_attributes']
  } catch {
    validation.value = 'Дополнительные свойства должны быть корректным JSON-объектом.'
    return
  }
  const body: ItemPatch = { name: fields.name.trim(), category_id: Number(categoryValue.value),
    condition_id: Number(fields.condition_id), purpose_ids: [...fields.purpose_ids], climate_ids: [...fields.climate_ids],
    extra_attributes: extraAttributes }
  if (fields.tracking_mode === 'grouped') body.quantity = quantity
  for (const [key] of optionalFields) {
    const value = fields[key].trim()
    if (props.item || value) body[key] = value || null
  }
  if (props.item) emit('update', body)
  else emit('create', { ...body, name: fields.name.trim(), category_id: Number(categoryValue.value),
    condition_id: Number(fields.condition_id), tracking_mode: fields.tracking_mode })
}
</script>

<template>
  <p v-if="loadError" role="alert">Не удалось загрузить данные формы.</p>
  <p v-else-if="loading" role="status">Загрузка формы…</p>
  <form v-else class="item-form" novalidate @submit.prevent="submit">
    <fieldset :disabled="pending">
      <legend class="visually-hidden">Данные вещи</legend>
      <label for="item-name">Название *</label><input id="item-name" v-model="fields.name" required>
      <label for="item-category">Категория *</label>
      <select id="item-category" v-model="categoryValue" required>
        <option value="">Выберите категорию</option>
        <option v-for="entry in options" :key="entry.id" :value="entry.id">{{ entry.label }}</option>
      </select>
      <template v-if="item"><p>Учёт: {{ fields.tracking_mode === 'individual' ? 'Индивидуальная вещь' : 'Группа одинаковых вещей' }}</p></template>
      <template v-else>
        <label for="item-tracking">Тип учёта *</label>
        <select id="item-tracking" v-model="fields.tracking_mode">
          <option value="individual">Индивидуальная вещь</option><option value="grouped">Группа одинаковых вещей</option>
        </select>
      </template>
      <template v-if="fields.tracking_mode === 'grouped'">
        <label for="item-quantity">Количество *</label>
        <input id="item-quantity" v-model="fields.quantity" type="number" min="0" step="1" inputmode="numeric" required>
      </template>
      <label for="item-condition">Состояние *</label>
      <select id="item-condition" v-model="fields.condition_id" required>
        <option value="">Выберите состояние</option>
        <option v-for="entry in conditions.data.value" :key="entry.id" :value="entry.id">{{ entry.name }}</option>
      </select>
      <fieldset class="item-choices"><legend>Назначения</legend>
        <label v-for="entry in purposes.data.value" :key="entry.id">
          <input v-model="fields.purpose_ids" type="checkbox" :value="entry.id" :data-purpose="entry.id">{{ entry.name }}
        </label>
      </fieldset>
      <fieldset class="item-choices"><legend>Климат</legend>
        <label v-for="entry in climates.data.value" :key="entry.id">
          <input v-model="fields.climate_ids" type="checkbox" :value="entry.id" :data-climate="entry.id">{{ entry.name }}
        </label>
      </fieldset>
      <details><summary>Необязательные поля</summary>
        <template v-for="[key, label] in optionalFields" :key="key">
          <label :for="`item-${key}`">{{ label }}</label>
          <textarea v-if="key === 'notes'" :id="`item-${key}`" v-model="fields[key]" rows="3" />
          <input v-else :id="`item-${key}`" v-model="fields[key]">
        </template>
      </details>
      <details><summary>Дополнительные свойства</summary>
        <label for="item-extra">JSON-объект</label>
        <textarea id="item-extra" v-model="extra" rows="5" spellcheck="false" />
      </details>
    </fieldset>
    <p v-if="validation" role="alert">{{ validation }}</p>
    <p v-if="error" role="alert">Не удалось сохранить вещь.</p>
    <div class="item-actions">
      <button type="submit" :disabled="pending">{{ pending ? 'Сохранение…' : 'Сохранить' }}</button>
      <RouterLink :to="cancel">Отмена</RouterLink>
    </div>
  </form>
</template>
