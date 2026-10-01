import { useQuery } from '@tanstack/vue-query'
import { computed, toValue, type MaybeRefOrGetter } from 'vue'
import { apiClient } from './client'
import type { operations } from './generated/schema'

export type ItemFilters = NonNullable<operations['list_items_api_items_get']['parameters']['query']>

export async function getItems(filters: ItemFilters) {
  const { data, response } = await apiClient.GET('/api/items', { params: { query: filters } })
  if (!response.ok || !data) throw new Error('Не удалось загрузить вещи.')
  return data
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
