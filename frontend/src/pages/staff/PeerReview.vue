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
  <Topbar title="Peer Review Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Reviews" :value="0" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Overdue" :value="0" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Discrepancies" :value="0" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Completed This Week" :value="0" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" :selectable="true" @select="(r) => (selected = r)" empty-text="No data"
        :columns="[
          { key: 'case', label: 'Case ID' },
          { key: 'patient', label: 'Patient' },
          { key: 'test', label: 'Test / Panel' },
          { key: 'reporter', label: 'Original Reporter' },
          { key: 'reviewer', label: 'Assigned Reviewer' },
          { key: 'due', label: 'Due Date' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.case" :subtitle="selected.patient" @close="selected = null">
      <dl class="text-sm space-y-3">
        <div class="flex justify-between"><dt class="text-surface-500">Test / Panel</dt><dd>{{ selected.test }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reporter</dt><dd>{{ selected.reporter }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Due</dt><dd>{{ selected.due }}</dd></div>
      </dl>
      <label class="block text-xs text-surface-500 mt-4 mb-1">Review Notes (Required)</label>
      <textarea class="input" rows="4" placeholder="Enter your comparison, comments, or additional findings..."></textarea>
      <button class="btn-primary w-full mt-4">Submit Review</button>
      <button class="btn-secondary w-full mt-2">Mark Agree</button>
      <button class="btn-danger-ghost w-full mt-2">Request Discussion</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a case to review</div>
  </div>
</template>
