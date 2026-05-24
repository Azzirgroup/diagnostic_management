<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { ref } from 'vue'

defineProps<{
  items: Array<{ to: string; label: string; icon: string; key: string }>
  brand?: { title: string; subtitle: string }
}>()

const collapsed = ref(false)
const route = useRoute()

// Compute active state manually because:
//   • RouterLink's default active-class on `to="/"` matches every path (it
//     prefix-matches), so Home would light up everywhere.
//   • `/orders/:name` is a SIBLING route to `/orders`, not a nested child,
//     so RouterLink doesn't treat it as a descendant — the Orders item
//     wouldn't light up on an order detail page.
// The path-prefix rule below handles both cleanly: Home only when exactly
// at root, every other item when the path matches or starts with its `to`.
function isActive(to: string): boolean {
  const here = route.path || '/'
  if (to === '/') return here === '/'
  return here === to || here.startsWith(to + '/')
}

const iconMap: Record<string, string> = {
  home: 'M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1h-5v-7H9v7H4a1 1 0 01-1-1V9.5z',
  patients: 'M16 14a4 4 0 10-8 0M12 11a4 4 0 100-8 4 4 0 000 8zM6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2',
  orders: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5a2 2 0 002 2h2a2 2 0 002-2',
  collection: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
  lab: 'M9 3v6.343M15 3v6.343M5 21h14l-4-12H9L5 21z',
  radiology: 'M21 12a9 9 0 11-18 0 9 9 0 0118 0zM12 7v5l3 2',
  critical: 'M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  billing: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 12h6m-6 4h4',
  analytics: 'M3 3v18h18M7 14l3-3 4 4 5-5',
  audit: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  settings: 'M10.325 4.317a1 1 0 011.35 0l.8.69a1 1 0 00.92.21l1.05-.25a1 1 0 011.16.71l.3 1.04a1 1 0 00.66.65l1.05.3a1 1 0 01.71 1.16l-.25 1.05a1 1 0 00.21.92l.69.8a1 1 0 010 1.35l-.69.8a1 1 0 00-.21.92l.25 1.05a1 1 0 01-.71 1.16l-1.05.3a1 1 0 00-.66.65l-.3 1.04a1 1 0 01-1.16.71l-1.05-.25a1 1 0 00-.92.21l-.8.69a1 1 0 01-1.35 0l-.8-.69a1 1 0 00-.92-.21l-1.05.25a1 1 0 01-1.16-.71l-.3-1.04a1 1 0 00-.66-.65l-1.05-.3a1 1 0 01-.71-1.16l.25-1.05a1 1 0 00-.21-.92l-.69-.8a1 1 0 010-1.35l.69-.8a1 1 0 00.21-.92l-.25-1.05a1 1 0 01.71-1.16l1.05-.3a1 1 0 00.66-.65l.3-1.04a1 1 0 011.16-.71l1.05.25a1 1 0 00.92-.21l.8-.69zM12 15a3 3 0 100-6 3 3 0 000 6z',
  inbox: 'M3 7l9 6 9-6M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z',
  statements: 'M8 7h12m-12 5h12m-12 5h12M3 7h.01M3 12h.01M3 17h.01',
  logout: 'M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h6a2 2 0 012 2v1',
  dashboard: 'M4 5h6v6H4V5zm10 0h6v6h-6V5zM4 13h6v6H4v-6zm10 0h6v6h-6v-6z',
  workflow: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5a2 2 0 002 2h2a2 2 0 002-2m-7 8l2 2 4-4',
}
</script>

<template>
  <aside
    class="bg-white border-r border-surface-200 h-screen sticky top-0 flex flex-col"
    :class="collapsed ? 'w-16' : 'w-60'"
  >
    <!-- Brand -->
    <div class="px-5 py-5 border-b border-surface-100">
      <div class="flex items-center gap-2">
        <div class="w-9 h-9 rounded-lg bg-brand-navy-700 flex items-center justify-center text-white shrink-0">
          <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v6.343M15 3v6.343M5 21h14l-4-12H9L5 21z"/>
          </svg>
        </div>
        <div v-if="!collapsed" class="leading-tight">
          <div class="text-base font-bold text-brand-navy-700">{{ brand?.title || 'Azzir' }}</div>
          <div class="text-[10px] uppercase tracking-widest text-brand-teal-600">{{ brand?.subtitle || 'ADMS' }}</div>
        </div>
      </div>
    </div>
    <!-- Nav -->
    <nav class="flex-1 overflow-y-auto py-3">
      <ul class="space-y-1 px-2">
        <li v-for="item in items" :key="item.key">
          <RouterLink
            :to="item.to"
            :class="[
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors',
              isActive(item.to)
                ? 'bg-brand-navy-700 text-white shadow-card'
                : 'text-surface-600 hover:bg-surface-50',
            ]"
          >
            <svg class="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="iconMap[item.icon] || iconMap.home"/>
            </svg>
            <span v-if="!collapsed">{{ item.label }}</span>
          </RouterLink>
        </li>
      </ul>
    </nav>
    <!-- Collapse -->
    <div class="border-t border-surface-100 p-3">
      <button class="flex items-center gap-2 text-sm text-surface-500 hover:text-surface-800" @click="collapsed = !collapsed">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="collapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'"/>
        </svg>
        <span v-if="!collapsed">Collapse</span>
      </button>
    </div>
  </aside>
</template>
