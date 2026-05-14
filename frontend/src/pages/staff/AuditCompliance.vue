<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'

const selected = ref<any>(null)
const rows = ref<any[]>([])

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    rows.value = []
  } catch {
    rows.value = []
  }
})
</script>

<template>
  <Topbar title="Audit &amp; Compliance Pack" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Open Findings" :value="0" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Documents Expiring" :value="0" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Audit Readiness" :value="0" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Missing Evidence" :value="0" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" :selectable="true" :initial-selected-index="0" @select="(r) => (selected = r)" empty-text="No data"
        :columns="[
          { key: 'section', label: 'Section' },
          { key: 'description', label: 'Description' },
          { key: 'status', label: 'Status' },
          { key: 'completion', label: 'Completion' },
          { key: 'last', label: 'Last Updated' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
        <template #cell-completion="{ value }">
          <div class="flex items-center gap-2">
            <div class="flex-1 h-1.5 bg-surface-100 rounded">
              <div class="h-1.5 bg-brand-teal-500 rounded" :style="{ width: `${value}%` }"></div>
            </div>
            <span class="text-xs text-surface-500 w-9 text-right">{{ value }}%</span>
          </div>
        </template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.section" :subtitle="selected.description" @close="selected = null">
      <div class="grid grid-cols-2 gap-3 text-sm mb-4">
        <div><div class="text-surface-500 text-xs">Documents</div><div class="font-semibold text-lg">24</div></div>
        <div><div class="text-surface-500 text-xs">Uploaded</div><div class="font-semibold text-lg">24</div></div>
        <div><div class="text-surface-500 text-xs">Expiring Soon</div><div class="font-semibold text-lg">1</div></div>
        <div><div class="text-surface-500 text-xs">Overdue</div><div class="font-semibold text-lg">0</div></div>
      </div>
      <button class="btn-primary w-full">Open Folder</button>
      <button class="btn-secondary w-full mt-2">Upload Evidence</button>
      <button class="btn-ghost w-full mt-2">Export Pack</button>
      <button class="btn-ghost w-full mt-2">Schedule Review</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a section</div>
  </div>
</template>
