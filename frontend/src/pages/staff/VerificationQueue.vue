<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { labApi, resultsApi, type DiagnosticReportRow } from '@/api/adms'
import { frappeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()
const rows = ref<DiagnosticReportRow[]>([])
const selected = ref<DiagnosticReportRow | null>(null)
const detail = ref<Awaited<ReturnType<typeof labApi.diagnosticReportDetail>> | null>(null)
const detailLoading = ref(false)
const comment = ref('')
const busy = ref(false)
const peerBusy = ref(false)
const err = ref('')

async function load() {
  try { rows.value = await labApi.verificationQueue(100) } catch { rows.value = [] }
}
onMounted(load)

// Load full detail (analytes + peer review status + urgent gate) whenever
// a row is selected, so the sidebar can show more than just the header
// fields and the Verify button can gate itself the same way the workflow
// and the full detail page do.
watch(selected, async (r) => {
  detail.value = null; err.value = ''; comment.value = ''
  if (!r) return
  detailLoading.value = true
  try {
    detail.value = await labApi.diagnosticReportDetail(r.name)
    comment.value = detail.value?.report?.conclusion || ''
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to load report')
  } finally { detailLoading.value = false }
})

const kpis = computed(() => {
  const total = rows.value.length
  const critical = rows.value.filter((r) => r.is_critical).length
  return { total, critical }
})

const peerReviewPassed = computed(() => !!detail.value?.report?.custom_peer_reviewed)
const pendingCase = computed(() => detail.value?.peer_review_case)
const isOriginalReporter = computed(() =>
  !!pendingCase.value?.original_reporter &&
  pendingCase.value.original_reporter === auth.user?.name,
)
const canApprovePeer = computed(() =>
  !!pendingCase.value && !peerReviewPassed.value && !isOriginalReporter.value,
)
const isUrgent = computed(() => !!detail.value?.report?.is_urgent)
const urgentAuthorized = computed(() => detail.value?.report?.urgent_review_status === 'Authorized')
const verifyAllowed = computed(() =>
  !!selected.value && peerReviewPassed.value && (!isUrgent.value || urgentAuthorized.value),
)

async function approvePeer() {
  if (!pendingCase.value) return
  peerBusy.value = true; err.value = ''
  try {
    await labApi.submitPeerReview({
      name: pendingCase.value.name, outcome: 'Agree',
      review_notes: 'Approved from Verification Queue — analytes reviewed inline.',
    })
    // Reload the detail so peerReviewPassed flips true and Verify unlocks.
    if (selected.value) {
      detail.value = await labApi.diagnosticReportDetail(selected.value.name)
    }
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to approve peer review')
  } finally { peerBusy.value = false }
}

// Urgent authorization — server enforces the "Urgent Review Officer" role.
// Show the button whenever the user has that role; server rejects otherwise.
const canAuthorizeUrgent = computed(() => auth.roles.includes('Urgent Review Officer'))
const urgentBusy = ref(false)
async function authorizeUrgent() {
  if (!detail.value?.sample?.name) return
  urgentBusy.value = true; err.value = ''
  try {
    await resultsApi.authorizeUrgent(detail.value.sample.name)
    if (selected.value) {
      detail.value = await labApi.diagnosticReportDetail(selected.value.name)
    }
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to authorize urgent review')
  } finally { urgentBusy.value = false }
}
const analyteCount = computed(() =>
  (detail.value?.lab_tests || []).reduce((s, t) => s + (t.normal_test_items?.length || 0), 0),
)

async function verify() {
  if (!selected.value || !verifyAllowed.value) return
  busy.value = true; err.value = ''
  try {
    // Use approve_report so the release goes through the SAME server gate
    // as the workflow's Verify & Release (peer review + urgent + sign-off).
    await resultsApi.approve({
      report: selected.value.name,
      conclusion: comment.value || undefined,
    })
    selected.value = null
    await load()
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to verify & release')
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
        <template #cell-name="{ value }">
          <button class="text-brand-teal-600 hover:underline"
                  @click.stop="router.push(`/lab/verification/${value}`)">{{ value }}</button>
        </template>
        <template #cell-is_critical="{ value }">
          <span v-if="value" class="text-status-danger font-semibold">Yes</span>
          <span v-else class="text-surface-400">—</span>
        </template>
        <template #cell-status="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Created</dt><dd>{{ selected.creation?.split('.')[0] }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reporter</dt><dd>{{ selected.practitioner || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Critical</dt><dd>{{ selected.is_critical ? 'Yes' : 'No' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
        <div v-if="detail" class="flex justify-between"><dt class="text-surface-500">Sample</dt><dd>{{ detail.sample?.name || '—' }}</dd></div>
        <div v-if="detail" class="flex justify-between"><dt class="text-surface-500">Lab Tests</dt><dd>{{ detail.lab_tests?.length || 0 }} ({{ analyteCount }} analytes)</dd></div>
        <div v-if="detail" class="flex justify-between"><dt class="text-surface-500">Peer Review</dt>
          <dd>
            <span v-if="peerReviewPassed" class="text-emerald-700 font-medium">Passed ✓</span>
            <span v-else-if="detail.peer_review_case" class="text-amber-700">Awaiting</span>
            <span v-else class="text-surface-400">—</span>
          </dd>
        </div>
        <div v-if="isUrgent" class="flex justify-between"><dt class="text-surface-500">Urgent Review</dt>
          <dd>
            <span v-if="urgentAuthorized" class="text-emerald-700 font-medium">Authorized ✓</span>
            <span v-else class="text-amber-700">{{ detail?.report?.urgent_review_status || 'Pending' }}</span>
          </dd>
        </div>
      </dl>

      <button class="btn-ghost w-full mt-3 !text-xs"
              @click="router.push(`/lab/verification/${selected.name}`)">
        Open full detail page →
      </button>
      <button v-if="detail?.workflow_session" class="btn-ghost w-full mt-2 !text-xs"
              @click="router.push(`/workflow/${detail.workflow_session}`)">
        ↩ Open Lab Workflow ({{ detail.workflow_session }})
      </button>

      <div v-if="detailLoading" class="text-xs text-surface-400 mt-3">Loading results…</div>

      <label class="block text-xs text-surface-500 mt-4 mb-1">Conclusion (saved on verify)</label>
      <textarea v-model="comment" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="3" placeholder="Add a final conclusion / sign-off note..."></textarea>
      <!-- Peer review inline — same button as workflow. Any user who is
           NOT the original reporter can close the case in one click. -->
      <button v-if="canApprovePeer" class="btn-primary w-full mt-3"
              :disabled="peerBusy" @click="approvePeer">
        {{ peerBusy ? 'Approving…' : '✓ Approve Peer Review' }}
      </button>
      <div v-else-if="pendingCase && isOriginalReporter"
           class="mt-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
        You entered these results — someone else must peer-review this case first.
      </div>
      <!-- Urgent authorization inline — server enforces the URR role. -->
      <button v-if="isUrgent && !urgentAuthorized && canAuthorizeUrgent"
              class="btn-primary w-full mt-3 !bg-red-600 hover:!bg-red-700"
              :disabled="urgentBusy" @click="authorizeUrgent">
        {{ urgentBusy ? 'Authorizing…' : '⚡ Authorize Urgent Review' }}
      </button>
      <div v-else-if="isUrgent && !urgentAuthorized"
           class="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
        Urgent case — you don't have the <strong>Urgent Review Officer</strong> role.
      </div>
      <button class="btn-primary w-full mt-3"
              :disabled="busy || !verifyAllowed"
              :title="verifyAllowed ? '' : (!peerReviewPassed ? 'Peer review must be closed first' : (isUrgent && !urgentAuthorized ? 'Urgent review must be authorized first' : ''))"
              @click="verify">
        {{ busy ? 'Releasing…' : 'Verify & Release' }}
      </button>
      <p v-if="!verifyAllowed && !detailLoading && detail" class="text-xs text-amber-600 mt-2">
        <span v-if="!peerReviewPassed">Awaiting Peer Review — close the peer review case first.</span>
        <span v-else-if="isUrgent && !urgentAuthorized">Urgent — awaits Urgent Review Officer authorization.</span>
      </p>
      <p v-if="err" class="text-xs text-status-danger mt-2">{{ err }}</p>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a report to verify</div>
  </div>
</template>
