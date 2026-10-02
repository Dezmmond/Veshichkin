import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { getItem, createItem, updateItem, type ItemCreate, type ItemPatch } from './items'
import { item } from '../features/catalog/fixtures.test-support'

afterEach(() => vi.restoreAllMocks())
const createBody: ItemCreate = { name: 'Новая', category_id: 20, condition_id: 5, tracking_mode: 'individual' }
const patchBody: ItemPatch = { brand: null, purpose_ids: [], extra_attributes: {} }

describe('item write API', () => {
  it('gets item by typed path ID', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: item, response: new Response() })
    await expect(getItem(1)).resolves.toEqual(item)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/items/{item_id}', { params: { path: { item_id: 1 } } })
  })
  it('returns null for 404', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ response: new Response(null, { status: 404 }) })
    await expect(getItem(999)).resolves.toBeNull()
  })
  it('rejects HTTP GET errors', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ response: new Response(null, { status: 500 }) })
    await expect(getItem(1)).rejects.toThrow('Не удалось загрузить вещь.')
  })
  it('rejects GET network errors', async () => {
    vi.spyOn(apiClient, 'GET').mockRejectedValue(new TypeError('Network unavailable'))
    await expect(getItem(1)).rejects.toThrow('Network unavailable')
  })
  it('posts generated create payload', async () => {
    const request = vi.spyOn(apiClient, 'POST').mockResolvedValue({ data: item, response: new Response(null, { status: 201 }) })
    await expect(createItem(createBody)).resolves.toEqual(item)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/items', { body: createBody })
  })
  it('patches generated payload with correct ID', async () => {
    const request = vi.spyOn(apiClient, 'PATCH').mockResolvedValue({ data: item, response: new Response() })
    await expect(updateItem(1, patchBody)).resolves.toEqual(item)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/items/{item_id}', { params: { path: { item_id: 1 } }, body: patchBody })
  })
  it.each([404, 422, 500])('rejects mutation HTTP %s', async (status) => {
    vi.spyOn(apiClient, 'POST').mockResolvedValue({ error: { detail: [] }, response: new Response(null, { status }) })
    vi.spyOn(apiClient, 'PATCH').mockResolvedValue({ error: { detail: [] }, response: new Response(null, { status }) })
    await expect(createItem(createBody)).rejects.toThrow('Не удалось сохранить вещь.')
    await expect(updateItem(1, patchBody)).rejects.toThrow('Не удалось сохранить вещь.')
  })
  it('rejects mutation network errors', async () => {
    vi.spyOn(apiClient, 'POST').mockRejectedValue(new TypeError('Network unavailable'))
    vi.spyOn(apiClient, 'PATCH').mockRejectedValue(new TypeError('Network unavailable'))
    await expect(createItem(createBody)).rejects.toThrow('Network unavailable')
    await expect(updateItem(1, patchBody)).rejects.toThrow('Network unavailable')
  })
})
