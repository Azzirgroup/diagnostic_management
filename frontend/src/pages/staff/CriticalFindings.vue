<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { criticalApi, type DiagnosticReportRow } from '@/api/adms'

const rows = ref<DiagnosticReportRow[]>([])
const selected = ref<DiagnosticReportRow | null>(null)
const tab = ref<'all' | 'unack' | 'ack'>('all')
const ackComment = ref('')
const busy = ref(false)

async function load() {
  try { rows.value = await criticalApi.listOpen() } catch { rows.value = [] }
}
onMounted(load)

const unackCount = computed(() => rows.value.filter((r) => !r.critical_acknowledged).length)
const ackCount = computed(() => rows.value.filter((r) => r.critical_acknowledged).length)
const filtered = computed(() => {
  if (tab.value === 'unack') return rows.value.filter((r) => !r.critical_acknowledged)
  if (tab.value === 'ack') return rows.value.filter((r) => r.critical_acknowledged)
  return rows.value
})

async function acknowledge() {
  if (!selected.value) return
  busy.value = true
  try {
    await criticalApi.acknowledge(selected.value.name, ackComment.value)
    ackComment.value = ''
    selected.value = null
    await load()
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Critical Findings" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Unacknowledged" :value="unackCount" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Acknowledged" :value="ackCount" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="All Open" :value="rows.length" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="With Log Entries" :value="rows.filter((r) => r.log && r.log.length).length" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-2 border-b border-surface-100">
        <button v-for="(label, key) in { all: `All (${rows.length})`, unack: `Unacknowledged (${unackCount})`, ack: `Acknowledged (${ackCount})` }" :key="key"
          :class="['btn-ghost !py-1.5 !text-xs', tab === key && '!bg-brand-navy-700 !text-white !border-transparent']"
          @click="tab = key as any">
          {{ label }}
        </button>
      </div>
      <DataTable :rows="filtered" row-key="name" :selectable="true" @select="(r) => (selected = r as any)" empty-text="No critical findings"
        :columns="[
          { key: 'patient_name', label: 'Patient' },
          { key: 'name', label: 'Report ID' },
          { key: 'status', label: 'Report Status' },
          { key: 'creation', label: 'Detected' },
          { key: 'critical_acknowledged', label: 'Ack.' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
        <template #cell-critical_acknowledged="{ value }">
          <StatusPill :status="value ? 'Acknowledged' : 'Pending'" />
        </template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.patient_name || selected.name" :subtitle="selected.name" @close="selected = null">
      <div class="bg-surface-50 rounded-lg p-3 mb-4">
        <div class="text-sm font-semibold text-status-danger">Critical Diagnostic Report</div>
        <p class="text-sm text-surface-700 mt-1">Document: {{ selected.docname || selected.name }}</p>
        <p class="text-sm text-surface-700 mt-1">Status: {{ selected.status }}</p>
      </div>
      <h4 class="font-semibold text-sm mb-2">Escalation Timeline</h4>
      <ul class="text-xs space-y-2 mb-4">
        <li v-if="!selected.log || !selected.log.length" class="text-surface-500">No log entries (acknowledge to create one)</li>
        <li v-for="(l, i) in selected.log || []" :key="i" class="flex justify-between">
          <span :class="l.status === 'Acknowledged' ? 'text-status-success' : 'text-status-danger'">● {{ l.status }}</span>
          <span class="text-surface-500">{{ l.detected_at || l.acknowledged_at }}</span>
        </li>
      </ul>
      <label class="block text-xs text-surface-500 mb-1">Notes (Optional)</label>
      <textarea v-model="ackComment" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="3" placeholder="Add notes about acknowledgment..."></textarea>
      <button class="btn-primary w-full mt-4" :disabled="busy || !!selected.critical_acknowledged" @click="acknowledge">
        {{ selected.critical_acknowledged ? 'Already Acknowledged' : 'Acknowledge' }}
      </button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a finding</div>
  </div>
</template>
