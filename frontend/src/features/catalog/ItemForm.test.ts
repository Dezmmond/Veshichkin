import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { createMemoryHistory, createRouter } from 'vue-router'
import ItemForm from './ItemForm.vue'
import { tree, item, conditions, purposes, climates } from './fixtures.test-support'
import { apiClient } from '../../api/client'
import type { ItemCreate, ItemPatch } from '../../api/items'
import type { components } from '../../api/generated/schema'

const cleanups: (() => void)[] = []
afterEach(() => { cleanups.splice(0).forEach((fn) => fn()); vi.restoreAllMocks() })

async function form(initial?: components['schemas']['ItemResponse'], categoryId: number | undefined = 20) {
  vi.spyOn(apiClient, 'GET').mockImplementation(async (path) => ({
    data: path === '/api/categories' ? tree : path === '/api/reference/conditions' ? conditions
      : path === '/api/reference/purposes' ? purposes : [...climates, { id: 11, name: 'Холодный', code: 'cold', sort_order: 1 }],
    response: new Response(),
  }))
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/:pathMatch(.*)*', component: ItemForm }] })
  await router.push('/form')
  const queryClient = new QueryClient()
  const wrapper = mount(ItemForm, { props: { item: initial, categoryId, pending: false, error: false },
    global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } })
  cleanups.push(() => { wrapper.unmount(); queryClient.clear() })
  await vi.waitFor(() => expect(wrapper.find('form').exists()).toBe(true))
  return wrapper
}
type FormWrapper = Awaited<ReturnType<typeof form>>
async function required(wrapper: FormWrapper) {
  await wrapper.get('#item-name').setValue('  Новая вещь  ')
  await wrapper.get('#item-condition').setValue('5')
}
async function submit(wrapper: FormWrapper) { await wrapper.get('form').trigger('submit') }
function created(wrapper: FormWrapper) { return wrapper.emitted('create')?.[0]?.[0] as ItemCreate }
function updated(wrapper: FormWrapper) { return wrapper.emitted('update')?.[0]?.[0] as ItemPatch }

