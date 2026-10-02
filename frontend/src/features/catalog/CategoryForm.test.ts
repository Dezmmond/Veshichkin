import { describe, expect, it } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import CategoryForm from './CategoryForm.vue'
import { tree } from './fixtures.test-support'
import type { CategoryCreate } from '../../api/categories'

function form(editing = false, parentId?: number) {
  return mount(CategoryForm, { props: { tree, category: editing ? tree[0].children![0] : undefined, parentId, pending: false },
    global: { stubs: { RouterLink: RouterLinkStub } } })
}
type Wrapper = ReturnType<typeof form>
function saved(wrapper: Wrapper) { return wrapper.emitted('save')?.[0]?.[0] as CategoryCreate }

describe('category form', () => {
  it('creates root with trimmed name and default order', async () => {
    const wrapper = form()
    await wrapper.get('#category-name').setValue('  Корень A  ')
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper)).toEqual({ name: 'Корень A', parent_id: null, sort_order: 0 })
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/catalog')
    wrapper.unmount()
  })
  it('preselects child parent and accepts a different selection', async () => {
    const wrapper = form(false, 20)
    expect((wrapper.get('#category-parent').element as HTMLSelectElement).selectedOptions[0]?.text).toBe('↳ Ветка B')
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/catalog/categories/20')
    await wrapper.get('#category-name').setValue('Дочерняя')
    await wrapper.get('#category-parent').setValue('40')
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper).parent_id).toBe(40)
    wrapper.unmount()
  })
  it('ignores unknown parent preselect', () => {
    const wrapper = form(false, 999)
    expect((wrapper.get('#category-parent').element as HTMLSelectElement).selectedOptions[0]?.text).toBe('Без родительской категории')
    wrapper.unmount()
  })
  it('blocks empty trimmed name', async () => {
    const wrapper = form()
    await wrapper.get('#category-name').setValue('  ')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('Укажите название категории.')
    wrapper.unmount()
  })
  it.each(['', '-1', '1.5'])('blocks invalid sort order %s', async (order) => {
    const wrapper = form()
    await wrapper.get('#category-name').setValue('Категория')
    await wrapper.get('#category-order').setValue(order)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toContain('целым числом')
    wrapper.unmount()
  })
  it('prefills edit and excludes self/descendants', async () => {
    const wrapper = form(true)
    expect((wrapper.get('#category-name').element as HTMLInputElement).value).toBe('Ветка B')
    expect((wrapper.get('#category-order').element as HTMLInputElement).value).toBe('0')
    expect((wrapper.get('#category-parent').element as HTMLSelectElement).selectedOptions[0]?.text).toBe('Корень A')
    expect(wrapper.findAll('#category-parent option').map((entry) => entry.text()))
      .toEqual(['Без родительской категории', 'Корень A', 'Корень D'])
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toBe('/catalog/categories/20')
    await wrapper.get('#category-name').setValue(' Новое имя ')
    await wrapper.get('#category-parent').setValue('40')
    await wrapper.get('#category-order').setValue('3')
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper)).toEqual({ name: 'Новое имя', parent_id: 40, sort_order: 3 })
    wrapper.unmount()
  })
  it('moves existing child to root with explicit null', async () => {
    const wrapper = form(true)
    await wrapper.get('#category-parent').setValue((wrapper.get('#category-parent').element as HTMLSelectElement).options[0].value)
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper).parent_id).toBeNull()
    wrapper.unmount()
  })
  it('blocks repeated save while pending', async () => {
    const wrapper = form(true)
    await wrapper.setProps({ pending: true })
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('button').attributes('disabled')).toBeDefined()
    expect(wrapper.emitted('save')).toBeUndefined()
    wrapper.unmount()
  })
})
