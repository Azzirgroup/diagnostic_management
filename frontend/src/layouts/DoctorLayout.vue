<script setup lang="ts">
import Sidebar from '@/components/layout/Sidebar.vue'

// The doctor portal sidebar. The doctor app is mounted with base="/doctor",
// so the router-internal paths are root-relative (/, /results, ...).
const items = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', key: 'dashboard' },
  { to: '/results', label: 'Result Inbox', icon: 'inbox', key: 'inbox' },
  { to: '/patients', label: 'Patients', icon: 'patients', key: 'patients' },
  { to: '/orders', label: 'Orders', icon: 'orders', key: 'orders' },
  { to: '/statements', label: 'Statements & Commission', icon: 'statements', key: 'statements' },
  { to: '/settings', label: 'Profile / Settings', icon: 'settings', key: 'settings' },
]
</script>

<template>
  <div class="flex min-h-screen bg-surface-50">
    <Sidebar :items="items" />
    <main class="flex-1 px-6 py-6 max-w-full overflow-x-hidden">
      <RouterView />
    </main>
  </div>
</template>
