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
  <Topbar title="Calibration &amp; Maintenance" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Due Today" :value="0" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Overdue" :value="0" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="In Progress" :value="0" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Recent Completions" :value="0" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        :selectable="true"
        @select="(r) => (selected = r)"
        empty-text="No data"
        :columns="[
          { key: 'instrument', label: 'Instrument' },
          { key: 'task', label: 'Task Type' },
          { key: 'due', label: 'Due Date' },
          { key: 'assigned', label: 'Assigned To' },
          { key: 'status', label: 'Status' },
          { key: 'last', label: 'Last Completed' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.instrument" :subtitle="selected.task" @close="selected = null">
      <div class="text-sm space-y-3">
        <div class="flex justify-between"><span class="text-surface-500">Due Date</span><span>{{ selected.due }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Assigned To</span><span>{{ selected.assigned }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Status</span><StatusPill :status="selected.status"/></div>
      </div>
      <button class="btn-primary w-full mt-6">Start Task</button>
      <button class="btn-ghost w-full mt-2">Mark Complete</button>
      <button class="btn-danger-ghost w-full mt-2">Escalate</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a task</div>
  </div>
</template>
