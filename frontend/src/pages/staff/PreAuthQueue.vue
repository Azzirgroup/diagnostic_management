<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { radiologyApi, type PreAuthRow } from '@/api/adms'

const rows = ref<PreAuthRow[]>([])
const selected = ref<PreAuthRow | null>(null)
const approvedAmount = ref<number | null>(null)
const approvalRef = ref('')
const denialReason = ref('')
const busy = ref(false)

async function load() {
  try { rows.value = await radiologyApi.preAuthQueue(undefined, 200) } catch { rows.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  const draft = rows.value.filter((r) => r.status === 'Draft').length
  const pending = rows.value.filter((r) => r.status === 'Submitted' || r.status === 'In Review').length
  const approvedToday = rows.value.filter((r) => r.status === 'Approved' && (r.submitted_date || '').startsWith(today)).length
  const expiring = rows.value.filter((r) => r.status === 'Approved').length
  return { draft, pending, approvedToday, expiring }
})

async function submitOne() {
  if (!selected.value) return
  busy.value = true
  try { await radiologyApi.submitPreAuth(selected.value.name); await load() } finally { busy.value = false }
}
async function decide(decision: 'Approved' | 'Denied') {
  if (!selected.value) return
  busy.value = true
  try {
    await radiologyApi.decidePreAuth({
      name: selected.value.name,
      decision,
      approved_amount: decision === 'Approved' ? approvedAmount.value ?? undefined : undefined,
      approval_reference: decision === 'Approved' ? approvalRef.value || undefined : undefined,
      denial_reason: decision === 'Denied' ? denialReason.value || undefined : undefined,
    })
    approvedAmount.value = null
    approvalRef.value = ''
    denialReason.value = ''
    selected.value = null
    await load()
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Pre-Auth Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Awaiting Submission" :value="kpis.draft" sub="Draft requests" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Pending Approval" :value="kpis.pending" sub="Submitted / In Review" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Approved Today" :value="kpis.approvedToday" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Approved (active)" :value="kpis.expiring" sub="Across queue" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" row-key="name" :selectable="true" @select="(r) => (selected = r as any)"
        empty-text="No pre-auth requests"
        :columns="[
          { key: 'name', label: 'Request ID' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'payor', label: 'Payor' },
          { key: 'modality', label: 'Modality' },
          { key: 'urgency', label: 'Urgency' },
          { key: 'submitted_date', label: 'Submitted' },
          { key: 'estimated_amount', label: 'Estimated' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Payor</dt><dd>{{ selected.payor || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Modality</dt><dd>{{ selected.modality || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Urgency</dt><dd>{{ selected.urgency || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Estimated</dt><dd>{{ selected.estimated_amount ?? '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status"/></dd></div>
      </dl>
      <button v-if="selected.status === 'Draft'" class="btn-primary w-full mt-6" :disabled="busy" @click="submitOne">Submit to Payor</button>

      <div v-if="selected.status === 'Submitted' || selected.status === 'In Review'" class="mt-6 space-y-2">
        <input v-model.number="approvedAmount" type="number" placeholder="Approved amount" class="w-full px-3 py-2 rounded border border-surface-200 text-sm" />
        <input v-model="approvalRef" placeholder="Approval reference #" class="w-full px-3 py-2 rounded border border-surface-200 text-sm" />
        <button class="btn-primary w-full" :disabled="busy" @click="decide('Approved')">Mark Approved</button>
        <input v-model="denialReason" placeholder="Denial reason" class="w-full px-3 py-2 rounded border border-surface-200 text-sm" />
        <button class="btn-danger-ghost w-full" :disabled="busy" @click="decide('Denied')">Mark Denied</button>
      </div>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a pre-auth request</div>
  </div>
</template>
