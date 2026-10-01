import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { RouterView, createMemoryHistory, createRouter } from 'vue-router'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { routes } from '../router'
import { apiClient } from '../api/client'
import { tree, item, conditions, purposes, climates } from '../features/catalog/fixtures.test-support'
import type { components } from '../api/generated/schema'
import type { ItemCreate, ItemPatch } from '../api/items'

const cleanups: (() => void)[] = []
afterEach(() => { cleanups.splice(0).forEach((fn) => fn()); vi.restoreAllMocks() })

function mockApi(options: { value?: components['schemas']['ItemResponse']; fail?: string; pending?: string; notFound?: boolean } = {}) {
  return vi.spyOn(apiClient, 'GET').mockImplementation(async (path) => {
    if (path === options.pending) return new Promise<never>(() => {})
    if (path === options.fail) throw new Error('private SQL secret')
    if (options.notFound && path === '/api/items/{item_id}') return { response: new Response(null, { status: 404 }) }
    const value = options.value ?? item
    return { data: path === '/api/items/{item_id}' ? value : path === '/api/items' ? [value]
      : path === '/api/categories' ? tree : path === '/api/reference/conditions' ? conditions
      : path === '/api/reference/purposes' ? purposes : climates,
    response: new Response() }
  })
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

describe('item details', () => {
  it('shows category/reference names, grouped quantity, all attributes, inactive status and edit link', async () => {
    mockApi({ value: { ...item, notes: 'Подробная заметка', extra_attributes: { volume_l: 35 }, is_active: false } })
    const { wrapper } = await screen('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Набор вещей'))
    expect(wrapper.findAll('dd').map((entry) => entry.text())).toEqual([
      'Ветка B', 'Группа одинаковых вещей', '7', 'Хорошее', 'Прогулки, Работа', 'Тёплый',
      'Brand', 'Model', 'Синий', 'M', 'Хлопок', 'Подробная заметка', '{\n  "volume_l": 35\n}',
    ])
    expect(wrapper.get('[role="status"]').text()).toBe('Не в текущем каталоге')
    expect(wrapper.get('a[href="/catalog/items/1/edit"]').text()).toBe('Редактировать')
    expect(wrapper.get('a[href="/catalog/categories/20"]').text()).toBe('Ветка B')
  })
  it('shows individual details without grouped quantity or inactive status', async () => {
    mockApi({ value: { ...item, tracking_mode: 'individual', quantity: 1 } })
    const { wrapper } = await screen('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe(item.name))
    expect(wrapper.text()).toContain('Индивидуальная вещь')
    expect(wrapper.text()).not.toContain('Количество')
    expect(wrapper.text()).not.toContain('Не в текущем каталоге')
  })
  it.each(['/api/items/{item_id}', '/api/categories', '/api/reference/conditions', '/api/reference/purposes', '/api/reference/climates'])(
    'shows loading for %s', async (pending) => {
      const request = mockApi({ pending })
      const { wrapper } = await screen('/catalog/items/1')
      if (pending !== '/api/items/{item_id}') {
        await vi.waitFor(() => expect(request).toHaveBeenCalledWith(pending))
      }
      await vi.waitFor(() => expect(wrapper.find('[role="status"]').exists()).toBe(true))
      expect(wrapper.get('[role="status"]').text()).toBe('Загрузка вещи…')
      expect(wrapper.find('dl').exists()).toBe(false)
    },
  )
  it.each(['/api/items/{item_id}', '/api/categories', '/api/reference/conditions', '/api/reference/purposes', '/api/reference/climates'])(
    'shows safe error for %s', async (fail) => {
      mockApi({ fail })
      const { wrapper } = await screen('/catalog/items/1')
      await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось загрузить вещь.'))
      expect(wrapper.text()).not.toContain('secret')
    },
  )
  it('shows 404 with return link without reference requests', async () => {
    const request = mockApi({ notFound: true })
    const { wrapper } = await screen('/catalog/items/999')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Вещь не найдена'))
    expect(wrapper.get('a').attributes('href')).toBe('/catalog')
    expect(request).toHaveBeenCalledTimes(1)
  })
  it.each(['0', '-1', 'abc', '1.5', '9007199254740992'])('rejects invalid details ID %s without API', async (id) => {
    const request = mockApi()
    const { wrapper } = await screen(`/catalog/items/${id}`)
    expect(wrapper.get('h1').text()).toBe('Вещь не найдена')
    expect(request).not.toHaveBeenCalled()
  })
})

describe('write routes and navigation', () => {
  it('creates through category navigation and refreshes cached lists and details', async () => {
    const state = { value: { ...item } }
    const request = mockApi({ value: state.value })
    const post = vi.spyOn(apiClient, 'POST').mockImplementation(async (_path, options) => {
      const body = options!.body as ItemCreate
      state.value = { ...item, ...body, name: body.name, quantity: body.quantity ?? 1 }
      request.mockImplementation(async (path) => ({ data: path === '/api/items/{item_id}' ? state.value
        : path === '/api/items' ? [state.value] : path === '/api/categories' ? tree
        : path === '/api/reference/conditions' ? conditions : path === '/api/reference/purposes' ? purposes : climates,
      response: new Response() }))
      return { data: state.value, response: new Response(null, { status: 201 }) }
    })
    const { wrapper, router } = await screen('/catalog/items/1')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe(item.name))
    await router.push('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    await wrapper.get('a[href="/catalog/items/new?category_id=20"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('#item-name').setValue('Созданная вещь')
    await wrapper.get('#item-condition').setValue('5')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog/items/1'))
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Созданная вещь'))
    expect(post).toHaveBeenCalledTimes(1)
    expect(request.mock.calls.filter((call) => call[0] === '/api/items/{item_id}')).toHaveLength(2)
    await router.push('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.get('.catalog-item h3').text()).toBe('Созданная вещь'))
    expect(request.mock.calls.filter((call) => call[0] === '/api/items')).toHaveLength(2)
  })
  it('updates, refetches cached details and refreshes cached list', async () => {
    const state = { value: { ...item } }
    const request = mockApi({ value: state.value })
    const patch = vi.spyOn(apiClient, 'PATCH').mockImplementation(async (_path, options) => {
      const body = (options as { body: ItemPatch }).body
      state.value = { ...item, ...body, name: body.name ?? item.name,
        category_id: body.category_id ?? item.category_id, quantity: body.quantity ?? item.quantity }
      request.mockImplementation(async (path) => ({ data: path === '/api/items/{item_id}' ? state.value
        : path === '/api/items' ? [state.value] : path === '/api/categories' ? tree
        : path === '/api/reference/conditions' ? conditions : path === '/api/reference/purposes' ? purposes : climates,
      response: new Response() }))
      return { data: state.value, response: new Response() }
    })
    const { wrapper, router } = await screen('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    await wrapper.get('.catalog-item a').trigger('click')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe(item.name))
    await wrapper.get('a[href="/catalog/items/1/edit"]').trigger('click')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('#item-name').setValue('Обновлённая вещь')
    await wrapper.get('#item-quantity').setValue('12')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog/items/1'))
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Обновлённая вещь'))
    expect(wrapper.text()).toContain('12')
    expect(patch).toHaveBeenCalledWith('/api/items/{item_id}', expect.objectContaining({ params: { path: { item_id: 1 } } }))
    expect(request.mock.calls.filter((call) => call[0] === '/api/items/{item_id}')).toHaveLength(2)
    await router.push('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.get('.catalog-item h3').text()).toBe('Обновлённая вещь'))
    expect(request.mock.calls.filter((call) => call[0] === '/api/items')).toHaveLength(2)
  })
  it.each(['create', 'edit'])('shows safe mutation failure for %s and keeps form values', async (mode) => {
    mockApi()
    vi.spyOn(apiClient, 'POST').mockRejectedValue(new Error('SQL secret'))
    vi.spyOn(apiClient, 'PATCH').mockRejectedValue(new Error('SQL secret'))
    const path = mode === 'create' ? '/catalog/items/new?category_id=20' : '/catalog/items/1/edit'
    const { wrapper, router } = await screen(path)
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('#item-name').setValue('Название сохранено')
    await wrapper.get('#item-condition').setValue('5')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось сохранить вещь.'))
    expect(wrapper.text()).not.toContain('secret')
    expect((wrapper.get('#item-name').element as HTMLInputElement).value).toBe('Название сохранено')
    expect(router.currentRoute.value.path).toBe(mode === 'create' ? '/catalog/items/new' : path)
  })
  it.each(['0', 'abc', '9007199254740992'])('rejects invalid edit ID %s', async (id) => {
    const request = mockApi()
    const { wrapper } = await screen(`/catalog/items/${id}/edit`)
    expect(wrapper.get('h1').text()).toBe('Вещь не найдена')
    expect(request).not.toHaveBeenCalled()
  })
  it('shows edit 404', async () => {
    mockApi({ notFound: true })
    const { wrapper } = await screen('/catalog/items/999/edit')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Вещь не найдена'))
  })
  it('shows edit item loading', async () => {
    mockApi({ pending: '/api/items/{item_id}' })
    const { wrapper } = await screen('/catalog/items/1/edit')
    expect(wrapper.get('[role="status"]').text()).toBe('Загрузка вещи…')
  })
  it('shows edit item loading error', async () => {
    mockApi({ fail: '/api/items/{item_id}' })
    const { wrapper } = await screen('/catalog/items/1/edit')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось загрузить вещь.'))
  })
  it.each(['/api/categories', '/api/reference/conditions', '/api/reference/purposes', '/api/reference/climates'])(
    'shows create form data error for %s', async (fail) => {
      mockApi({ fail })
      const { wrapper } = await screen('/catalog/items/new')
      await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось загрузить данные формы.'))
      expect(wrapper.find('form').exists()).toBe(false)
    },
  )
  it('shows create form loading', async () => {
    mockApi({ pending: '/api/categories' })
    const { wrapper } = await screen('/catalog/items/new')
    expect(wrapper.get('[role="status"]').text()).toBe('Загрузка формы…')
  })
  it('ignores invalid preselect query and cancels to catalog', async () => {
    mockApi()
    const { wrapper, router } = await screen('/catalog/items/new?category_id=abc')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    expect((wrapper.get('#item-category').element as HTMLSelectElement).value).toBe('')
    await wrapper.get('a').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog'))
  })
  it('cancels edit back to details', async () => {
    mockApi()
    const { wrapper, router } = await screen('/catalog/items/1/edit')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
    await wrapper.get('a').trigger('click')
    await vi.waitFor(() => expect(router.currentRoute.value.path).toBe('/catalog/items/1'))
  })
})
