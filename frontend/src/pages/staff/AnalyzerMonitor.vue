<script setup lang="ts">
import { ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'

const selected = ref<any>(null)
const rows = [
  { instrument: 'Hematology Analyzer (XN-550) · IFACE-XN550', status: 'Online', queue: 0, last_sample: 'SMP-25-11452', last_message: '10:25:34 AM · Live', error: '—' },
  { instrument: 'Biochemistry Analyzer (AU680) · IFACE-AU680', status: 'Online', queue: 3, last_sample: 'SMP-25-11449', last_message: '10:25:18 AM · Live', error: '—' },
  { instrument: 'CLIA Analyzer (iFlash 3000) · IFACE-IF3000', status: 'Warning', queue: 12, last_sample: 'SMP-25-11441', last_message: '10:24:02 AM · 3 min ago', error: 'Delayed' },
  { instrument: 'Blood Gas Analyzer (ABL90) · IFACE-ABL90', status: 'Error', queue: 0, last_sample: 'SMP-25-11438', last_message: '10:15:42 AM · 10 min ago', error: 'Connection Lost' },
]
</script>

<template>
  <Topbar title="Analyzer Interface Monitor" subtitle="Real-time monitoring of instrument interfaces and HL7 message traffic." />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Online Instruments" :value="12" delta="1 from yesterday" delta-direction="up" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Pending Messages" :value="64" delta="8 from yesterday" delta-direction="up" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Failed Messages" :value="3" delta="2 from yesterday" delta-direction="down" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Last Sync" :value="'1 min ago'" sub="Auto-sync active" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        :selectable="true"
        @select="(r) => (selected = r)"
        :columns="[
          { key: 'instrument', label: 'Instrument / Interface' },
          { key: 'status', label: 'Status' },
          { key: 'queue', label: 'Queue Depth' },
          { key: 'last_sample', label: 'Last Sample' },
          { key: 'last_message', label: 'Last Message' },
          { key: 'error', label: 'Error State' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <div v-if="selected" class="card p-5">
      <div class="flex items-center justify-between">
        <h3 class="font-semibold">{{ selected.instrument.split('·')[0].trim() }}</h3>
        <StatusPill :status="selected.status"/>
      </div>
      <h4 class="font-semibold text-sm mt-4">Recent HL7 Traffic</h4>
      <ul class="text-xs font-mono space-y-1 mt-2">
        <li class="flex justify-between"><span>10:25:18 AM ORU^R01</span><span class="text-status-success">✓ ACK</span></li>
        <li class="flex justify-between"><span>10:25:17 AM ORU^R01</span><span class="text-status-success">✓ ACK</span></li>
        <li class="flex justify-between"><span>10:25:14 AM ORU^R01</span><span class="text-status-warning">⧖ Queued</span></li>
      </ul>
      <button class="btn-primary w-full mt-6">Retry Failed</button>
      <button class="btn-ghost w-full mt-2">Acknowledge / Resolve</button>
    </div>
    <div v-else class="card p-6 text-center text-surface-400">Select an instrument to inspect</div>
  </div>
</template>
