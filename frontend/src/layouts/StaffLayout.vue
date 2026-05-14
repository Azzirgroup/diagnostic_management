<script setup lang="ts">
import Sidebar from '@/components/layout/Sidebar.vue'

// Sidebar nav items match the screenshots — Home, Patients, Orders, Collection,
// Lab, Radiology, Critical Findings, Billing, Analytics, Audit & Compliance,
// Settings. Visibility per role is enforced by the route guards.
const items = [
  { to: '/', label: 'Home', icon: 'home', key: 'home' },
  { to: '/patients', label: 'Patients', icon: 'patients', key: 'patients' },
  { to: '/orders', label: 'Orders', icon: 'orders', key: 'orders' },
  { to: '/collection', label: 'Collection', icon: 'collection', key: 'collection' },
  { to: '/lab', label: 'Lab', icon: 'lab', key: 'lab' },
  { to: '/radiology', label: 'Radiology', icon: 'radiology', key: 'radiology' },
  { to: '/critical-findings', label: 'Critical Findings', icon: 'critical', key: 'critical' },
  { to: '/billing', label: 'Billing', icon: 'billing', key: 'billing' },
  { to: '/analytics', label: 'Analytics', icon: 'analytics', key: 'analytics' },
  { to: '/audit', label: 'Audit & Compliance', icon: 'audit', key: 'audit' },
  { to: '/settings', label: 'Settings', icon: 'settings', key: 'settings' },
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
