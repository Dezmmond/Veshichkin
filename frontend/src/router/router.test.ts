import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { mount } from '@vue/test-utils'
import { RouterView, createMemoryHistory, createRouter } from 'vue-router'
import { routes } from './index'
import { apiClient } from '../api/client'

beforeEach(() => {
  vi.spyOn(apiClient, 'GET').mockImplementation(async (path) => ({
    data: path === '/api/health' ? { status: 'ok' as const } : [],
    response: new Response(null, { status: 200 }),
  }))
})

afterEach(() => vi.restoreAllMocks())

describe('routes', () => {
  it.each([
    ['/', 'home', 'Veshichkin'],
    ['/catalog', 'catalog', 'Каталог'],
    ['/catalog/categories/invalid', 'category', 'Категория не найдена'],
    ['/revision', 'revision', 'Ревизия'],
    ['/unknown/nested-page', 'not-found', 'Страница не найдена'],
  ])('renders %s', async (path, name, heading) => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push(path)
    await router.isReady()
    const queryClient = new QueryClient()
    const wrapper = mount(RouterView, {
      global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
    })
    try {
      expect(router.currentRoute.value.name).toBe(name)
      expect(wrapper.get('h1').text()).toBe(heading)
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })
})
