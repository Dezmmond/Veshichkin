import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { apiClient } from './client'
import type { components } from './generated/schema'

export type CategoryCreate = components['schemas']['CategoryCreate']
export type CategoryPatch = components['schemas']['CategoryPatch']

function categoryError(error: components['schemas']['ErrorResponse'] | components['schemas']['HTTPValidationError'] | undefined, deleting = false) {
  const code = error && 'error' in error ? error.error.code : undefined
  const messages: Record<string, string> = {
    category_not_found: 'Категория не найдена.',
    category_parent_not_found: 'Родительская категория больше не существует.',
    category_cycle: 'Нельзя переместить категорию внутрь самой себя или её подкатегории.',
    category_in_use: 'Категорию нельзя удалить, пока она используется или содержит подкатегории.',
  }
  return new Error((code && messages[code]) || (deleting ? 'Не удалось удалить категорию.' : 'Не удалось сохранить категорию.'))
}

export async function createCategory(body: CategoryCreate) {
  const { data, error, response } = await apiClient.POST('/api/categories', { body }).catch(() => { throw categoryError(undefined) })
  if (!response.ok || !data) throw categoryError(error)
  return data
}

export async function updateCategory(id: number, body: CategoryPatch) {
  const { data, error, response } = await apiClient.PATCH('/api/categories/{category_id}', { params: { path: { category_id: id } }, body }).catch(() => { throw categoryError(undefined) })
  if (!response.ok || !data) throw categoryError(error)
  return data
}

export async function deleteCategory(id: number) {
  const { error, response } = await apiClient.DELETE('/api/categories/{category_id}', { params: { path: { category_id: id } } }).catch(() => { throw categoryError(undefined, true) })
  if (!response.ok) throw categoryError(error, true)
}

export function useCreateCategoryMutation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: createCategory,
    onSuccess: () => client.invalidateQueries({ queryKey: ['categories'] }) })
}

export function useUpdateCategoryMutation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: ({ id, body }: { id: number; body: CategoryPatch }) => updateCategory(id, body),
    onSuccess: () => client.invalidateQueries({ queryKey: ['categories'] }) })
}

export function useDeleteCategoryMutation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: deleteCategory,
    onSuccess: () => client.invalidateQueries({ queryKey: ['categories'] }) })
}

export async function getCategories() {
  const { data, response } = await apiClient.GET('/api/categories')
  if (!response.ok || !data) throw new Error('Не удалось загрузить категории.')
  return data
}

export function useCategoriesQuery(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({
    queryKey: ['categories'], queryFn: getCategories,
    enabled: () => toValue(enabled), retry: false, refetchOnWindowFocus: false,
  })
}
