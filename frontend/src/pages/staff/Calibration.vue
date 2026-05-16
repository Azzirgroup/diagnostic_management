<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { calibrationApi, type CalibrationRow } from '@/api/adms'

const rows = ref<CalibrationRow[]>([])
const dueSoon = ref<CalibrationRow[]>([])
const selected = ref<CalibrationRow | null>(null)

async function load() {
  try { rows.value = await calibrationApi.list({ limit: 100 }) } catch { rows.value = [] }
  try { dueSoon.value = await calibrationApi.dueSoon(14) } catch { dueSoon.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  const dueToday = dueSoon.value.filter((r) => r.next_due === today).length
  const overdue = dueSoon.value.filter((r) => r.next_due && r.next_due < today).length
  const inProgress = rows.value.filter((r) => r.status === 'In Progress' || r.status === 'Scheduled').length
  const recent = rows.value.filter((r) => r.status === 'Completed').length
  return { dueToday, overdue, inProgress, recent }
})
</script>

<template>
  <Topbar title="Calibration &amp; Maintenance" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Due Today" :value="kpis.dueToday" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Overdue" :value="kpis.overdue" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="In Progress / Scheduled" :value="kpis.inProgress" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Completed Runs" :value="kpis.recent" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r as any)"
        empty-text="No calibration runs"
        :columns="[
          { key: 'instrument', label: 'Instrument' },
          { key: 'calibration_type', label: 'Type' },
          { key: 'analyte', label: 'Analyte' },
          { key: 'performed_date', label: 'Performed' },
          { key: 'next_due', label: 'Next Due' },
          { key: 'result', label: 'Result' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-result="{ value }"><StatusPill :status="value as string" /></template>
        <template #cell-status="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.instrument" :subtitle="selected.calibration_type || ''" @close="selected = null">
      <div class="text-sm space-y-3">
        <div class="flex justify-between"><span class="text-surface-500">Analyte</span><span>{{ selected.analyte || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Performed</span><span>{{ selected.performed_date || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">By</span><span>{{ selected.performed_by || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Next Due</span><span>{{ selected.next_due || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Calibrator Lot</span><span>{{ selected.calibrator_lot || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Result</span><StatusPill :status="selected.result"/></div>
        <div class="flex justify-between"><span class="text-surface-500">Status</span><StatusPill :status="selected.status"/></div>
      </div>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a calibration run</div>
  </div>
</template>
