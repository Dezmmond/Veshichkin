<script setup lang="ts">
import { useHealthQuery } from '../api/health'

const { isPending, isError } = useHealthQuery()
</script>

<template>
  <section>
    <h1>Veshichkin</h1>
    <p>Проект на этапе создания базового каркаса. Разделы каталога и ревизии пока доступны как заглушки.</p>
    <p role="status" aria-live="polite">
      <template v-if="isPending">Backend: проверка…</template>
      <template v-else-if="isError">Backend: недоступен</template>
      <template v-else>Backend: доступен</template>
    </p>
  </section>
</template>
