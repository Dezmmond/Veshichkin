import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { getCategories } from './categories'
import { getPurposes, getConditions, getClimates } from './referenceData'
import { getItems, itemsQueryKey } from './items'
import { tree, item, purposes, conditions, climates } from '../features/catalog/fixtures.test-support'

afterEach(() => vi.restoreAllMocks())

describe('catalog API modules', () => {
  it('requests categories and returns the generated response', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: tree, response: new Response() })
    await expect(getCategories()).resolves.toEqual(tree)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/categories')
  })
  it.each([
    [getPurposes, '/api/reference/purposes', purposes],
    [getConditions, '/api/reference/conditions', conditions],
    [getClimates, '/api/reference/climates', climates],
  ] as const)('requests references %s', async (getReference, path, data) => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data, response: new Response() })
    await expect(getReference()).resolves.toEqual(data)
    expect(request).toHaveBeenCalledExactlyOnceWith(path)
  })
  it('passes exact category filters as query parameters', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: [item], response: new Response() })
    await expect(getItems({ category_id: 20 })).resolves.toEqual([item])
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/items', { params: { query: { category_id: 20 } } })
  })
  it('includes filters in item cache keys', () => {
    expect(itemsQueryKey({ category_id: 20 })).toEqual(['items', { category_id: 20 }])
    expect(itemsQueryKey({ category_id: 20 })).not.toEqual(itemsQueryKey({ category_id: 30 }))
  })
  it.each([getCategories, getPurposes, getConditions, getClimates, () => getItems({ category_id: 20 })])(
    'rejects HTTP failure for %s', async (request) => {
      vi.spyOn(apiClient, 'GET').mockResolvedValue({ response: new Response(null, { status: 503 }) })
      await expect(request()).rejects.toThrow('Не удалось загрузить')
    },
  )
  it.each([getCategories, () => getItems({ category_id: 20 })])('rejects network failure for %s', async (request) => {
    vi.spyOn(apiClient, 'GET').mockRejectedValue(new TypeError('Network unavailable'))
    await expect(request()).rejects.toThrow('Network unavailable')
  })
})
