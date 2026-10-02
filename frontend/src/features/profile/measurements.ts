import type { components } from '../../api/generated/schema'

export const measurementFields = [
  { key: 'height_cm', label: 'Рост', unit: 'см' },
  { key: 'weight_kg', label: 'Вес', unit: 'кг' },
  { key: 'chest_cm', label: 'Обхват груди', unit: 'см' },
  { key: 'waist_cm', label: 'Обхват талии', unit: 'см' },
  { key: 'hips_cm', label: 'Обхват бёдер', unit: 'см' },
  { key: 'inseam_cm', label: 'Длина по внутреннему шву', unit: 'см' },
  { key: 'foot_length_cm', label: 'Длина стопы', unit: 'см' },
] as const satisfies readonly {
  key: keyof Omit<components['schemas']['MeasurementProfileResponse'], 'extra_measurements' | 'updated_at'>;
  label: string; unit: string
}[]

export type MeasurementFieldKey = typeof measurementFields[number]['key']

export function parseMeasurement(value: string): string | null {
  const decimal = value.trim().replace(',', '.')
  if (!decimal) return null
  if (!/^(?:\d+(?:\.\d{1,2})?|\.\d{1,2})$/.test(decimal)) throw new Error('Invalid decimal')
  const [whole, fraction] = decimal.split('.')
  const integer = (whole || '0').replace(/^0+(?=\d)/, '')
  if (integer.length > 4 || !/[1-9]/.test(decimal)) throw new Error('Decimal out of range')
  return fraction === undefined ? integer : `${integer}.${fraction}`
}
