import { useQuery } from '@tanstack/vue-query'
import { toValue, type MaybeRefOrGetter } from 'vue'
import { apiClient } from './client'

export async function getPurposes() {
  const { data, response } = await apiClient.GET('/api/reference/purposes')
  if (!response.ok || !data) throw new Error('Не удалось загрузить назначения.')
  return data
}

export async function getConditions() {
  const { data, response } = await apiClient.GET('/api/reference/conditions')
  if (!response.ok || !data) throw new Error('Не удалось загрузить состояния.')
  return data
}

export async function getClimates() {
  const { data, response } = await apiClient.GET('/api/reference/climates')
  if (!response.ok || !data) throw new Error('Не удалось загрузить климат.')
  return data
}

export function usePurposesQuery(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({ queryKey: ['reference', 'purposes'], queryFn: getPurposes,
    enabled: () => toValue(enabled), retry: false, refetchOnWindowFocus: false })
}

export function useConditionsQuery(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({ queryKey: ['reference', 'conditions'], queryFn: getConditions,
    enabled: () => toValue(enabled), retry: false, refetchOnWindowFocus: false })
}

export function useClimatesQuery(enabled: MaybeRefOrGetter<boolean> = true) {
  return useQuery({ queryKey: ['reference', 'climates'], queryFn: getClimates,
    enabled: () => toValue(enabled), retry: false, refetchOnWindowFocus: false })
}
