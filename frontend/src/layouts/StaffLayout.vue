<script setup lang="ts">
import { computed } from 'vue'
import Sidebar from '@/components/layout/Sidebar.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// Analytics is restricted to managers — only users carrying System Manager
// or Manager (the diagnostic Lab/Radiology/Diagnostic manager variants) see
// the sidebar entry. Everyone else still has it filtered out client-side.
const isManager = computed(() => {
  const roles = auth.roles || []
  return roles.some((r) =>
    r === 'System Manager' ||
    r === 'Manager' ||
    r === 'Lab Manager' ||
    r === 'Radiology Manager' ||
    r === 'Diagnostic Director' ||
    r === 'Lab Director',
  )
})

const items = computed(() => {
  const all = [
    { to: '/', label: 'Home', icon: 'home', key: 'home' },
    { to: '/patients', label: 'Patients', icon: 'patients', key: 'patients' },
    { to: '/orders', label: 'Test Orders', icon: 'orders', key: 'orders' },
    { to: '/collection', label: 'Collection', icon: 'collection', key: 'collection' },
    { to: '/lab', label: 'Lab', icon: 'lab', key: 'lab' },
    { to: '/radiology', label: 'Radiology', icon: 'radiology', key: 'radiology' },
    { to: '/critical-findings', label: 'Critical Findings', icon: 'critical', key: 'critical' },
    { to: '/billing', label: 'Billing', icon: 'billing', key: 'billing' },
    { to: '/analytics', label: 'Analytics', icon: 'analytics', key: 'analytics', manager: true },
    { to: '/audit', label: 'Audit & Compliance', icon: 'audit', key: 'audit' },
    { to: '/settings', label: 'Settings', icon: 'settings', key: 'settings' },
  ]
  return all.filter((i) => !i.manager || isManager.value)
})
</script>

<template>
  <div class="flex min-h-screen bg-surface-50">
    <Sidebar :items="items" />
    <main class="flex-1 px-6 py-6 max-w-full overflow-x-hidden">
      <RouterView />
    </main>
  </div>
</template>
