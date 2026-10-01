import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { getHealth } from './health'

afterEach(() => vi.restoreAllMocks())

describe('health API', () => {
  it('returns the successful typed response', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({
      data: { status: 'ok' }, response: new Response(null, { status: 200 }),
    })
    await expect(getHealth()).resolves.toEqual({ status: 'ok' })
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/health')
  })

  it('rejects a network failure', async () => {
    vi.spyOn(apiClient, 'GET').mockRejectedValue(new TypeError('Network unavailable'))
    await expect(getHealth()).rejects.toThrow('Network unavailable')
  })

  it('rejects an unsuccessful HTTP status even if a body is returned', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({
      data: { status: 'ok' }, response: new Response(null, { status: 503 }),
    })
    await expect(getHealth()).rejects.toThrow('Backend is unavailable')
  })
})
