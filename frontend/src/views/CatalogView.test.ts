import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { RouterView, createMemoryHistory, createRouter } from 'vue-router'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { routes } from '../router'
import { apiClient } from '../api/client'
import { tree, item, conditions, purposes, climates } from '../features/catalog/fixtures.test-support'

const cleanups: (() => void)[] = []
afterEach(() => {
  cleanups.splice(0).forEach((cleanup) => cleanup())
  vi.restoreAllMocks()
})

function mockCatalog(options: { emptyRoots?: boolean; emptyItems?: boolean; fail?: string; pending?: string } = {}) {
  return vi.spyOn(apiClient, 'GET').mockImplementation(async (path) => {
    if (path === options.pending) return new Promise<never>(() => {})
    if (path === options.fail) throw new Error('Traceback private SQL secret')
    const data = path === '/api/categories' ? options.emptyRoots ? [] : tree
      : path === '/api/items' ? options.emptyItems ? [] : [item]
      : path === '/api/reference/conditions' ? conditions
      : path === '/api/reference/purposes' ? purposes : climates
    return { data, response: new Response() }
  })
}

async function mountRoute(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push(path)
  await router.isReady()
  const queryClient = new QueryClient()
  const wrapper = mount(RouterView, { global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } })
  cleanups.push(() => { wrapper.unmount(); queryClient.clear() })
  return { wrapper, router }
}

describe('catalog root', () => {
  it('shows loading', async () => {
    mockCatalog({ pending: '/api/categories' })
    const { wrapper } = await mountRoute('/catalog')
    expect(wrapper.get('[role="status"]').text()).toBe('Загрузка каталога…')
  })
  it('shows only roots in backend order with category links', async () => {
    mockCatalog()
    const { wrapper } = await mountRoute('/catalog')
    await vi.waitFor(() => expect(wrapper.findAll('.category-links a')).toHaveLength(2))
    expect(wrapper.findAll('.category-links a').map((link) => [link.text(), link.attributes('href')]))
      .toEqual([['Корень A', '/catalog/categories/10'], ['Корень D', '/catalog/categories/40']])
    expect(wrapper.text()).not.toContain('Ветка B')
  })
  it('shows empty categories', async () => {
    mockCatalog({ emptyRoots: true })
    const { wrapper } = await mountRoute('/catalog')
    await vi.waitFor(() => expect(wrapper.text()).toContain('Категории пока отсутствуют.'))
  })
  it('shows a safe API error', async () => {
    mockCatalog({ fail: '/api/categories' })
    const { wrapper } = await mountRoute('/catalog')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось загрузить каталог.'))
    expect(wrapper.text()).not.toContain('secret')
  })
})

