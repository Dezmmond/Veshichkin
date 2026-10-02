import type { components } from '../../api/generated/schema'

export const emptyProfile: components['schemas']['MeasurementProfileResponse'] = {
  height_cm: null, weight_kg: null, chest_cm: null, waist_cm: null, hips_cm: null,
  inseam_cm: null, foot_length_cm: null, extra_measurements: {}, updated_at: '2026-10-02T12:00:00Z',
}

export const profile: components['schemas']['MeasurementProfileResponse'] = {
  ...emptyProfile, height_cm: '182.00', weight_kg: '78.50', foot_length_cm: '27.40',
  extra_measurements: { neck_cm: 39 },
}
