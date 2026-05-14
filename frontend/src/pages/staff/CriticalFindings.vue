<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { getList } from '@/api/client'

interface CriticalRow {
  name: string
  patient: string
  order: string
  dept: string
  finding: string
  detected: string
  assigned: string
  status: string
  timer: string
}

const selected = ref<CriticalRow | null>(null)
const tab = ref<'all' | 'unack' | 'escalated' | 'ack'>('all')
const ackComment = ref('')
const rows = ref<CriticalRow[]>([])

const unackCount = computed(() => rows.value.filter((r) => r.status === 'Unack.').length)
const ackCount = computed(() => rows.value.filter((r) => r.status === 'Acknowledged').length)

async function load() {
  try {
    const data = await getList<{ name: string; patient_name: string; docname: string; modified: string; is_critical: number; critical_acknowledged: number }>({
      doctype: 'Diagnostic Report',
      fields: ['name', 'patient_name', 'docname', 'modified', 'is_critical', 'critical_acknowledged'],
      filters: { is_critical: 1 },
      limit_page_length: 50,
      order_by: 'modified desc',
    })
    rows.value = data.map((d) => ({
      name: d.name,
      patient: d.patient_name || d.name,
      order: d.docname || d.name,
      dept: '—',
      finding: '—',
      detected: d.modified?.split('.')[0] || '—',
      assigned: '—',
      status: d.critical_acknowledged ? 'Acknowledged' : 'Unack.',
      timer: '—',
    }))
  } catch {
    rows.value = []
  }
}
onMounted(load)
</script>

<template>
  <Topbar title="Critical Findings" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Unacknowledged" :value="unackCount" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Escalated" :value="0" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Acknowledged" :value="ackCount" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Breached SLA" :value="0" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-2 border-b border-surface-100">
        <button v-for="(label, key) in { all: `All (${rows.length})`, unack: `Unacknowledged (${unackCount})`, escalated: 'Escalated', ack: `Acknowledged (${ackCount})` }" :key="key"
          :class="['btn-ghost !py-1.5 !text-xs', tab === key && '!bg-brand-navy-700 !text-white !border-transparent']"
          @click="tab = key as any">
          {{ label }}
        </button>
      </div>
      <DataTable :rows="rows" :selectable="true" :initial-selected-index="0" @select="(r) => (selected = r as CriticalRow)" empty-text="No critical findings"
        :columns="[
          { key: 'patient', label: 'Patient' },
          { key: 'order', label: 'Order / Study ID' },
          { key: 'dept', label: 'Dept.' },
          { key: 'finding', label: 'Critical Finding / Summary' },
          { key: 'detected', label: 'Detected' },
          { key: 'assigned', label: 'Assigned To' },
          { key: 'status', label: 'Ack. Status' },
          { key: 'timer', label: 'Escalation Timer' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
        <template #cell-timer="{ value }"><span class="text-status-danger font-mono">{{ value }}</span></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.patient.split('·')[0].trim()" :subtitle="selected.order" @close="selected = null">
      <div class="bg-status-danger-bg/40 border border-status-danger/30 rounded-lg p-3 mb-4">
        <div class="text-sm font-semibold text-status-danger">Finding / Report Snippet</div>
        <p class="text-sm text-surface-700 mt-1">{{ selected.finding }}</p>
      </div>
      <h4 class="font-semibold text-sm mb-2">Escalation Timeline</h4>
      <ul class="text-xs space-y-2 mb-4">
        <li class="flex justify-between"><span class="text-status-success">● Detected</span><span class="text-surface-500">{{ selected.detected }}</span></li>
        <li class="flex justify-between"><span class="text-status-danger">● Unacknowledged</span><span class="text-surface-500">Auto-generated alert</span></li>
      </ul>
      <label class="block text-xs text-surface-500 mb-1">Notes (Optional)</label>
      <textarea v-model="ackComment" class="input" rows="3" placeholder="Add notes about acknowledgment..."></textarea>
      <button class="btn-primary w-full mt-4">Acknowledge</button>
      <button class="btn-secondary w-full mt-2">Escalate Again</button>
      <button class="btn-ghost w-full mt-2">Call Log</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a finding</div>
  </div>
</template>
