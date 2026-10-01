import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { QueryClient, VueQueryPlugin, useQueryClient } from '@tanstack/vue-query'
import PrimeVue, { usePrimeVue } from 'primevue/config'
import App from './App.vue'
import { routes } from './router'
import { apiClient } from './api/client'

beforeEach(() => {
  vi.spyOn(apiClient, 'GET').mockResolvedValue({
    data: { status: 'ok' }, response: new Response(null, { status: 200 }),
  })
})

afterEach(() => vi.restoreAllMocks())

describe('application shell', () => {
  it('mounts with navigation links and changes the active view', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push('/')
    await router.isReady()
    const queryClient = new QueryClient()
    const wrapper = mount(App, {
      global: {
        plugins: [router, [VueQueryPlugin, { queryClient }], [PrimeVue, { unstyled: true }]],
      },
    })
    try {
      const navigation = wrapper.get('nav[aria-label="Основная навигация"]')
      expect(navigation.findAll('a').map((link) => [link.text(), link.attributes('href')])).toEqual([
        ['Главная', '/'], ['Каталог', '/catalog'], ['Ревизия', '/revision'],
      ])
      expect(wrapper.get('h1').text()).toBe('Veshichkin')
      expect(navigation.get('a[href="/"]').attributes('aria-current')).toBe('page')
      await navigation.get('a[href="/catalog"]').trigger('click')
      await flushPromises()
      expect(router.currentRoute.value.path).toBe('/catalog')
      expect(wrapper.get('h1').text()).toBe('Каталог')
      expect(navigation.get('a[href="/catalog"]').classes()).toContain('router-link-exact-active')
      expect(navigation.get('a[href="/catalog"]').attributes('aria-current')).toBe('page')
      expect(navigation.get('a[href="/"]').attributes('aria-current')).toBeUndefined()
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })

  it('provides PrimeVue and Vue Query without creating queries', () => {
    const queryClient = new QueryClient()
    let providedClient: QueryClient | undefined
    let unstyled: boolean | undefined
    const probe = defineComponent({
      setup() {
        providedClient = useQueryClient()
        unstyled = usePrimeVue().config.unstyled
        return () => null
      },
    })
    const wrapper = mount(probe, {
      global: {
        plugins: [[VueQueryPlugin, { queryClient }], [PrimeVue, { unstyled: true }]],
      },
    })
    try {
      expect(providedClient).toBe(queryClient)
      expect(unstyled).toBe(true)
      expect(queryClient.getQueryCache().getAll()).toEqual([])
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })

  it('returns to the home view from an unknown URL', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push('/missing')
    await router.isReady()
    const queryClient = new QueryClient()
    const wrapper = mount(App, {
      global: { plugins: [router, [VueQueryPlugin, { queryClient }]] },
    })
    try {
      expect(wrapper.get('h1').text()).toBe('Страница не найдена')
      await wrapper.get('main a[href="/"]').trigger('click')
      await flushPromises()
      expect(router.currentRoute.value.path).toBe('/')
      expect(wrapper.get('h1').text()).toBe('Veshichkin')
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })
})
