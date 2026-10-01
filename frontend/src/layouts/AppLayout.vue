<script setup lang="ts">
import { RouterView } from 'vue-router'
import AppNavigation from '../components/AppNavigation.vue'
</script>

<template>
  <div class="app-layout">
    <a class="skip-link" href="#main-content">К содержимому</a>
    <header>
      <AppNavigation />
    </header>
    <main id="main-content" class="app-content" tabindex="-1">
      <RouterView />
    </main>
  </div>
</template>
