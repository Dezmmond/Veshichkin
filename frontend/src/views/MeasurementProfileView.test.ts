import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { RouterView, createMemoryHistory, createRouter } from 'vue-router'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { routes } from '../router'
import { apiClient } from '../api/client'
import { emptyProfile, profile } from '../features/profile/fixtures.test-support'
import type { MeasurementProfilePatch } from '../api/profile'

const cleanups: (() => void)[] = []
afterEach(() => { cleanups.splice(0).forEach((fn) => fn()); vi.restoreAllMocks() })

async function screen() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  await router.push('/profile/measurements')
  await router.isReady()
  const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity } } })
  const wrapper = mount(RouterView, { global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } })
  cleanups.push(() => { wrapper.unmount(); queryClient.clear() })
  return { wrapper, router }
}

describe('measurement profile screen', () => {
  it('shows loading', async () => {
    vi.spyOn(apiClient, 'GET').mockReturnValue(new Promise<never>(() => {}))
    const { wrapper } = await screen()
    expect(wrapper.get('h1').text()).toBe('Мои замеры')
    expect(wrapper.get('[role="status"]').text()).toBe('Загрузка замеров…')
  })
  it('shows safe GET error and never confuses it with null', async () => {
    vi.spyOn(apiClient, 'GET').mockRejectedValue(new Error('SQL secret Traceback'))
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось загрузить замеры.'))
    expect(wrapper.text()).not.toContain('secret')
    expect(wrapper.text()).not.toContain('Замеры пока не сохранены.')
    expect(wrapper.find('form').exists()).toBe(false)
  })
  it('shows normal null state, opens first-fill form and cancels without mutation', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: null, response: new Response() })
    const patch = vi.spyOn(apiClient, 'PATCH')
    const { wrapper, router } = await screen()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Замеры пока не сохранены.'))
    expect(patch).not.toHaveBeenCalled()
    expect(wrapper.get('button').text()).toBe('Заполнить замеры')
    await wrapper.get('button').trigger('click')
    expect(wrapper.find('form').exists()).toBe(true)
    await wrapper.get('#measurement-foot_length_cm').setValue('27.4')
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('Замеры пока не сохранены.')
    expect(patch).not.toHaveBeenCalled()
    expect(router.currentRoute.value.path).toBe('/profile/measurements')
  })
  it('shows only non-null values with units and readable extra object', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('dl').exists()).toBe(true))
    expect(wrapper.findAll('dt').map((entry) => entry.text())).toEqual(['Рост', 'Вес', 'Длина стопы'])
    expect(wrapper.findAll('dd').map((entry) => entry.text())).toEqual(['182.00 см', '78.50 кг', '27.40 см'])
    expect(wrapper.get('pre').text()).toBe('{\n  "neck_cm": 39\n}')
    expect(wrapper.get('button').text()).toBe('Редактировать')
    expect(wrapper.text()).not.toContain('Обхват талии')
  })
  it('distinguishes empty existing singleton from null and permits editing', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: emptyProfile, response: new Response() })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.text()).toContain('Замеры пока не заполнены.'))
    expect(wrapper.text()).not.toContain('Замеры пока не сохранены.')
    expect(wrapper.find('dl').exists()).toBe(false)
    expect(wrapper.find('pre').exists()).toBe(false)
    expect(wrapper.get('button').text()).toBe('Редактировать')
    await wrapper.get('button').trigger('click')
    expect(wrapper.find('form').exists()).toBe(true)
  })
  it('shows extra-only profile without empty-content message', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: { ...emptyProfile, extra_measurements: { neck_cm: 39 } }, response: new Response() })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('pre').exists()).toBe(true))
    expect(wrapper.text()).not.toContain('Замеры пока не заполнены.')
    expect(wrapper.find('dl').exists()).toBe(false)
  })
  it('creates singleton from one field, invalidates/refetches and returns to view', async () => {
    const get = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: null, response: new Response() })
    const saved = { ...emptyProfile, foot_length_cm: '0.01' }
    const patch = vi.spyOn(apiClient, 'PATCH').mockImplementation(async () => {
      get.mockResolvedValue({ data: saved, response: new Response() })
      return { data: saved, response: new Response() }
    })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('button').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    await wrapper.get('#measurement-foot_length_cm').setValue('0.01')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.findAll('dd').map((entry) => entry.text())).toEqual(['0.01 см']))
    expect(wrapper.find('form').exists()).toBe(false)
    expect(get).toHaveBeenCalledTimes(2)
    expect(patch).toHaveBeenCalledExactlyOnceWith('/api/profile/measurements', { body: {
      height_cm: null, weight_kg: null, chest_cm: null, waist_cm: null, hips_cm: null,
      inseam_cm: null, foot_length_cm: '0.01', extra_measurements: {},
    } })
  })
  it('edits initial strings, clears a numeric field and custom object, then displays refetched values', async () => {
    const get = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    const saved = { ...profile, height_cm: '183.25', weight_kg: null, extra_measurements: {} }
    const patch = vi.spyOn(apiClient, 'PATCH').mockImplementation(async () => {
      get.mockResolvedValue({ data: saved, response: new Response() })
      return { data: saved, response: new Response() }
    })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('dl').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    expect((wrapper.get('#measurement-height_cm').element as HTMLInputElement).value).toBe('182.00')
    await wrapper.get('#measurement-height_cm').setValue('183.25')
    await wrapper.get('#measurement-weight_kg').setValue('')
    await wrapper.get('#measurement-extra').setValue('{}')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.findAll('dd').map((entry) => entry.text())).toEqual(['183.25 см', '27.40 см']))
    expect(patch).toHaveBeenCalledWith('/api/profile/measurements', { body: expect.objectContaining({ height_cm: '183.25', weight_kg: null, extra_measurements: {} }) })
    expect(get).toHaveBeenCalledTimes(2)
    expect(wrapper.find('pre').exists()).toBe(false)
    await wrapper.get('button').trigger('click')
    expect((wrapper.get('#measurement-height_cm').element as HTMLInputElement).value).toBe('183.25')
  })
  it('cancels editing without PATCH and preserves saved view', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    const patch = vi.spyOn(apiClient, 'PATCH')
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('dl').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    await wrapper.get('#measurement-height_cm').setValue('190')
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.findAll('dd').map((entry) => entry.text())).toContain('182.00 см')
    expect(patch).not.toHaveBeenCalled()
    await wrapper.get('button').trigger('click')
    expect((wrapper.get('#measurement-height_cm').element as HTMLInputElement).value).toBe('182.00')
  })
  it('blocks repeated submit and cancel until PATCH and refetch finish', async () => {
    const get = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    let finishPatch!: () => void
    let finishGet!: () => void
    const saved = { ...profile, height_cm: '185.01' }
    const patch = vi.spyOn(apiClient, 'PATCH').mockImplementation(async () => {
      await new Promise<void>((resolve) => { finishPatch = resolve })
      get.mockImplementation(async () => {
        await new Promise<void>((resolve) => { finishGet = resolve })
        return { data: saved, response: new Response() }
      })
      return { data: saved, response: new Response() }
    })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('dl').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    await wrapper.get('#measurement-height_cm').setValue('185.01')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(patch).toHaveBeenCalledTimes(1))
    expect(wrapper.findAll('button').every((button) => button.attributes('disabled') !== undefined)).toBe(true)
    await wrapper.get('form').trigger('submit')
    await wrapper.findAll('button')[1].trigger('click')
    expect(patch).toHaveBeenCalledTimes(1)
    expect(wrapper.find('form').exists()).toBe(true)
    finishPatch()
    await vi.waitFor(() => expect(get).toHaveBeenCalledTimes(2))
    expect(wrapper.find('form').exists()).toBe(true)
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    finishGet()
    await vi.waitFor(() => expect(wrapper.findAll('dd').map((entry) => entry.text())).toContain('185.01 см'))
  })
  it('keeps form values after mutation error and allows retry', async () => {
    const get = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    const patch = vi.spyOn(apiClient, 'PATCH').mockRejectedValue(new Error('SQL secret Traceback'))
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('dl').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    await wrapper.get('#measurement-height_cm').setValue('187.05')
    await wrapper.get('#measurement-extra').setValue('{"neck_cm":40}')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('Не удалось сохранить замеры.'))
    expect((wrapper.get('#measurement-height_cm').element as HTMLInputElement).value).toBe('187.05')
    expect((wrapper.get('#measurement-extra').element as HTMLTextAreaElement).value).toBe('{"neck_cm":40}')
    expect(wrapper.text()).not.toContain('secret')
    expect(get).toHaveBeenCalledTimes(1)
    const saved = { ...profile, height_cm: '187.05', extra_measurements: { neck_cm: 40 } }
    patch.mockImplementation(async () => {
      get.mockResolvedValue({ data: saved, response: new Response() })
      return { data: saved, response: new Response() }
    })
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.findAll('dd').map((entry) => entry.text())).toContain('187.05 см'))
    expect(patch).toHaveBeenCalledTimes(2)
  })
  it('does not send invalid JSON to backend', async () => {
    vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: null, response: new Response() })
    const patch = vi.spyOn(apiClient, 'PATCH')
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('button').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    await wrapper.get('#measurement-extra').setValue('{bad')
    await wrapper.get('form').trigger('submit')
    expect(patch).not.toHaveBeenCalled()
    expect(wrapper.get('[role="alert"]').text()).toContain('JSON-объектом')
  })
  it('sends custom measurements as a full replacement object', async () => {
    const get = vi.spyOn(apiClient, 'GET').mockResolvedValue({ data: profile, response: new Response() })
    const saved = { ...profile, extra_measurements: { shoulder_width_cm: 47 } }
    const patch = vi.spyOn(apiClient, 'PATCH').mockImplementation(async () => {
      get.mockResolvedValue({ data: saved, response: new Response() })
      return { data: saved, response: new Response() }
    })
    const { wrapper } = await screen()
    await vi.waitFor(() => expect(wrapper.find('dl').exists()).toBe(true))
    await wrapper.get('button').trigger('click')
    await wrapper.get('#measurement-extra').setValue('{"shoulder_width_cm":47}')
    await wrapper.get('form').trigger('submit')
    await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(false))
    expect(wrapper.get('pre').text()).toContain('"shoulder_width_cm": 47')
    expect(wrapper.get('pre').text()).not.toContain('neck_cm')
    const request = patch.mock.calls[0] as unknown as [string, { body: MeasurementProfilePatch }]
    expect(request[1].body.extra_measurements).toEqual({ shoulder_width_cm: 47 })
  })
})