describe('shared item form', () => {
  it('creates individual without quantity and preselects existing category', async () => {
    const wrapper = await form()
    await required(wrapper)
    expect(wrapper.find('#item-quantity').exists()).toBe(false)
    await submit(wrapper)
    expect(created(wrapper)).toEqual({ name: 'Новая вещь', category_id: 20, tracking_mode: 'individual',
      condition_id: 5, purpose_ids: [], climate_ids: [], extra_attributes: {} })
    expect(wrapper.get('a').attributes('href')).toBe('/catalog/categories/20')
    expect(wrapper.findAll('#item-category option').map((option) => option.text()))
      .toEqual(['Выберите категорию', 'Корень A', '↳ Ветка B', '↳ ↳ Лист C', 'Корень D'])
  })
  it('leaves unknown preselect unselected and cancel returns to catalog', async () => {
    const wrapper = await form(undefined, 999)
    expect((wrapper.get('#item-category').element as HTMLSelectElement).value).toBe('')
    expect(wrapper.get('a').attributes('href')).toBe('/catalog')
    await required(wrapper)
    await submit(wrapper)
    expect(wrapper.emitted('create')).toBeUndefined()
  })
  it.each(['', '-1', '1.5'])('blocks grouped invalid quantity %s', async (quantity) => {
    const wrapper = await form()
    await required(wrapper)
    await wrapper.get('#item-tracking').setValue('grouped')
    await wrapper.get('#item-quantity').setValue(quantity)
    await submit(wrapper)
    expect(wrapper.get('[role="alert"]').text()).toContain('целым числом')
    expect(wrapper.emitted('create')).toBeUndefined()
  })
  it.each([0, 7])('accepts grouped quantity %s', async (quantity) => {
    const wrapper = await form()
    await required(wrapper)
    await wrapper.get('#item-tracking').setValue('grouped')
    await wrapper.get('#item-quantity').setValue(String(quantity))
    await submit(wrapper)
    expect(created(wrapper)).toMatchObject({ tracking_mode: 'grouped', quantity })
  })
  it('sends multiple purposes/climates, scalar values and parsed JSON', async () => {
    const wrapper = await form()
    await required(wrapper)
    for (const selector of ['[data-purpose="6"]', '[data-purpose="8"]', '[data-climate="9"]', '[data-climate="11"]']) {
      await wrapper.get(selector).setValue(true)
    }
    for (const key of ['brand', 'model', 'color', 'size', 'material', 'notes']) {
      await wrapper.get(`#item-${key}`).setValue(` ${key} value `)
    }
    await wrapper.get('#item-extra').setValue('{"waterproof":true,"volume_l":35}')
    await submit(wrapper)
    expect(created(wrapper)).toMatchObject({ purpose_ids: [6, 8], climate_ids: [9, 11],
      brand: 'brand value', model: 'model value', color: 'color value', size: 'size value', material: 'material value',
      notes: 'notes value', extra_attributes: { waterproof: true, volume_l: 35 } })
  })
  it.each(['{invalid', '[]', '"text"', '12', 'null'])('blocks invalid extra JSON %s', async (json) => {
    const wrapper = await form()
    await required(wrapper)
    await wrapper.get('#item-extra').setValue(json)
    await submit(wrapper)
    expect(wrapper.get('[role="alert"]').text()).toContain('JSON-объектом')
    expect(wrapper.emitted('create')).toBeUndefined()
  })
  it.each(['name', 'condition', 'category', 'tracking'])('blocks missing required %s', async (field) => {
    const wrapper = await form()
    await required(wrapper)
    await wrapper.get(`#item-${field}`).setValue(field === 'name' ? '   ' : '')
    await submit(wrapper)
    expect(wrapper.emitted('create')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toContain('Заполните')
  })
  it('prefills edit values with immutable tracking mode and current selections', async () => {
    const wrapper = await form({ ...item, extra_attributes: { sample: true }, notes: 'Заметка' })
    expect((wrapper.get('#item-name').element as HTMLInputElement).value).toBe(item.name)
    expect((wrapper.get('#item-category').element as HTMLSelectElement).value).toBe('20')
    expect((wrapper.get('#item-condition').element as HTMLSelectElement).value).toBe('5')
    expect(wrapper.find('#item-tracking').exists()).toBe(false)
    expect(wrapper.text()).toContain('Группа одинаковых вещей')
    expect((wrapper.get('[data-purpose="6"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.get('[data-purpose="8"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.get('[data-climate="9"]').element as HTMLInputElement).checked).toBe(true)
    expect((wrapper.get('#item-extra').element as HTMLTextAreaElement).value).toContain('"sample": true')
    expect(wrapper.get('a').attributes('href')).toBe('/catalog/items/1')
    await wrapper.get('#item-quantity').setValue('0')
    await submit(wrapper)
    expect(updated(wrapper).quantity).toBe(0)
    expect(updated(wrapper)).not.toHaveProperty('tracking_mode')
    expect(updated(wrapper)).not.toHaveProperty('is_active')
  })
  it('clears scalars with null, replaces relations and clears extra object', async () => {
    const wrapper = await form(item)
    for (const key of ['brand', 'model', 'color', 'size', 'material', 'notes']) await wrapper.get(`#item-${key}`).setValue('')
    await wrapper.get('[data-purpose="6"]').setValue(false)
    await wrapper.get('[data-climate="9"]').setValue(false)
    await wrapper.get('[data-climate="11"]').setValue(true)
    await wrapper.get('#item-extra').setValue('{}')
    await submit(wrapper)
    expect(updated(wrapper)).toMatchObject({ brand: null, model: null, color: null, size: null, material: null, notes: null,
      purpose_ids: [8], climate_ids: [11], extra_attributes: {} })
  })
  it('clears both relation arrays', async () => {
    const wrapper = await form(item)
    for (const selector of ['[data-purpose="6"]', '[data-purpose="8"]', '[data-climate="9"]']) await wrapper.get(selector).setValue(false)
    await submit(wrapper)
    expect(updated(wrapper)).toMatchObject({ purpose_ids: [], climate_ids: [] })
  })
  it('omits individual quantity on edit', async () => {
    const wrapper = await form({ ...item, tracking_mode: 'individual', quantity: 1 })
    expect(wrapper.find('#item-quantity').exists()).toBe(false)
    await submit(wrapper)
    expect(updated(wrapper)).not.toHaveProperty('quantity')
    expect(updated(wrapper)).not.toHaveProperty('tracking_mode')
  })
  it('disables duplicate submits while mutation is pending', async () => {
    const wrapper = await form()
    await required(wrapper)
    await wrapper.setProps({ pending: true })
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    await submit(wrapper)
    expect(wrapper.emitted('create')).toBeUndefined()
  })
})
