<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'
import { computed, ref } from 'vue'

const props = defineProps<{
  items: Array<{ to: string; label: string; icon: string; key: string; section?: string }>
  brand?: { title: string; subtitle: string }
}>()

const collapsed = ref(false)
const route = useRoute()

// An item is "active" ONLY when it's the MOST SPECIFIC match for the current
// path. Without this, /lab/reports would light up both "Lab" AND "Lab
// Reports" because both are prefixes of the path.
function isActive(to: string): boolean {
  const here = route.path || '/'
  if (to === '/') return here === '/'
  const matches = here === to || here.startsWith(to + '/')
  if (!matches) return false
  // Reject if another sidebar item has a MORE specific `to` that also matches.
  const longer = props.items.some((it) =>
    it.to !== to && it.to.length > to.length &&
    (here === it.to || here.startsWith(it.to + '/')),
  )
  return !longer
}

// Group items by their `section` string, preserving definition order.
// Loose items (no section) come first as a top block with no header.
const grouped = computed(() => {
  const groups: Array<{ title: string; items: typeof props.items }> = []
  for (const it of props.items) {
    const key = it.section || ''
    let g = groups.find((x) => x.title === key)
    if (!g) { g = { title: key, items: [] }; groups.push(g) }
    g.items.push(it)
  }
  return groups
})

const iconMap: Record<string, string> = {
  home: 'M3 9.5L12 3l9 6.5V20a1 1 0 01-1 1h-5v-7H9v7H4a1 1 0 01-1-1V9.5z',
  // Patients — head-and-shoulders silhouette
  patients: 'M16 14a4 4 0 10-8 0M12 11a4 4 0 100-8 4 4 0 000 8zM6 21v-2a4 4 0 014-4h4a4 4 0 014 4v2',
  // Customers — briefcase (distinct from Patients now)
  customers: 'M20 7h-3V5a2 2 0 00-2-2H9a2 2 0 00-2 2v2H4a1 1 0 00-1 1v11a1 1 0 001 1h16a1 1 0 001-1V8a1 1 0 00-1-1zM9 5h6v2H9V5zm12 15H3v-4h5v1h8v-1h5v4z',
  orders: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5a2 2 0 002 2h2a2 2 0 002-2',
  collection: 'M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z',
  lab: 'M9 3v6.343M15 3v6.343M5 21h14l-4-12H9L5 21z',
  radiology: 'M21 12a9 9 0 11-18 0 9 9 0 0118 0zM12 7v5l3 2',
  critical: 'M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  // Billing — receipt / invoice
  billing: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 12h6m-6 4h4',
  // Shift — clock
  shift: 'M12 6v6l4 2M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  // Check-in — clipboard with tick
  checkin: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5a2 2 0 002 2h2a2 2 0 002-2m-6 8l2 2 4-4',
  analytics: 'M3 3v18h18M7 14l3-3 4 4 5-5',
  audit: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
  settings: 'M10.325 4.317a1 1 0 011.35 0l.8.69a1 1 0 00.92.21l1.05-.25a1 1 0 011.16.71l.3 1.04a1 1 0 00.66.65l1.05.3a1 1 0 01.71 1.16l-.25 1.05a1 1 0 00.21.92l.69.8a1 1 0 010 1.35l-.69.8a1 1 0 00-.21.92l.25 1.05a1 1 0 01-.71 1.16l-1.05.3a1 1 0 00-.66.65l-.3 1.04a1 1 0 01-1.16.71l-1.05-.25a1 1 0 00-.92.21l-.8.69a1 1 0 01-1.35 0l-.8-.69a1 1 0 00-.92-.21l-1.05.25a1 1 0 01-1.16-.71l-.3-1.04a1 1 0 00-.66-.65l-1.05-.3a1 1 0 01-.71-1.16l.25-1.05a1 1 0 00-.21-.92l-.69-.8a1 1 0 010-1.35l.69-.8a1 1 0 00.21-.92l-.25-1.05a1 1 0 01.71-1.16l1.05-.3a1 1 0 00.66-.65l.3-1.04a1 1 0 011.16-.71l1.05.25a1 1 0 00.92-.21l.8-.69zM12 15a3 3 0 100-6 3 3 0 000 6z',
  // Branches — building
  branches: 'M4 21V5a2 2 0 012-2h6a2 2 0 012 2v16m-8 0h16m-8-14h4a2 2 0 012 2v12M9 7h.01M9 11h.01M9 15h.01',
  workflow: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 012-2h2a2 2 0 012 2M9 5a2 2 0 002 2h2a2 2 0 002-2m-7 8l2 2 4-4',
  reports: 'M9 12h6m-6 4h6M9 8h6M5 21h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v14a2 2 0 002 2z',
}
</script>

<template>
  <aside
    class="bg-white border-r border-surface-200 h-screen sticky top-0 flex flex-col"
    :class="collapsed ? 'w-14' : 'w-52'"
  >
    <!-- Brand -->
    <div class="px-4 py-3 border-b border-surface-100">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-brand-navy-700 flex items-center justify-center text-white shrink-0">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v6.343M15 3v6.343M5 21h14l-4-12H9L5 21z"/>
          </svg>
        </div>
        <div v-if="!collapsed" class="leading-tight">
          <div class="text-sm font-bold text-brand-navy-700">{{ brand?.title || 'Azzir' }}</div>
          <div class="text-[9px] uppercase tracking-widest text-brand-teal-600">{{ brand?.subtitle || 'ADMS' }}</div>
        </div>
      </div>
    </div>
    <!-- Nav — grouped by section with tiny caption headers -->
    <nav class="flex-1 overflow-y-auto py-2">
      <div v-for="(group, gi) in grouped" :key="group.title || `_top${gi}`" class="mb-2">
        <div v-if="group.title && !collapsed"
             class="px-3 pt-2 pb-1 text-[10px] font-semibold uppercase tracking-wider text-surface-400">
          {{ group.title }}
        </div>
        <ul class="space-y-0.5 px-2">
          <li v-for="item in group.items" :key="item.key">
            <RouterLink
              :to="item.to"
              :class="[
                'flex items-center gap-2.5 px-2.5 py-1.5 rounded-md text-[13px] transition-colors',
                isActive(item.to)
                  ? 'bg-brand-navy-700 text-white shadow-card'
                  : 'text-surface-600 hover:bg-surface-50',
              ]"
              :title="collapsed ? item.label : ''"
            >
              <svg class="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="iconMap[item.icon] || iconMap.home"/>
              </svg>
              <span v-if="!collapsed">{{ item.label }}</span>
            </RouterLink>
          </li>
        </ul>
      </div>
    </nav>
    <!-- Collapse -->
    <div class="border-t border-surface-100 p-2">
      <button class="flex items-center gap-2 text-xs text-surface-500 hover:text-surface-800 px-2 py-1" @click="collapsed = !collapsed">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" :d="collapsed ? 'M9 5l7 7-7 7' : 'M15 19l-7-7 7-7'"/>
        </svg>
        <span v-if="!collapsed">Collapse</span>
      </button>
    </div>
  </aside>
</template>
