<script setup lang="ts">
import { computed, ref } from 'vue'
import { useMeasurementProfileQuery, useUpdateMeasurementProfileMutation, type MeasurementProfilePatch } from '../api/profile'
import MeasurementProfileForm from '../features/profile/MeasurementProfileForm.vue'
import { measurementFields } from '../features/profile/measurements'

const query = useMeasurementProfileQuery()
const mutation = useUpdateMeasurementProfileMutation()
const editing = ref(false)
const profile = query.data
const values = computed(() => measurementFields.filter(({ key }) => profile.value?.[key] != null))
const hasExtra = computed(() => !!profile.value && Object.keys(profile.value.extra_measurements).length > 0)
function edit() { mutation.reset(); editing.value = true }
function cancel() { if (!mutation.isPending.value) { editing.value = false; mutation.reset() } }
async function save(body: MeasurementProfilePatch) {
  if (mutation.isPending.value) return
  try {
    await mutation.mutateAsync(body)
    editing.value = false
  } catch { /* Keep the form values; display a safe mutation error. */ }
}
</script>

<template>
  <section class="measurement-profile">
    <h1>Мои замеры</h1>
    <MeasurementProfileForm v-if="editing" :profile="profile ?? null" :pending="mutation.isPending.value"
      :error="mutation.isError.value" @save="save" @cancel="cancel" />
    <p v-else-if="query.isError.value" role="alert">Не удалось загрузить замеры.</p>
    <p v-else-if="query.isPending.value" role="status">Загрузка замеров…</p>
    <template v-else-if="profile === null">
      <p>Замеры пока не сохранены.</p>
      <div class="item-actions"><button type="button" @click="edit">Заполнить замеры</button></div>
    </template>
    <template v-else-if="profile">
      <p v-if="!values.length && !hasExtra">Замеры пока не заполнены.</p>
      <dl v-if="values.length">
        <template v-for="field in values" :key="field.key">
          <dt>{{ field.label }}</dt><dd>{{ profile[field.key] }} {{ field.unit }}</dd>
        </template>
      </dl>
      <section v-if="hasExtra" aria-label="Дополнительные замеры">
        <h2>Дополнительные замеры</h2><pre>{{ JSON.stringify(profile.extra_measurements, null, 2) }}</pre>
      </section>
      <div class="item-actions"><button type="button" @click="edit">Редактировать</button></div>
    </template>
  </section>
</template>
