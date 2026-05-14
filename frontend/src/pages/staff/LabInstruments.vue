<script setup lang="ts">
import { ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'

const selected = ref<any>(null)
// Until the Lab Instrument doctype lands, this view renders the layout with placeholder rows.
const rows = [
  { name: 'Sysmex XN-550', section: 'Hematology', model: 'XN-550', interface: 'Online', location: 'Hematology · Bench 1', last_maintenance: 'May 10, 2025', state: 'Operational' },
  { name: 'Roche Cobas 6000', section: 'Biochemistry', model: 'cobas 6000', interface: 'Online', location: 'Biochemistry · Bench 1', last_maintenance: 'May 02, 2025', state: 'Operational' },
  { name: 'Mindray BS-240', section: 'Chemistry', model: 'BS-240', interface: 'Degraded', location: 'Chemistry · Bench 1', last_maintenance: 'Apr 20, 2025', state: 'Warning' },
  { name: 'Thermo Fisher Indiko Plus', section: 'Urinalysis', model: 'Indiko Plus', interface: 'Offline', location: 'Urinalysis · Bench 1', last_maintenance: 'May 18, 2025', state: 'Offline' },
]
</script>

<template>
  <Topbar title="Lab Instruments" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Online" :value="24" delta="3 vs yesterday" delta-direction="up" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Offline" :value="4" delta="1 vs yesterday" delta-direction="down" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Maintenance Due" :value="6" delta="2 vs yesterday" delta-direction="up" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Error State" :value="2" delta="1 vs yesterday" delta-direction="down" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r)"
        :columns="[
          { key: 'name', label: 'Instrument' },
          { key: 'section', label: 'Section' },
          { key: 'model', label: 'Model' },
          { key: 'interface', label: 'Interface' },
          { key: 'location', label: 'Location' },
          { key: 'last_maintenance', label: 'Last Maintenance' },
          { key: 'state', label: 'State' },
        ]"
      >
        <template #cell-state="{ value }"><StatusPill :status="value as string" /></template>
        <template #cell-interface="{ value }">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full" :class="value === 'Online' ? 'bg-status-success' : value === 'Offline' ? 'bg-status-danger' : 'bg-status-warning'"/>
            {{ value }}
          </div>
        </template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.section + ' · ' + selected.model" @close="selected = null">
      <div class="space-y-3 text-sm">
        <div class="flex justify-between"><span class="text-surface-500">Status</span><StatusPill :status="selected.state" /></div>
        <div class="flex justify-between"><span class="text-surface-500">Interface</span><span>{{ selected.interface }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Last Maintenance</span><span>{{ selected.last_maintenance }}</span></div>
      </div>
      <button class="btn-primary w-full mt-6">Open Maintenance</button>
      <button class="btn-ghost w-full mt-2">View Logs</button>
      <button class="btn-danger-ghost w-full mt-2">Set Offline</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select an instrument</div>
  </div>
</template>
