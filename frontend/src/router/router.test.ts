import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { RouterView, createMemoryHistory, createRouter } from 'vue-router'
import { routes } from './index'

describe('routes', () => {
  it.each([
    ['/', 'home', 'Veshichkin'],
    ['/catalog', 'catalog', 'Каталог'],
    ['/revision', 'revision', 'Ревизия'],
    ['/unknown/nested-page', 'not-found', 'Страница не найдена'],
  ])('renders %s', async (path, name, heading) => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    await router.push(path)
    await router.isReady()
    const wrapper = mount(RouterView, { global: { plugins: [router] } })
    try {
      expect(router.currentRoute.value.name).toBe(name)
      expect(wrapper.get('h1').text()).toBe(heading)
    } finally {
      wrapper.unmount()
    }
  })
})
