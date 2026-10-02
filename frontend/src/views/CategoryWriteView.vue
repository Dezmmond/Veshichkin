<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useCategoriesQuery, useCreateCategoryMutation, useUpdateCategoryMutation, useDeleteCategoryMutation, type CategoryCreate } from '../api/categories'
import { findCategoryById, parseCategoryId } from '../features/catalog/categoryTree'
import CategoryForm from '../features/catalog/CategoryForm.vue'

const route = useRoute()
const router = useRouter()
const editing = computed(() => route.name === 'category-edit')
const id = computed(() => parseCategoryId(route.params.categoryId))
const parentId = computed(() => parseCategoryId(route.query.parent_id))
const categories = useCategoriesQuery(() => !editing.value || id.value !== undefined)
const category = computed(() => id.value === undefined ? undefined : findCategoryById(categories.data.value ?? [], id.value))
const create = useCreateCategoryMutation()
const update = useUpdateCategoryMutation()
const deletion = useDeleteCategoryMutation()
const confirming = ref(false)
watch(() => route.fullPath, () => { create.reset(); update.reset(); deletion.reset(); confirming.value = false })
const pending = computed(() => create.isPending.value || update.isPending.value || deletion.isPending.value)
const saveError = computed(() => create.error.value?.message ?? update.error.value?.message)
async function save(body: CategoryCreate) {
  if (pending.value) return
  try {
    const saved = editing.value && id.value !== undefined ? await update.mutateAsync({ id: id.value, body }) : await create.mutateAsync(body)
    await router.push(`/catalog/categories/${saved.id}`)
  } catch { /* Safe mapped API error is displayed by the form. */ }
}
async function remove() {
  if (id.value === undefined || pending.value) return
  try {
    await deletion.mutateAsync(id.value)
    await router.push('/catalog')
  } catch { /* Safe mapped API error is displayed inline. */ }
}
</script>

<template>
  <section>
    <template v-if="editing && (id === undefined || (!categories.isPending.value && !categories.isError.value && !category))">
      <h1>Категория не найдена</h1><RouterLink to="/catalog">Вернуться в каталог</RouterLink>
    </template>
    <template v-else>
      <h1>{{ editing ? 'Редактировать категорию' : 'Добавить категорию' }}</h1>
      <p v-if="categories.isError.value" role="alert">Не удалось загрузить категории.</p>
      <p v-else-if="categories.isPending.value" role="status">Загрузка категорий…</p>
      <template v-else>
        <CategoryForm :key="editing ? id : 'new'" :tree="categories.data.value ?? []" :category="editing ? category : undefined"
          :parent-id="parentId" :pending="pending" :error="saveError" @save="save" />
        <section v-if="editing && category" class="category-deletion" aria-label="Удаление категории">
          <button v-if="!confirming" class="management-action" type="button" :disabled="pending" @click="confirming = true; deletion.reset()">Удалить категорию</button>
          <section v-else class="confirmation" aria-label="Подтверждение удаления категории">
            <p>Удалить категорию «{{ category.name }}»?</p>
            <p>Категория удалится только если не содержит подкатегорий и не используется вещами или ревизиями.</p>
            <div class="item-actions">
              <button type="button" :disabled="pending" @click="confirming = false; deletion.reset()">Отмена</button>
              <button type="button" :disabled="pending" @click="remove">{{ deletion.isPending.value ? 'Удаление…' : 'Удалить' }}</button>
            </div>
          </section>
          <p v-if="deletion.isError.value" role="alert">{{ deletion.error.value?.message }}</p>
        </section>
      </template>
    </template>
  </section>
</template>
