import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import MeasurementProfileForm from './MeasurementProfileForm.vue'
import { emptyProfile, profile } from './fixtures.test-support'
import type { MeasurementProfilePatch } from '../../api/profile'

function form(existing: typeof profile | null = null) {
  return mount(MeasurementProfileForm, { props: { profile: existing, pending: false, error: false } })
}
type Form = ReturnType<typeof form>
function saved(wrapper: Form) { return wrapper.emitted('save')?.[0]?.[0] as MeasurementProfilePatch }

describe('measurement form semantics', () => {
  it('allows only one field, preserves 0.01 and sends null for empty fields', async () => {
    const wrapper = form()
    await wrapper.get('#measurement-foot_length_cm').setValue('0.01')
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper)).toEqual({ height_cm: null, weight_kg: null, chest_cm: null, waist_cm: null,
      hips_cm: null, inseam_cm: null, foot_length_cm: '0.01', extra_measurements: {} })
    expect(wrapper.get('#measurement-foot_length_cm').attributes('inputmode')).toBe('decimal')
    expect(wrapper.get('label[for="measurement-foot_length_cm"]').text()).toBe('Длина стопы (см)')
    expect(wrapper.get('label[for="measurement-weight_kg"]').text()).toBe('Вес (кг)')
    wrapper.unmount()
  })
  it('sends multiple decimal strings without rounding and accepts decimal comma', async () => {
    const wrapper = form()
    for (const [key, value] of [['height_cm', '182.00'], ['weight_kg', '78.5'], ['chest_cm', '101'],
      ['waist_cm', '80'], ['hips_cm', '95.05'], ['inseam_cm', '85'], ['foot_length_cm', '27,4']]) {
      await wrapper.get(`#measurement-${key}`).setValue(value)
    }
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper)).toMatchObject({ height_cm: '182.00', weight_kg: '78.5', chest_cm: '101',
      waist_cm: '80', hips_cm: '95.05', inseam_cm: '85', foot_length_cm: '27.4' })
    wrapper.unmount()
  })
  it.each(['0', '0.00', '-1', 'NaN', 'Infinity', 'abc', '10000', '9999.999', '1.234', '1e2', '0.001'])(
    'blocks invalid decimal %s without emitting a payload', async (value) => {
      const wrapper = form()
      await wrapper.get('#measurement-height_cm').setValue(value)
      await wrapper.get('form').trigger('submit')
      expect(wrapper.emitted('save')).toBeUndefined()
      expect(wrapper.get('[role="alert"]').text()).toContain('Рост: введите число больше 0')
      wrapper.unmount()
    },
  )
  it.each([['9999.99', '9999.99'], ['.01', '0.01'], ['00027.40', '27.40'], [' 182.00 ', '182.00']])(
    'accepts decimal boundary/normalization %s', async (value, result) => {
      const wrapper = form()
      await wrapper.get('#measurement-height_cm').setValue(value)
      await wrapper.get('form').trigger('submit')
      expect(saved(wrapper).height_cm).toBe(result)
      wrapper.unmount()
    },
  )
  it('allows an entirely empty profile', async () => {
    const wrapper = form(emptyProfile)
    await wrapper.get('form').trigger('submit')
    expect(Object.values(saved(wrapper)).filter((value) => value === null)).toHaveLength(7)
    expect(saved(wrapper).extra_measurements).toEqual({})
    wrapper.unmount()
  })
  it('prefills response strings and existing custom object; clearing sends null and {}', async () => {
    const wrapper = form(profile)
    expect((wrapper.get('#measurement-height_cm').element as HTMLInputElement).value).toBe('182.00')
    expect((wrapper.get('#measurement-extra').element as HTMLTextAreaElement).value).toContain('"neck_cm": 39')
    await wrapper.get('#measurement-height_cm').setValue('')
    await wrapper.get('#measurement-extra').setValue('{}')
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper)).toMatchObject({ height_cm: null, weight_kg: '78.50', extra_measurements: {} })
    wrapper.unmount()
  })
  it('replaces custom measurements with a parsed object', async () => {
    const wrapper = form(profile)
    await wrapper.get('#measurement-extra').setValue('{"shoulder_width_cm":47,"nested":{"value":1}}')
    await wrapper.get('form').trigger('submit')
    expect(saved(wrapper).extra_measurements).toEqual({ shoulder_width_cm: 47, nested: { value: 1 } })
    wrapper.unmount()
  })
  it.each(['{invalid', '[]', 'null', '"text"', '39'])('rejects non-object/invalid JSON %s', async (json) => {
    const wrapper = form()
    await wrapper.get('#measurement-extra').setValue(json)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('save')).toBeUndefined()
    expect(wrapper.get('[role="alert"]').text()).toBe('Дополнительные замеры должны быть корректным JSON-объектом.')
    wrapper.unmount()
  })
  it('shows {} for empty existing custom measurements', () => {
    const wrapper = form(emptyProfile)
    expect((wrapper.get('#measurement-extra').element as HTMLTextAreaElement).value).toBe('{}')
    wrapper.unmount()
  })
  it('emits cancel without saving', async () => {
    const wrapper = form(profile)
    await wrapper.findAll('button')[1].trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
    expect(wrapper.emitted('save')).toBeUndefined()
    wrapper.unmount()
  })
})
