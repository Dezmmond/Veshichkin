import { useQuery } from '@tanstack/vue-query'
import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'
import { apiClient } from './client'

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