describe('category screen', () => {
  it('shows breadcrumb, immediate children, exact-category items and readable metadata', async () => {
    const request = mockCatalog()
    const { wrapper } = await mountRoute('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    expect(wrapper.get('h1').text()).toBe('Ветка B')
    const breadcrumb = wrapper.get('nav[aria-label="Путь категории"]')
    expect(breadcrumb.findAll('li').map((entry) => entry.text())).toEqual(['Каталог', 'Корень A', 'Ветка B'])
    expect(breadcrumb.get('a[href="/catalog"]').text()).toBe('Каталог')
    expect(breadcrumb.get('a[href="/catalog/categories/10"]').text()).toBe('Корень A')
    expect(breadcrumb.get('[aria-current="page"]').text()).toBe('Ветка B')
    expect(wrapper.get('.category-links a').attributes('href')).toBe('/catalog/categories/30')
    expect(wrapper.get('.category-links a').text()).toBe('Лист C')
    expect(request).toHaveBeenCalledWith('/api/items', { params: { query: { category_id: 20 } } })
    const card = wrapper.get('.catalog-item')
    expect(card.get('h3').text()).toBe('Набор вещей')
    expect(card.findAll('dd').map((entry) => entry.text())).toEqual([
      'Группа', '7', 'Хорошее', 'Прогулки, Работа', 'Тёплый', 'Brand', 'Model', 'Синий', 'M', 'Хлопок',
    ])
    expect(card.find('a').exists()).toBe(false)
  })
  it('updates item filters and breadcrumb when route category changes, reusing the tree', async () => {
    const request = mockCatalog()
    const { wrapper, router } = await mountRoute('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    await router.push('/catalog/categories/30')
    await vi.waitFor(() => expect(request).toHaveBeenCalledWith('/api/items', { params: { query: { category_id: 30 } } }))
    expect(wrapper.get('h1').text()).toBe('Лист C')
    expect(wrapper.get('nav').findAll('li').map((entry) => entry.text())).toEqual(['Каталог', 'Корень A', 'Ветка B', 'Лист C'])
    expect(wrapper.get('nav a[href="/catalog/categories/20"]').text()).toBe('Ветка B')
    expect(wrapper.find('.category-links').exists()).toBe(false)
    expect(request.mock.calls.filter((call) => call[0] === '/api/categories')).toHaveLength(1)
  })
  it('shows empty items', async () => {
    mockCatalog({ emptyItems: true })
    const { wrapper } = await mountRoute('/catalog/categories/40')
    await vi.waitFor(() => expect(wrapper.text()).toContain('В этой категории пока нет вещей.'))
    expect(wrapper.find('.category-links').exists()).toBe(false)
  })
  it('shows individual items with absent references and optional metadata', async () => {
    mockCatalog().mockImplementation(async (path) => ({
      data: path === '/api/categories' ? tree : path === '/api/items'
        ? [{ ...item, tracking_mode: 'individual' as const, quantity: 1, condition_id: null,
          purpose_ids: [], climate_ids: [], brand: null, model: null, color: null, size: null, material: null }]
        : [],
      response: new Response(),
    }))
    const { wrapper } = await mountRoute('/catalog/categories/20')
    await vi.waitFor(() => expect(wrapper.find('.catalog-item').exists()).toBe(true))
    expect(wrapper.get('.catalog-item').findAll('dd').map((entry) => entry.text()))
      .toEqual(['Индивидуальная', '1', 'Не указано', 'Не указаны', 'Не указаны'])
  })
  it('shows unknown category without item/reference requests', async () => {
    const request = mockCatalog()
    const { wrapper } = await mountRoute('/catalog/categories/999')
    await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Категория не найдена'))
    expect(wrapper.get('a').attributes('href')).toBe('/catalog')
    expect(request).toHaveBeenCalledExactlyOnceWith('/api/categories')
  })
  it.each(['0', '-1', 'abc', '1.5', '9007199254740992'])('rejects invalid ID %s without API requests', async (id) => {
    const request = mockCatalog()
    const { wrapper } = await mountRoute(`/catalog/categories/${id}`)
    expect(wrapper.get('h1').text()).toBe('Категория не найдена')
    expect(request).not.toHaveBeenCalled()
  })
  it.each(['/api/categories', '/api/items', '/api/reference/conditions', '/api/reference/purposes', '/api/reference/climates'])(
    'shows safe error for %s', async (fail) => {
      mockCatalog({ fail })
      const { wrapper } = await mountRoute('/catalog/categories/20')
      await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось загрузить каталог.'))
      expect(wrapper.text()).not.toContain('Traceback')
      expect(wrapper.text()).not.toContain('secret')
    },
  )
  it.each(['/api/categories', '/api/items', '/api/reference/conditions', '/api/reference/purposes', '/api/reference/climates'])(
    'shows loading while waiting for %s', async (pending) => {
      mockCatalog({ pending })
      const { wrapper } = await mountRoute('/catalog/categories/20')
      if (pending !== '/api/categories') {
        await vi.waitFor(() => expect(wrapper.get('h1').text()).toBe('Ветка B'))
      }
      await vi.waitFor(() => expect(wrapper.find('[role="status"]').exists()).toBe(true))
      expect(wrapper.get('[role="status"]').text()).toBe('Загрузка каталога…')
      expect(wrapper.find('.catalog-item').exists()).toBe(false)
    },
  )
})
