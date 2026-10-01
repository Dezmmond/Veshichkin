import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { RouterView, createMemoryHistory, createRouter } from 'vue-router'
import { apiClient } from '../api/client'
import { routes } from '../router'
import { tree, item, conditions, purposes, climates } from '../features/catalog/fixtures.test-support'
import { itemsQueryKey, type ItemFilters } from '../api/items'
import type { CategoryCreate, CategoryPatch } from '../api/categories'
import type { components } from '../api/generated/schema'

const cleanups: (() => void)[] = []
afterEach(() => { cleanups.splice(0).forEach((fn) => fn()); vi.restoreAllMocks() })

function backend(empty = false) {
  const state = { categories: JSON.parse(JSON.stringify(tree)) as components['schemas']['CategoryTree'][],
    item: { ...item }, empty }
  const get = vi.spyOn(apiClient, 'GET').mockImplementation(async (path) => ({
    data: path === '/api/categories' ? state.categories : path === '/api/items/{item_id}' ? state.item
      : path === '/api/items' ? state.empty || !state.item.is_active ? [] : [state.item]
      : path === '/api/reference/conditions' ? conditions : path === '/api/reference/purposes' ? purposes : climates,
    response: new Response(),
  }))
  return { state, get }
}

async function screen(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } })
  const wrapper = mount(RouterView, { global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } })
  cleanups.push(() => { wrapper.unmount(); queryClient.clear() })
  return { wrapper, router, queryClient }
}

