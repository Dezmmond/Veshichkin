import type { components } from '../../api/generated/schema'

export const tree: components['schemas']['CategoryTree'][] = [
  { id: 10, name: 'Корень A', parent_id: null, sort_order: 0, children: [
    { id: 20, name: 'Ветка B', parent_id: 10, sort_order: 0, children: [
      { id: 30, name: 'Лист C', parent_id: 20, sort_order: 0, children: [] },
    ] },
  ] },
  { id: 40, name: 'Корень D', parent_id: null, sort_order: 1, children: [] },
]

export const item: components['schemas']['ItemResponse'] = {
  id: 1, category_id: 20, name: 'Набор вещей', tracking_mode: 'grouped', quantity: 7,
  condition_id: 5, purpose_ids: [6, 8], climate_ids: [9], is_active: true,
  brand: 'Brand', model: 'Model', color: 'Синий', size: 'M', material: 'Хлопок',
  notes: null, extra_attributes: {}, created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

export const conditions: components['schemas']['ConditionResponse'][] = [
  { id: 5, name: 'Хорошее', code: 'sample', rank: 1, description: null },
]
export const purposes: components['schemas']['OrderedReferenceResponse'][] = [
  { id: 6, name: 'Прогулки', code: 'walk', sort_order: 0 },
  { id: 8, name: 'Работа', code: 'work', sort_order: 1 },
]
export const climates: components['schemas']['OrderedReferenceResponse'][] = [
  { id: 9, name: 'Тёплый', code: 'warm', sort_order: 0 },
]
