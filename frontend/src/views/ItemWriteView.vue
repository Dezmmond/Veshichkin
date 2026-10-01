<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import ItemForm from '../features/catalog/ItemForm.vue'
import { parseCategoryId } from '../features/catalog/categoryTree'
import { useItemQuery, useCreateItemMutation, useUpdateItemMutation, type ItemCreate, type ItemPatch } from '../api/items'

const route = useRoute()
const router = useRouter()
const editing = computed(() => route.name === 'item-edit')
const id = computed(() => editing.value ? parseCategoryId(route.params.itemId) : undefined)
const categoryId = computed(() => parseCategoryId(route.query.category_id))
const item = useItemQuery(id)
const create = useCreateItemMutation()
const update = useUpdateItemMutation()
watch(() => route.fullPath, () => { create.reset(); update.reset() })
async function saveCreate(body: ItemCreate) {
  try {
    const saved = await create.mutateAsync(body)
    await router.push(`/catalog/items/${saved.id}`)
  } catch { /* Mutation error is displayed by the form. */ }
}
async function saveUpdate(body: ItemPatch) {
  if (id.value === undefined) return
  try {
    const saved = await update.mutateAsync({ id: id.value, body })
    await router.push(`/catalog/items/${saved.id}`)
  } catch { /* Mutation error is displayed by the form. */ }
}
</script>

<template>
  <section>
    <template v-if="editing && (id === undefined || item.data.value === null)">
      <h1>Вещь не найдена</h1><RouterLink to="/catalog">Вернуться в каталог</RouterLink>
    </template>
    <template v-else>
      <h1>{{ editing ? 'Редактировать вещь' : 'Добавить вещь' }}</h1>
      <p v-if="editing && item.isError.value" role="alert">Не удалось загрузить вещь.</p>
      <p v-else-if="editing && item.isPending.value" role="status">Загрузка вещи…</p>
      <ItemForm v-else :key="editing ? id : 'new'" :item="editing ? item.data.value ?? undefined : undefined"
        :category-id="categoryId" :pending="create.isPending.value || update.isPending.value"
        :error="create.isError.value || update.isError.value" @create="saveCreate" @update="saveUpdate" />
    </template>
  </section>
</template>
