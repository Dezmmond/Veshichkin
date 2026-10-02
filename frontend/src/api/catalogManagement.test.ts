import { afterEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { createCategory, updateCategory, deleteCategory, type CategoryCreate } from './categories'
import { removeItem } from './items'
import { tree } from '../features/catalog/fixtures.test-support'

afterEach(() => vi.restoreAllMocks())
const body: CategoryCreate = { name: 'Новая категория', parent_id: null, sort_order: 2 }

describe('category management API', () => {
  it('creates a category with generated payload', async () => {
    const request = vi.spyOn(apiClient, 'POST').mockResolvedValue({ data: tree[1], response: new Response(null, { status: 201 }) })
    await expect(createCategory(body)).resolves.toEqual(tree[1])
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/categories', { body })
  })
  it('patches category by path ID, including explicit parent null', async () => {
    const request = vi.spyOn(apiClient, 'PATCH').mockResolvedValue({ data: tree[1], response: new Response() })
    await expect(updateCategory(40, body)).resolves.toEqual(tree[1])
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/categories/{category_id}', { params: { path: { category_id: 40 } }, body })
  })
  it('deletes a category by path ID and accepts empty 204', async () => {
    const request = vi.spyOn(apiClient, 'DELETE').mockResolvedValue({ data: undefined, response: new Response(null, { status: 204 }) })
    await expect(deleteCategory(40)).resolves.toBeUndefined()
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/categories/{category_id}', { params: { path: { category_id: 40 } } })
  })
  it.each([
    ['category_not_found', 'Категория не найдена.'],
    ['category_parent_not_found', 'Родительская категория больше не существует.'],
    ['category_cycle', 'Нельзя переместить категорию внутрь самой себя или её подкатегории.'],
    ['category_in_use', 'Категорию нельзя удалить, пока она используется или содержит подкатегории.'],
  ])('maps known error %s without exposing backend text', async (code, message) => {
    const response = { error: { error: { code, message: 'SQL secret' }, detail: [] }, response: new Response(null, { status: 409 }) }
    vi.spyOn(apiClient, 'POST').mockResolvedValue(response)
    vi.spyOn(apiClient, 'PATCH').mockResolvedValue(response)
    vi.spyOn(apiClient, 'DELETE').mockResolvedValue(response)
    await expect(createCategory(body)).rejects.toThrow(message)
    await expect(updateCategory(40, body)).rejects.toThrow(message)
    await expect(deleteCategory(40)).rejects.toThrow(message)
  })
  it('maps unknown HTTP errors to safe operation messages', async () => {
    const response = { error: { detail: [] }, response: new Response(null, { status: 422 }) }
    vi.spyOn(apiClient, 'POST').mockResolvedValue(response)
    vi.spyOn(apiClient, 'PATCH').mockResolvedValue(response)
    vi.spyOn(apiClient, 'DELETE').mockResolvedValue(response)
    await expect(createCategory(body)).rejects.toThrow('Не удалось сохранить категорию.')
    await expect(updateCategory(40, body)).rejects.toThrow('Не удалось сохранить категорию.')
    await expect(deleteCategory(40)).rejects.toThrow('Не удалось удалить категорию.')
  })
  it('normalizes network errors safely', async () => {
    vi.spyOn(apiClient, 'POST').mockRejectedValue(new Error('private network secret'))
    vi.spyOn(apiClient, 'PATCH').mockRejectedValue(new Error('private network secret'))
    vi.spyOn(apiClient, 'DELETE').mockRejectedValue(new Error('private network secret'))
    await expect(createCategory(body)).rejects.toThrow('Не удалось сохранить категорию.')
    await expect(updateCategory(40, body)).rejects.toThrow('Не удалось сохранить категорию.')
    await expect(deleteCategory(40)).rejects.toThrow('Не удалось удалить категорию.')
  })
})

describe('non-destructive item removal API', () => {
  it('sends DELETE with correct item ID', async () => {
    const request = vi.spyOn(apiClient, 'DELETE').mockResolvedValue({ data: undefined, response: new Response(null, { status: 204 }) })
    await expect(removeItem(1)).resolves.toBe(1)
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/items/{item_id}', { params: { path: { item_id: 1 } } })
  })
  it('rejects HTTP errors', async () => {
    vi.spyOn(apiClient, 'DELETE').mockResolvedValue({ error: { detail: [] }, response: new Response(null, { status: 422 }) })
    await expect(removeItem(1)).rejects.toThrow('Не удалось убрать вещь из каталога.')
  })
  it('rejects network errors', async () => {
    vi.spyOn(apiClient, 'DELETE').mockRejectedValue(new Error('Network unavailable'))
    await expect(removeItem(1)).rejects.toThrow('Network unavailable')
  })
})
