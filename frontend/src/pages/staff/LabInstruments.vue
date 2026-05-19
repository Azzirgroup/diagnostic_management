<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { instrumentsApi, type LabInstrumentRow } from '@/api/adms'

const rows = ref<LabInstrumentRow[]>([])
const selected = ref<LabInstrumentRow | null>(null)
const busy = ref(false)

async function load() {
  try { rows.value = await instrumentsApi.list() } catch { rows.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const operational = rows.value.filter((r) => r.state === 'Operational').length
  const offline = rows.value.filter((r) => r.state === 'Offline').length
  const warning = rows.value.filter((r) => r.state === 'Warning').length
  const error = rows.value.filter((r) => r.state === 'Error').length
  return { operational, offline, warning, error }
})

async function setState(newState: string) {
  if (!selected.value) return
  busy.value = true
  try {
    await instrumentsApi.setState(selected.value.name, newState)
    await load()
    selected.value = rows.value.find((r) => r.name === selected.value?.name) || null
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Lab Instruments" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Operational" :value="kpis.operational" sub="Live and reporting" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Offline" :value="kpis.offline" sub="No heartbeat" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Warning" :value="kpis.warning" sub="Degraded" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Error" :value="kpis.error" sub="Requires service" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        empty-text="No instruments configured"
        @select="(r) => (selected = r as any)"
        :columns="[
          { key: 'instrument_name', label: 'Instrument' },
          { key: 'section', label: 'Section' },
          { key: 'model', label: 'Model' },
          { key: 'interface_type', label: 'Interface' },
          { key: 'location', label: 'Location' },
          { key: 'last_maintenance', label: 'Last Maintenance' },
          { key: 'state', label: 'State' },
        ]"
      >
        <template #cell-instrument_name="{ value }">
          <button class="text-brand-teal-600 hover:underline" @click.stop="$router.push(`/lab/instrument/${value}`)">{{ value }}</button>
        </template>
        <template #cell-state="{ value }"><StatusPill :status="value as string" /></template>
        <template #cell-interface_type="{ value }">
          <div class="flex items-center gap-1.5">
            <span class="w-2 h-2 rounded-full bg-status-success" />
            {{ value || 'Manual' }}
          </div>
        </template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.instrument_name" :subtitle="(selected.section || '—') + ' · ' + (selected.model || '—')" @close="selected = null">
      <div class="space-y-3 text-sm">
        <div class="flex justify-between"><span class="text-surface-500">State</span><StatusPill :status="selected.state" /></div>
        <div class="flex justify-between"><span class="text-surface-500">Interface</span><span>{{ selected.interface_type || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Manufacturer</span><span>{{ selected.manufacturer || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Serial</span><span>{{ selected.serial_number || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Last Maintenance</span><span>{{ selected.last_maintenance || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Last Heartbeat</span><span>{{ selected.last_heartbeat || '—' }}</span></div>
        <div class="flex justify-between"><span class="text-surface-500">Host</span><span>{{ selected.host || '—' }}{{ selected.port ? `:${selected.port}` : '' }}</span></div>
      </div>
      <button class="btn-primary w-full mt-6" :disabled="busy" @click="setState('Maintenance')">Open Maintenance</button>
      <button class="btn-ghost w-full mt-2" :disabled="busy" @click="setState('Operational')">Mark Operational</button>
      <button class="btn-danger-ghost w-full mt-2" :disabled="busy" @click="setState('Offline')">Set Offline</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select an instrument</div>
  </div>
</template>
