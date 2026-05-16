<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { labApi, type DiagnosticReportRow } from '@/api/adms'

const rows = ref<DiagnosticReportRow[]>([])
const selected = ref<DiagnosticReportRow | null>(null)
const comment = ref('')
const amendmentReason = ref('')
const busy = ref(false)

async function load() {
  try { rows.value = await labApi.verificationQueue(100) } catch { rows.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const total = rows.value.length
  const critical = rows.value.filter((r) => r.is_critical).length
  return { total, critical }
})

async function verify() {
  if (!selected.value) return
  busy.value = true
  try {
    await labApi.verify(selected.value.name, comment.value || undefined)
    comment.value = ''
    selected.value = null
    await load()
  } finally { busy.value = false }
}
async function amend() {
  if (!selected.value || !amendmentReason.value.trim()) return
  busy.value = true
  try {
    await labApi.amend(selected.value.name, amendmentReason.value)
    amendmentReason.value = ''
    selected.value = null
    await load()
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Verification Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Verification" :value="kpis.total" sub="Draft or Pending status" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Critical Flagged" :value="kpis.critical" sub="Requires acknowledgement" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Peer Reviews" :value="0" sub="See Peer Review page" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Avg Sign-off" :value="'—'" sub="TBD" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r as any)"
        empty-text="Verification queue is clear"
        :columns="[
          { key: 'name', label: 'Report' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'practitioner', label: 'Reporter' },
          { key: 'creation', label: 'Created' },
          { key: 'is_critical', label: 'Critical' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-is_critical="{ value }">
          <span v-if="value" class="text-status-danger font-semibold">Yes</span>
          <span v-else class="text-surface-400">—</span>
        </template>
        <template #cell-status="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
      <dl class="text-sm space-y-3">
        <div class="flex justify-between"><dt class="text-surface-500">Created</dt><dd>{{ selected.creation?.split('.')[0] }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reporter</dt><dd>{{ selected.practitioner || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Critical</dt><dd>{{ selected.is_critical ? 'Yes' : 'No' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
      </dl>
      <label class="block text-xs text-surface-500 mt-4 mb-1">Conclusion (saved on verify)</label>
      <textarea v-model="comment" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="3" placeholder="Add a final conclusion / sign-off note..."></textarea>
      <button class="btn-primary w-full mt-4" :disabled="busy" @click="verify">Verify &amp; Release</button>
      <label class="block text-xs text-surface-500 mt-4 mb-1">Amendment Reason</label>
      <input v-model="amendmentReason" class="w-full px-3 py-2 rounded border border-surface-200 text-sm" placeholder="Why is amendment needed?" />
      <button class="btn-ghost w-full mt-2" :disabled="busy || !amendmentReason.trim()" @click="amend">Request Amendment</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a report to verify</div>
  </div>
</template>
