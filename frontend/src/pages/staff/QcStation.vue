<script setup lang="ts">
import { ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'

const selected = ref<any>(null)
const rows = [
  { analyzer: 'Sysmex XN-1000', level: 'Level 2', lot: 'XN22345', section: 'CBC', run_time: 'May 22, 2025 09:42 AM', result: 'Failed', flag: '1_3s' },
  { analyzer: 'Cobas c311', level: 'Level 1', lot: 'CHM5567', section: 'Chemistry', run_time: 'May 22, 2025 09:35 AM', result: 'Passed', flag: '—' },
  { analyzer: 'Abbott Alinity i', level: 'Level 1', lot: 'IMM7789', section: 'Immunology', run_time: 'May 22, 2025 09:28 AM', result: 'Passed', flag: '—' },
  { analyzer: 'Sysmex XN-1000', level: 'Level 1', lot: 'XN22344', section: 'CBC', run_time: 'May 22, 2025 09:16 AM', result: 'Failed', flag: '2_2s' },
]
</script>

<template>
  <Topbar title="QC Station" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending QC Runs" :value="18" delta="4 from yesterday" delta-direction="down" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Failed Controls" :value="3" delta="1 from yesterday" delta-direction="up" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Instruments Due" :value="5" sub="No change" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Today's Pass Rate" :value="'96.4%'" delta="2.1% vs yesterday" delta-direction="up" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        :selectable="true"
        @select="(r) => (selected = r)"
        :columns="[
          { key: 'analyzer', label: 'Analyzer' },
          { key: 'level', label: 'Control Level' },
          { key: 'lot', label: 'Lot Number' },
          { key: 'section', label: 'Section' },
          { key: 'run_time', label: 'Run Time' },
          { key: 'result', label: 'Result' },
          { key: 'flag', label: 'Westgard Flag' },
        ]"
      >
        <template #cell-result="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.analyzer" :subtitle="selected.section + ' · Level ' + selected.level" @close="selected = null">
      <div class="text-sm space-y-3">
        <div class="flex justify-between"><span class="text-surface-500">Lot Number</span><span>{{ selected.lot }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Run Time</span><span>{{ selected.run_time }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Result</span><StatusPill :status="selected.result"/></div>
      </div>
      <h4 class="mt-4 font-semibold text-sm">Rule Violations (Westgard)</h4>
      <div class="card p-3 mt-2 text-xs">
        <div class="font-mono text-status-danger">{{ selected.flag }}</div>
        <div class="text-surface-500 mt-1">One control exceeds ±3 SD · Run 10: -2.9 SD</div>
      </div>
      <button class="btn-primary w-full mt-6">Approve Run</button>
      <button class="btn-danger-ghost w-full mt-2">Reject Run</button>
      <button class="btn-ghost w-full mt-2">Open Corrective Action</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a QC run</div>
  </div>
</template>
