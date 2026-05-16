<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { qcApi, type QCRow } from '@/api/adms'

const rows = ref<QCRow[]>([])
const selected = ref<QCRow | null>(null)
const correctiveAction = ref('')
const busy = ref(false)

async function load() {
  try { rows.value = await qcApi.list({ limit: 100 }) } catch { rows.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const pending = rows.value.filter((r) => r.status === 'Pending Review').length
  const failed = rows.value.filter((r) => r.result === 'Fail').length
  const due = rows.value.filter((r) => r.result === 'Warning').length
  const passed = rows.value.filter((r) => r.result === 'Pass').length
  const total = passed + failed + due
  const passRate = total ? Math.round((passed / total) * 1000) / 10 : 0
  return { pending, failed, due, passRate }
})

async function approve() {
  if (!selected.value) return
  busy.value = true
  try { await qcApi.approve(selected.value.name); await load(); selected.value = null } finally { busy.value = false }
}
async function reject() {
  if (!selected.value) return
  busy.value = true
  try {
    await qcApi.reject(selected.value.name, correctiveAction.value)
    correctiveAction.value = ''
    await load()
    selected.value = null
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="QC Station" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending QC Runs" :value="kpis.pending" sub="Awaiting review" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Failed Controls" :value="kpis.failed" sub="Require corrective action" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Warnings" :value="kpis.due" sub="1-2s flag" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Pass Rate" :value="kpis.passRate + '%'" sub="Across visible runs" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        empty-text="No QC runs"
        @select="(r) => (selected = r as any)"
        :columns="[
          { key: 'instrument', label: 'Analyzer' },
          { key: 'analyte', label: 'Analyte' },
          { key: 'control_level', label: 'Level' },
          { key: 'lot_number', label: 'Lot' },
          { key: 'section', label: 'Section' },
          { key: 'run_datetime', label: 'Run Time' },
          { key: 'result', label: 'Result' },
          { key: 'westgard_flag', label: 'Westgard' },
        ]"
      >
        <template #cell-result="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.instrument" :subtitle="(selected.section || '—') + ' · ' + (selected.control_level || '—')" @close="selected = null">
      <div class="text-sm space-y-3">
        <div class="flex justify-between"><span class="text-surface-500">Analyte</span><span>{{ selected.analyte }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Lot</span><span>{{ selected.lot_number || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Run Time</span><span>{{ selected.run_datetime || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Expected</span><span>{{ selected.expected_value ?? '—' }} {{ selected.unit || '' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Observed</span><span>{{ selected.observed_value ?? '—' }} {{ selected.unit || '' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">SD</span><span>{{ selected.sd ?? '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Z-Score</span><span>{{ selected.z_score ?? '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Result</span><StatusPill :status="selected.result" /></div>
        <div class="flex justify-between"><span class="text-surface-500">Status</span><StatusPill :status="selected.status" /></div>
      </div>
      <div v-if="selected.westgard_flag" class="card p-3 mt-4 text-xs">
        <div class="font-semibold text-status-danger">Westgard: {{ selected.westgard_flag }}</div>
      </div>
      <label class="text-xs text-surface-500 block mt-4">Corrective Action (if rejecting)</label>
      <textarea v-model="correctiveAction" class="w-full mt-1 px-3 py-2 rounded border border-surface-200 text-sm" rows="2"></textarea>
      <button class="btn-primary w-full mt-4" :disabled="busy || selected.status !== 'Pending Review'" @click="approve">Approve Run</button>
      <button class="btn-danger-ghost w-full mt-2" :disabled="busy || selected.status !== 'Pending Review'" @click="reject">Reject Run</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a QC run</div>
  </div>
</template>
