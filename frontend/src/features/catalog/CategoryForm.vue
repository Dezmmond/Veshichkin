<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { RouterLink } from 'vue-router'
import type { components } from '../../api/generated/schema'
import type { CategoryCreate } from '../../api/categories'
import { findCategoryById, flattenCategories } from './categoryTree'

const props = defineProps<{ tree: components['schemas']['CategoryTree'][];
  category?: components['schemas']['CategoryTree']; parentId?: number; pending: boolean; error?: string }>()
const emit = defineEmits<{ save: [body: CategoryCreate] }>()
const validParent = props.parentId !== undefined && findCategoryById(props.tree, props.parentId) ? props.parentId : null
const fields = reactive({ name: props.category?.name ?? '', parent_id: props.category ? props.category.parent_id : validParent,
  sort_order: props.category?.sort_order ?? 0 as number | string })
const blocked = computed(() => new Set(props.category ? flattenCategories([props.category]).map((entry) => entry.id) : []))
const options = computed(() => flattenCategories(props.tree).filter((entry) => !blocked.value.has(entry.id)))
const validation = ref('')
const cancel = props.category ? `/catalog/categories/${props.category.id}` : validParent ? `/catalog/categories/${validParent}` : '/catalog'
function submit() {
  if (props.pending) return
  validation.value = ''
  if (!fields.name.trim()) { validation.value = 'Укажите название категории.'; return }
  const order = Number(fields.sort_order)
  if (fields.sort_order === '' || !Number.isInteger(order) || order < 0) {
    validation.value = 'Порядок должен быть целым числом не меньше 0.'; return
  }
  emit('save', { name: fields.name.trim(), parent_id: fields.parent_id ?? null, sort_order: order })
}
</script>

<template>
  <form class="item-form category-form" novalidate @submit.prevent="submit">
    <fieldset :disabled="pending">
      <legend class="visually-hidden">Данные категории</legend>
      <label for="category-name">Название *</label><input id="category-name" v-model="fields.name" required>
      <label for="category-parent">Родительская категория</label>
      <select id="category-parent" v-model="fields.parent_id">
        <option :value="null">Без родительской категории</option>
        <option v-for="entry in options" :key="entry.id" :value="entry.id">{{ entry.label }}</option>
      </select>
      <label for="category-order">Порядок</label>
      <input id="category-order" v-model="fields.sort_order" type="number" min="0" step="1" inputmode="numeric">
    </fieldset>
    <p v-if="validation" role="alert">{{ validation }}</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <div class="item-actions"><button type="submit" :disabled="pending">{{ pending ? 'Сохранение…' : 'Сохранить' }}</button><RouterLink :to="cancel">Отмена</RouterLink></div>
  </form>
</template>
