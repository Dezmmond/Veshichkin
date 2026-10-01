import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { apiClient } from './client'
import type { components, operations } from './generated/schema'

export type ItemCreate = components['schemas']['ItemCreate']
export type ItemPatch = components['schemas']['ItemPatch']

export type ItemFilters = NonNullable<operations['list_items_api_items_get']['parameters']['query']>

export async function getItems(filters: ItemFilters) {
  const { data, response } = await apiClient.GET('/api/items', { params: { query: filters } })
  if (!response.ok || !data) throw new Error('Не удалось загрузить вещи.')
  return data
}

export async function getItem(id: number) {
  const { data, response } = await apiClient.GET('/api/items/{item_id}', { params: { path: { item_id: id } } })
  if (response.status === 404) return null
  if (!response.ok || !data) throw new Error('Не удалось загрузить вещь.')
  return data
}

export async function createItem(body: ItemCreate) {
  const { data, response } = await apiClient.POST('/api/items', { body })
  if (!response.ok || !data) throw new Error('Не удалось сохранить вещь.')
  return data
}

export async function updateItem(id: number, body: ItemPatch) {
  const { data, response } = await apiClient.PATCH('/api/items/{item_id}', { params: { path: { item_id: id } }, body })
  if (!response.ok || !data) throw new Error('Не удалось сохранить вещь.')
  return data
}

export const itemQueryKey = (id: number | undefined) => ['item', id] as const

export function useItemQuery(id: MaybeRefOrGetter<number | undefined>) {
  return useQuery({ queryKey: computed(() => itemQueryKey(toValue(id))),
    queryFn: () => getItem(toValue(id)!), enabled: () => toValue(id) !== undefined,
    retry: false, refetchOnWindowFocus: false })
}

export function useCreateItemMutation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: createItem, onSuccess: async (item) => {
    await Promise.all([client.invalidateQueries({ queryKey: ['items'] }),
      client.invalidateQueries({ queryKey: itemQueryKey(item.id) })])
  } })
}

export function useUpdateItemMutation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: ({ id, body }: { id: number; body: ItemPatch }) => updateItem(id, body),
    onSuccess: async (item) => {
      await Promise.all([client.invalidateQueries({ queryKey: ['items'] }),
        client.invalidateQueries({ queryKey: itemQueryKey(item.id) })])
    } })
}

export const itemsQueryKey = (filters: ItemFilters) => ['items', filters] as const

export function useItemsQuery(
  filters: MaybeRefOrGetter<ItemFilters>, enabled: MaybeRefOrGetter<boolean> = true,
) {
  return useQuery({
    queryKey: computed(() => itemsQueryKey(toValue(filters))),
    queryFn: () => getItems(toValue(filters)), enabled: () => toValue(enabled),
    retry: false, refetchOnWindowFocus: false,
  })
}
