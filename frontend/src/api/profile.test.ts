import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { getMeasurementProfile, updateMeasurementProfile, type MeasurementProfilePatch } from './profile'
import { profile } from '../features/profile/fixtures.test-support'

afterEach(() => vi.restoreAllMocks())

describe('measurement profile API', () => {
  it('returns typed profile including decimal strings', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    await expect(getMeasurementProfile()).resolves.toEqual(profile)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/profile/measurements')
  })
  it('accepts successful null as normal empty state', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: null, response: new Response() })
    await expect(getMeasurementProfile()).resolves.toBeNull()
  })
  it('rejects HTTP GET error', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ response: new Response(null, { status: 503 }) })
    await expect(getMeasurementProfile()).rejects.toThrow('Не удалось загрузить замеры.')
  })
  it('rejects missing response data rather than treating it as null', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ response: new Response() })
    await expect(getMeasurementProfile()).rejects.toThrow('Не удалось загрузить замеры.')
  })
  it('rejects GET network error', async () => {
    vi.spyOn(apiClient, 'GET').mockRejectedValue(new TypeError('Network unavailable'))
    await expect(getMeasurementProfile()).rejects.toThrow('Network unavailable')
  })
  it('patches generated payload with decimal string, explicit null and custom object', async () => {
    const body: MeasurementProfilePatch = { foot_length_cm: '0.01', height_cm: null, extra_measurements: { neck_cm: 39 } }
    const request = vi.spyOn(apiClient, 'PATCH').mockResolvedValue({ data: profile, response: new Response() })
    await expect(updateMeasurementProfile(body)).resolves.toEqual(profile)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/profile/measurements', { body })
  })
  it('rejects PATCH HTTP error', async () => {
    vi.spyOn(apiClient, 'PATCH').mockResolvedValue({ error: { detail: [] }, response: new Response(null, { status: 422 }) })
    await expect(updateMeasurementProfile({})).rejects.toThrow('Не удалось сохранить замеры.')
  })
  it('rejects PATCH network error', async () => {
    vi.spyOn(apiClient, 'PATCH').mockRejectedValue(new TypeError('Network unavailable'))
    await expect(updateMeasurementProfile({})).rejects.toThrow('Network unavailable')
  })
})
