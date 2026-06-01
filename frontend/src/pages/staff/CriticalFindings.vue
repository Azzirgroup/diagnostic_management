<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { criticalApi, type DiagnosticReportRow } from '@/api/adms'
import { frappeError } from '@/api/client'

const router = useRouter()
const rows = ref<DiagnosticReportRow[]>([])
const selected = ref<DiagnosticReportRow | null>(null)
const tab = ref<'all' | 'unack' | 'ack'>('all')

// Peer review form (matches the detail page so the actions stay consistent
// across both views).
const outcome = ref<'Agree' | 'Minor Disagreement' | 'Major Disagreement' | 'Amendment Required'>('Agree')
const discrepancy = ref<'' | 'None' | 'Minor' | 'Major' | 'Critical'>('')
const reviewNotes = ref('')
const busy = ref(false)
const error = ref('')

async function load() {
  try { rows.value = await criticalApi.listOpen() } catch { rows.value = [] }
}
onMounted(load)

const pendingReviewCount = computed(() => rows.value.filter((r) => !r.critical_acknowledged).length)
const reviewedCount = computed(() => rows.value.filter((r) => r.critical_acknowledged).length)
const filtered = computed(() => {
  if (tab.value === 'unack') return rows.value.filter((r) => !r.critical_acknowledged)
  if (tab.value === 'ack') return rows.value.filter((r) => r.critical_acknowledged)
  return rows.value
})

function resetForm() {
  outcome.value = 'Agree'
  discrepancy.value = ''
  reviewNotes.value = ''
  error.value = ''
}
function pickRow(r: DiagnosticReportRow) {
  selected.value = r
  resetForm()
}

async function submitPeerReview() {
  if (!selected.value) return
  busy.value = true
  error.value = ''
  try {
    await criticalApi.submitPeerReview({
      report: selected.value.name,
      outcome: outcome.value,
      review_notes: reviewNotes.value,
      discrepancy_severity: discrepancy.value || undefined,
    })
    selected.value = null
    resetForm()
    await load()
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to submit peer review')
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Critical Results · Peer Review" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Peer Review" :value="pendingReviewCount" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Reviewed" :value="reviewedCount" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="All Open" :value="rows.length" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="With Review History" :value="rows.filter((r) => r.log && r.log.length).length" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-2 border-b border-surface-100">
        <button v-for="(label, key) in { all: `All (${rows.length})`, unack: `Pending Review (${pendingReviewCount})`, ack: `Reviewed (${reviewedCount})` }" :key="key"
          :class="['btn-ghost !py-1.5 !text-xs', tab === key && '!bg-brand-navy-700 !text-white !border-transparent']"
          @click="tab = key as any">
          {{ label }}
        </button>
      </div>
      <DataTable :rows="filtered" row-key="name" :selectable="true" @select="(r) => pickRow(r as any)" empty-text="No critical results"
        :columns="[
          { key: 'patient_name', label: 'Patient' },
          { key: 'name', label: 'Report ID' },
          { key: 'status', label: 'Report Status' },
          { key: 'creation', label: 'Detected' },
          { key: 'critical_acknowledged', label: 'Actions' },
        ]"
      >
        <template #cell-name="{ row, value }">
          <div class="flex flex-col">
            <button class="text-brand-teal-600 hover:underline text-left" @click.stop="router.push(`/critical-findings/${value}`)">{{ value }}</button>
            <button class="text-xs text-brand-teal-500 hover:underline text-left mt-0.5" @click.stop="router.push(`/critical-findings/${value}`)">View Full Result →</button>
          </div>
        </template>
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
        <template #cell-critical_acknowledged="{ row, value }">
          <div class="flex items-center gap-2">
            <StatusPill :status="value ? 'Reviewed' : 'Pending Review'" />
            <button v-if="!value" class="text-xs text-brand-navy-700 hover:underline" @click.stop="pickRow(row as any)">Review →</button>
          </div>
        </template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.patient_name || selected.name" :subtitle="selected.name" @close="selected = null">
      <div class="bg-surface-50 rounded-lg p-3 mb-4">
        <div class="text-sm font-semibold text-status-danger">Critical Result · Peer Review</div>
        <p class="text-sm text-surface-700 mt-1">Document: {{ selected.docname || selected.name }}</p>
        <p class="text-sm text-surface-700 mt-1">Status: {{ selected.status }}</p>
        <button class="text-xs text-brand-teal-600 hover:underline mt-2" @click="router.push(`/critical-findings/${selected.name}`)">View Full Result →</button>
      </div>
      <h4 class="font-semibold text-sm mb-2">Peer Review Timeline</h4>
      <ul class="text-xs space-y-2 mb-4">
        <li v-if="!selected.log || !selected.log.length" class="text-surface-500">No review entries yet — submit a peer review to record one</li>
        <li v-for="(l, i) in selected.log || []" :key="i" class="flex justify-between">
          <span :class="l.status === 'Acknowledged' ? 'text-status-success' : 'text-status-danger'">● {{ l.status === 'Acknowledged' ? 'Reviewed' : l.status }}</span>
          <span class="text-surface-500">{{ l.detected_at || l.acknowledged_at }}</span>
        </li>
      </ul>
      <template v-if="!selected.critical_acknowledged">
        <label class="block text-xs text-surface-500 mb-1">Outcome</label>
        <select v-model="outcome" class="input mb-3">
          <option>Agree</option>
          <option>Minor Disagreement</option>
          <option>Major Disagreement</option>
          <option>Amendment Required</option>
        </select>
        <label class="block text-xs text-surface-500 mb-1">Discrepancy Severity</label>
        <select v-model="discrepancy" class="input mb-3">
          <option value="">—</option>
          <option>None</option><option>Minor</option><option>Major</option><option>Critical</option>
        </select>
        <label class="block text-xs text-surface-500 mb-1">Reviewer Notes</label>
        <textarea v-model="reviewNotes" class="input w-full mb-3" rows="3" placeholder="Agreement / disagreement, follow-up actions..."></textarea>
        <p v-if="error" class="text-sm text-status-danger mb-2">{{ error }}</p>
        <button class="btn-primary w-full" :disabled="busy" @click="submitPeerReview">
          {{ busy ? 'Submitting…' : 'Submit Peer Review' }}
        </button>
      </template>
      <div v-else class="text-sm text-surface-500">Already reviewed.</div>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a result to review</div>
  </div>
</template>