describe('structured catalog filters', () => {
  it('loads all active items with absent filters and preserves root navigation', async () => {
    const { get } = backend()
    const { wrapper } = await screen('/catalog')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    expect(get).toHaveBeenCalledWith('/api/items', { params: { query: {} } })
    expect(wrapper.get('section[aria-label="Все вещи"] h2').text()).toBe('Все вещи')
    expect(wrapper.findAll('.category-links a').map((link) => link.text())).toEqual(['Корень A', 'Корень D'])
    expect(wrapper.get('a[href="/catalog/categories/new"]').text()).toBe('Добавить категорию')
  })
  it.each([
    ['category', '20', { category_id: 20 }],
    ['condition', '5', { condition_id: 5 }],
    ['purpose', '6', { purpose_id: 6 }],
    ['climate', '9', { climate_id: 9 }],
    ['tracking', 'grouped', { tracking_mode: 'grouped' }],
    ['tracking', 'individual', { tracking_mode: 'individual' }],
  ] as const)('applies %s through request params and a distinct query key', async (control, value, filters) => {
    const { get } = backend()
    const { wrapper, queryClient } = await screen('/catalog')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    await wrapper.get(`#filter-${control}`).setValue(value)
    await vi.waitFor(() => expect(get).toHaveBeenCalledWith('/api/items', { params: { query: filters } }))
    await vi.waitFor(() => expect(queryClient.getQueryData(itemsQueryKey(filters))).toEqual([item]))
    expect(queryClient.getQueryData(itemsQueryKey({}))).toEqual([item])
  })
  it('combines filters and resets all selectors to absent values', async () => {
    const { get } = backend()
    const { wrapper } = await screen('/catalog')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    for (const [control, value] of [['category', '20'], ['condition', '5'], ['purpose', '6'], ['climate', '9'], ['tracking', 'grouped']]) {
      await wrapper.get(`#filter-${control}`).setValue(value)
    }
    await vi.waitFor(() => expect(get).toHaveBeenCalledWith('/api/items', { params: { query: {
      category_id: 20, condition_id: 5, purpose_id: 6, climate_id: 9, tracking_mode: 'grouped',
    } } }))
    await wrapper.get('.catalog-filters button').trigger('click')
    expect(wrapper.findAll('.catalog-filters select').map((select) => (select.element as HTMLSelectElement).value))
      .toEqual(['', '', '', '', ''])
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
  })
  it('distinguishes empty catalog from empty filtered results and offers reset', async () => {
    backend(true)
    const { wrapper } = await screen('/catalog')
    await vi.waitFor(() => expect(wrapper.text()).toContain('В каталоге пока нет вещей.'))
    await wrapper.get('#filter-condition').setValue('5')
    await vi.waitFor(() => expect(wrapper.text()).toContain('По выбранным фильтрам ничего не найдено.'))
    expect(wrapper.text()).not.toContain('В каталоге пока нет вещей.')
    await wrapper.get('.catalog-filters button').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('В каталоге пока нет вещей.'))
  })
  it('keeps exact category fixed across filter changes, reset and route navigation', async () => {
    const { get } = backend()
    const { wrapper, router } = await screen('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    expect(wrapper.find('#filter-category').exists()).toBe(false)
    await wrapper.get('#filter-condition').setValue('5')
    await wrapper.get('#filter-purpose').setValue('6')
    await wrapper.get('#filter-climate').setValue('9')
    await wrapper.get('#filter-tracking').setValue('individual')
    const extra: ItemFilters = { condition_id: 5, purpose_id: 6, climate_id: 9, tracking_mode: 'individual' }
    await vi.waitFor(() => expect(get).toHaveBeenCalledWith('/api/items', { params: { query: { ...extra, category_id: 20 } } }))
    await router.push('/catalog/categories/30')
    await vi.waitFor(() => expect(get).toHaveBeenCalledWith('/api/items', { params: { query: { ...extra, category_id: 30 } } }))
    await wrapper.get('.catalog-filters button').trigger('click')
    await vi.waitFor(() => expect(get).toHaveBeenCalledWith('/api/items', { params: { query: { category_id: 30 } } }))
  })
  it('does not treat fixed category alone as an active user filter', async () => {
    backend(true)
    const { wrapper } = await screen('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.text()).toContain('В этой категории пока нет вещей.'))
    await wrapper.get('#filter-purpose').setValue('6')
    await vi.waitFor(() => expect(wrapper.text()).toContain('По выбранным фильтрам ничего не найдено.'))
  })
})

describe('item removal UX', () => {
  it('requires confirmation and cancel performs no DELETE', async () => {
    backend()
    const deletion = vi.spyOn(apiClient, 'DELETE')
    const { wrapper } = await screen('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe(item.name))
    await wrapper.get('.management-action').trigger('click')
    const confirmation = wrapper.get('.confirmation')
    expect(confirmation.text()).toContain(`Убрать «${item.name}» из текущего каталога?`)
    expect(confirmation.text()).toContain('Запись и её данные сохранятся.')
    await confirmation.findAll('button')[0].trigger('click')
    expect(wrapper.find('.confirmation').exists()).toBe(false)
    expect(deletion).not.toHaveBeenCalled()
  })
  it('blocks repeats while pending, refetches inactive details and invalidates lists', async () => {
    const { state, get } = backend()
    let finish!: () => void
    const deletion = vi.spyOn(apiClient, 'DELETE').mockImplementation(async () => {
      await new Promise<void>((resolve) => { finish = resolve })
      state.item.is_active = false
      return { data: undefined, response: new Response(null, { status: 204 }) }
    })
    const { wrapper, router } = await screen('/catalog')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    await router.push('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe(item.name))
    await wrapper.get('.management-action').trigger('click')
    await wrapper.get('.confirmation').findAll('button')[1].trigger('click')
    await vi.waitFor(() => expect(deletion).toHaveBeenCalledTimes(1))
    expect(wrapper.get('.confirmation').findAll('button').every((button) => button.attributes('disabled') !== undefined)).toBe(true)
    await wrapper.get('.confirmation').findAll('button')[1].trigger('click')
    expect(deletion).toHaveBeenCalledTimes(1)
    expect(deletion).toHaveBeenCalledWith('/api/items/{item_id}', { params: { path: { item_id: 1 } } })
    finish()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Не в текущем каталоге'))
    expect(wrapper.find('.management-action').exists()).toBe(false)
    expect(wrapper.find('a[href="/catalog/items/1/edit"]').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('Восстановить')
    expect(router.currentRoute.value.path).toBe('/catalog/items/1')
    expect(get.mock.calls.filter((call) => call[0] === '/api/items/{item_id}')).toHaveLength(2)
    await router.push('/catalog')
    await vi.waitFor(() => expect(wrapper.text()).toContain('В каталоге пока нет вещей.'))
    expect(get.mock.calls.filter((call) => call[0] === '/api/items')).toHaveLength(2)
  })
  it('does not offer removal or restore for inactive items', async () => {
    const { state } = backend()
    state.item.is_active = false
    const { wrapper } = await screen('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Не в текущем каталоге'))
    expect(wrapper.find('.management-action').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Восстановить')
    expect(wrapper.find('a[href="/catalog/items/1/edit"]').exists()).toBe(true)
  })
  it('keeps details visible and shows a safe DELETE error', async () => {
    backend()
    vi.spyOn(apiClient, 'DELETE').mockRejectedValue(new Error('SQL secret'))
    const { wrapper } = await screen('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe(item.name))
    await wrapper.get('.management-action').trigger('click')
    await wrapper.get('.confirmation').findAll('button')[1].trigger('click')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось убрать вещь из каталога.'))
    expect(wrapper.get('h1').text()).toBe(item.name)
    expect(wrapper.find('dl').exists()).toBe(true)
    expect(wrapper.text()).not.toContain('secret')
  })
})

describe('category CRUD navigation', () => {
  it.each([null, 20])('creates a category with parent %s and refetches tree before navigation', async (parent) => {
    const { state, get } = backend()
    const post = vi.spyOn(apiClient, 'POST').mockImplementation(async (_path, options) => {
      const body = options!.body as CategoryCreate
      const created = { ...body, parent_id: body.parent_id ?? null, id: 50, children: [] }
      if (parent === null) state.categories.push(created)
      else state.categories[0].children![0].children!.push(created)
      return { data: created, response: new Response(null, { status: 201 }) }
    })
    const { wrapper, router } = await screen(parent === null ? '/catalog' : '/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    await wrapper.get(`a[href="${parent === null ? '/catalog/categories/new' : '/catalog/categories/new?parent_id=20'}"]`).trigger('click')
    await vi.waitFor(() => expect(wrapper.find('.category-form').exists()).toBe(true))
    await wrapper.get('#category-name').setValue(' Новая категория ')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog/categories/50'))
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Новая категория'))
    expect(post).toHaveBeenCalledWith('/api/categories', { body: { name: 'Новая категория', parent_id: parent, sort_order: 0 } })
    expect(get.mock.calls.filter((call) => call[0] === '/api/categories')).toHaveLength(2)
    if (parent !== null) expect(wrapper.get('nav a[href="/catalog/categories/20"]').text()).toBe('Ветка B')
  })
  it('renames, reparents and changes sort order; navigation reflects refetched tree', async () => {
    const { state, get } = backend()
    const patch = vi.spyOn(apiClient, 'PATCH').mockImplementation(async (_path, options) => {
      const body = (options as { body: CategoryPatch }).body
      const changed = { ...state.categories[0].children![0], ...body,
        name: body.name!, parent_id: body.parent_id ?? null, sort_order: body.sort_order! }
      state.categories[0].children = []
      state.categories[1].children = [changed]
      return { data: changed, response: new Response() }
    })
    const { wrapper, router } = await screen('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Ветка B'))
    await wrapper.get('a[href="/catalog/categories/20/edit"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('#category-name').setValue('Переименованная')
    await wrapper.get('#category-parent').setValue('40')
    await wrapper.get('#category-order').setValue('2')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog/categories/20'))
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Переименованная'))
    expect(wrapper.get('nav a[href="/catalog/categories/40"]').text()).toBe('Корень D')
    expect(wrapper.find('nav a[href="/catalog/categories/10"]').exists()).toBe(false)
    expect(patch).toHaveBeenCalledWith('/api/categories/{category_id}', { params: { path: { category_id: 20 } },
      body: { name: 'Переименованная', parent_id: 40, sort_order: 2 } })
    expect(get.mock.calls.filter((call) => call[0] === '/api/categories')).toHaveLength(2)
  })
  it.each([
    ['category_cycle', 'Нельзя переместить категорию внутрь самой себя или её подкатегории.'],
    ['category_not_found', 'Категория не найдена.'],
    ['category_parent_not_found', 'Родительская категория больше не существует.'],
    ['unknown', 'Не удалось сохранить категорию.'],
  ])('shows safe save error %s', async (code, message) => {
    backend()
    const failure = { error: { error: { code, message: 'SQL secret' }, detail: [] }, response: new Response(null, { status: 409 }) }
    vi.spyOn(apiClient, 'PATCH').mockResolvedValue(failure)
    const { wrapper, router } = await screen('/catalog/categories/20/edit')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe(message))
    expect(wrapper.text()).not.toContain('secret')
    expect(router.currentRoute.value.path).toBe('/catalog/categories/20/edit')
  })
  it.each(['abc', '0', '9007199254740992'])('rejects invalid edit ID %s without query', async (id) => {
    const { get } = backend()
    const { wrapper } = await screen(`/catalog/categories/${id}/edit`)
    expect(wrapper.get('h1').text()).toBe('Категория не найдена')
    expect(get).not.toHaveBeenCalled()
  })
  it('shows unknown edit category using only existing tree endpoint', async () => {
    const { get } = backend()
    const { wrapper } = await screen('/catalog/categories/999/edit')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Категория не найдена'))
    expect(get).toHaveBeenCalledExactlyOnceWith('/api/categories')
  })
})

describe('category delete confirmation', () => {
  it('requires confirmation and cancel has no cascade or DELETE', async () => {
    backend()
    const deletion = vi.spyOn(apiClient, 'DELETE')
    const { wrapper } = await screen('/catalog/categories/40/edit')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('.management-action').trigger('click')
    expect(wrapper.get('.confirmation').text()).toContain('Категория удалится только если не содержит подкатегорий и не используется вещами или ревизиями.')
    await wrapper.get('.confirmation').findAll('button')[0].trigger('click')
    expect(wrapper.find('.confirmation').exists()).toBe(false)
    expect(deletion).not.toHaveBeenCalled()
  })
  it('blocks pending repeats, deletes exactly one category and refreshes roots', async () => {
    const { state, get } = backend()
    let finish!: () => void
    const deletion = vi.spyOn(apiClient, 'DELETE').mockImplementation(async () => {
      await new Promise<void>((resolve) => { finish = resolve })
      state.categories = state.categories.filter((entry) => entry.id !== 40)
      return { data: undefined, response: new Response(null, { status: 204 }) }
    })
    const { wrapper, router } = await screen('/catalog/categories/40/edit')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('.management-action').trigger('click')
    await wrapper.get('.confirmation').findAll('button')[1].trigger('click')
    await vi.waitFor(() => expect(deletion).toHaveBeenCalledTimes(1))
    expect(wrapper.get('.confirmation').findAll('button').every((button) => button.attributes('disabled') !== undefined)).toBe(true)
    await wrapper.get('.confirmation').findAll('button')[1].trigger('click')
    expect(deletion).toHaveBeenCalledTimes(1)
    finish()
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog'))
    await vi.waitFor(() => expect(wrapper.findAll('.category-links a').map((link) => link.text())).toEqual(['Корень A']))
    expect(deletion).toHaveBeenCalledExactlyOnceWith('/api/categories/{category_id}', { params: { path: { category_id: 40 } } })
    expect(get.mock.calls.filter((call) => call[0] === '/api/categories')).toHaveLength(2)
  })
  it.each([
    ['category_in_use', 'Категорию нельзя удалить, пока она используется или содержит подкатегории.'],
    ['unknown', 'Не удалось удалить категорию.'],
  ])('shows safe delete error %s without cascading requests', async (code, message) => {
    backend()
    const deletion = vi.spyOn(apiClient, 'DELETE').mockResolvedValue({ error: { error: { code, message: 'SQL secret' }, detail: [] }, response: new Response(null, { status: 409 }) })
    const patch = vi.spyOn(apiClient, 'PATCH')
    const { wrapper, router } = await screen('/catalog/categories/40/edit')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('.management-action').trigger('click')
    await wrapper.get('.confirmation').findAll('button')[1].trigger('click')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe(message))
    expect(wrapper.text()).not.toContain('secret')
    expect(deletion).toHaveBeenCalledTimes(1)
    expect(patch).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/catalog/categories/40/edit')
  })
})
