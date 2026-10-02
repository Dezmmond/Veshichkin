<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <section>
    <h1>Страница не найдена</h1>
    <p>По этому адресу нет страницы.</p>
    <RouterLink to="/">Вернуться на главную</RouterLink>
  </section>
</template>
