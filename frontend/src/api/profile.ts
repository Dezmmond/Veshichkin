import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { apiClient } from './client'
import type { components } from './generated/schema'

export type MeasurementProfilePatch = components['schemas']['MeasurementProfilePatch']
export const measurementProfileQueryKey = ['measurement-profile'] as const

export async function getMeasurementProfile() {
  const { data, response } = await apiClient.GET('/api/profile/measurements')
  if (!response.ok || data === undefined) throw new Error('Не удалось загрузить замеры.')
  return data
}

export async function updateMeasurementProfile(body: MeasurementProfilePatch) {
  const { data, response } = await apiClient.PATCH('/api/profile/measurements', { body })
  if (!response.ok || !data) throw new Error('Не удалось сохранить замеры.')
  return data
}

export function useMeasurementProfileQuery() {
  return useQuery({ queryKey: measurementProfileQueryKey, queryFn: getMeasurementProfile,
    retry: false, refetchOnWindowFocus: false })
}

export function useUpdateMeasurementProfileMutation() {
  const client = useQueryClient()
  return useMutation({ mutationFn: updateMeasurementProfile,
    onSuccess: () => client.invalidateQueries({ queryKey: measurementProfileQueryKey }) })
}
