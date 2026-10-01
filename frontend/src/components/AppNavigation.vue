<script setup lang="ts">
import { RouterLink } from 'vue-router'
</script>

<template>
  <nav class="app-navigation" aria-label="Основная навигация">
    <RouterLink to="/">Главная</RouterLink>
    <RouterLink to="/catalog">Каталог</RouterLink>
    <RouterLink to="/revision">Ревизия</RouterLink>
  </nav>
</template>
