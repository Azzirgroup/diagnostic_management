<script setup lang="ts">
import { computed } from 'vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import { useAuthStore } from '@/stores/auth'
import { canSee, SIDEBAR_ITEMS } from '@/auth/access'

const auth = useAuthStore()

const items = computed(() => SIDEBAR_ITEMS.filter((i) => canSee(i, auth.roles || [])))
</script>

<template>
  <div class="flex min-h-screen bg-surface-50">
    <Sidebar :items="items" />
    <main class="flex-1 px-6 py-6 max-w-full overflow-x-hidden">
      <RouterView />
    </main>
  </div>
</template>
