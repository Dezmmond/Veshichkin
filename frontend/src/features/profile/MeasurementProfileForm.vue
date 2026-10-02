<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { components } from '../../api/generated/schema'
import type { MeasurementProfilePatch } from '../../api/profile'
import { measurementFields, parseMeasurement, type MeasurementFieldKey } from './measurements'

const props = defineProps<{ profile: components['schemas']['MeasurementProfileResponse'] | null;
  pending: boolean; error: boolean }>()
const emit = defineEmits<{ save: [body: MeasurementProfilePatch]; cancel: [] }>()
const fields = reactive(Object.fromEntries(measurementFields.map(({ key }) => [key, props.profile?.[key] ?? ''])) as Record<MeasurementFieldKey, string>)
const extra = ref(JSON.stringify(props.profile?.extra_measurements ?? {}, null, 2))
const validation = ref('')
function submit() {
  if (props.pending) return
  validation.value = ''
  const body: MeasurementProfilePatch = {}
  for (const field of measurementFields) {
    try { body[field.key] = parseMeasurement(fields[field.key]) }
    catch {
      validation.value = `${field.label}: введите число больше 0 и не больше 9999.99, максимум два знака после запятой.`
      return
    }
  }
  try {
    const parsed: unknown = extra.value.trim() ? JSON.parse(extra.value) : {}
    if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error()
    body.extra_measurements = parsed as MeasurementProfilePatch['extra_measurements']
  } catch {
    validation.value = 'Дополнительные замеры должны быть корректным JSON-объектом.'
    return
  }
  emit('save', body)
}
</script>

<template>
  <form class="item-form measurement-form" novalidate @submit.prevent="submit">
    <fieldset :disabled="pending">
      <legend class="visually-hidden">Мои замеры</legend>
      <p>Заполните нужные поля. Остальные можно оставить пустыми.</p>
      <template v-for="field in measurementFields" :key="field.key">
        <label :for="`measurement-${field.key}`">{{ field.label }} ({{ field.unit }})</label>
        <input :id="`measurement-${field.key}`" v-model="fields[field.key]" type="text" inputmode="decimal" autocomplete="off">
      </template>
      <details>
        <summary>Дополнительные замеры</summary>
        <label for="measurement-extra">JSON-объект</label>
        <textarea id="measurement-extra" v-model="extra" rows="5" spellcheck="false" />
      </details>
    </fieldset>
    <p v-if="validation" role="alert">{{ validation }}</p>
    <p v-if="error" role="alert">Не удалось сохранить замеры.</p>
    <div class="item-actions">
      <button type="submit" :disabled="pending">{{ pending ? 'Сохранение…' : 'Сохранить' }}</button>
      <button type="button" :disabled="pending" @click="emit('cancel')">Отмена</button>
    </div>
  </form>
</template>
