import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import HomeView from './HomeView.vue'
import { apiClient } from '../api/client'

afterEach(() => vi.restoreAllMocks())

function mountHome() {
  const queryClient = new QueryClient()
  const wrapper = mount(HomeView, {
    global: { plugins: [[VueQueryPlugin, { queryClient }]] },
  })
  return { wrapper, queryClient }
}

describe('Home backend status', () => {
  it('shows loading while the request is pending', () => {
    vi.spyOn(apiClient, 'GET').mockReturnValue(new Promise<never>(() => {}))
    const { wrapper, queryClient } = mountHome()
    try {
      expect(wrapper.get('[role="status"]').text()).toBe('Backend: проверка…')
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })

  it('shows available after a successful query', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockResolvedValue({
      data: { status: 'ok' }, response: new Response(null, { status: 200 }),
    })
    const { wrapper, queryClient } = mountHome()
    try {
      await vi.waitFor(() => expect(wrapper.get('[role="status"]').text()).toBe('Backend: доступен'))
      expect(request).toHaveBeenCalledExactlyOnceWith('/api/health')
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })

  it('shows unavailable without exposing internal error details or retrying', async () => {
    const request = vi.spyOn(apiClient, 'GET').mockRejectedValue(
      new Error('Traceback: private-host secret-password'),
    )
    const { wrapper, queryClient } = mountHome()
    try {
      await vi.waitFor(() => expect(wrapper.get('[role="status"]').text()).toBe('Backend: недоступен'))
      expect(wrapper.text()).not.toContain('Traceback')
      expect(wrapper.text()).not.toContain('secret-password')
      expect(request).toHaveBeenCalledTimes(1)
    } finally {
      wrapper.unmount()
      queryClient.clear()
    }
  })
})
