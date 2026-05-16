<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { instrumentsApi, type LabInstrumentRow } from '@/api/adms'

const rows = ref<LabInstrumentRow[]>([])
const selected = ref<LabInstrumentRow | null>(null)

async function load() {
  try { rows.value = await instrumentsApi.monitor() } catch { rows.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const online = rows.value.filter((r) => r.state === 'Operational').length
  const warning = rows.value.filter((r) => r.state === 'Warning').length
  const error = rows.value.filter((r) => r.state === 'Error' || r.state === 'Offline').length
  const lastSync = rows.value.reduce((acc: string | undefined, r) => {
    if (!r.last_heartbeat) return acc
    return acc && acc > r.last_heartbeat ? acc : r.last_heartbeat
  }, undefined)
  return { online, warning, error, lastSync: lastSync || '—' }
})
</script>

<template>
  <Topbar title="Analyzer Interface Monitor" subtitle="Live state of instrument interfaces driven by heartbeats." />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Online" :value="kpis.online" sub="Operational" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Warnings" :value="kpis.warning" sub="Degraded" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Errors / Offline" :value="kpis.error" sub="Needs attention" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Last Heartbeat" :value="kpis.lastSync" sub="Across fleet" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        empty-text="No instruments registered"
        @select="(r) => (selected = r as any)"
        :columns="[
          { key: 'instrument_name', label: 'Instrument' },
          { key: 'section', label: 'Section' },
          { key: 'interface_type', label: 'Interface' },
          { key: 'state', label: 'State' },
          { key: 'last_heartbeat', label: 'Last Heartbeat' },
          { key: 'stale', label: 'Stale (>10m)' },
        ]"
      >
        <template #cell-state="{ value }"><StatusPill :status="value as string" /></template>
        <template #cell-stale="{ value }">
          <span :class="value ? 'text-status-danger' : 'text-status-success'">{{ value ? 'Yes' : 'No' }}</span>
        </template>
      </DataTable>
    </div>
    <div v-if="selected" class="card p-5">
      <div class="flex items-center justify-between">
        <h3 class="font-semibold">{{ selected.instrument_name }}</h3>
        <StatusPill :status="selected.state"/>
      </div>
      <dl class="text-sm space-y-2 mt-3">
        <div class="flex justify-between"><dt class="text-surface-500">Section</dt><dd>{{ selected.section || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Interface</dt><dd>{{ selected.interface_type || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Host</dt><dd>{{ selected.host || '—' }}{{ selected.port ? `:${selected.port}` : '' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Last Heartbeat</dt><dd>{{ selected.last_heartbeat || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Stale</dt><dd>{{ selected.stale ? 'Yes' : 'No' }}</dd></div>
      </dl>
    </div>
    <div v-else class="card p-6 text-center text-surface-400">Select an instrument to inspect</div>
  </div>
</template>
