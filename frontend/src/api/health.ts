import { useQuery } from '@tanstack/vue-query'
import { apiClient } from './client'

export async function getHealth() {
  const { data, response } = await apiClient.GET('/api/health')
  if (!response.ok || !data) {
    throw new Error('Backend is unavailable')
  }
  return data
}

export function useHealthQuery() {
  return useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    retry: false,
    refetchOnWindowFocus: false,
  })
}
