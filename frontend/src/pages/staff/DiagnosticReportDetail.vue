<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { labApi, resultsApi } from '@/api/adms'
import { frappeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

// Full-page detail for a Diagnostic Report — mirrors PeerReviewDetail's
// shape. Everything a verifier needs (analyte tables, sample, peer-review
// status, urgent gate) on one screen, plus the Verify & Release action.
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const reportName = computed(() => String(route.params.name || ''))
const detail = ref<Awaited<ReturnType<typeof labApi.diagnosticReportDetail>> | null>(null)
const loading = ref(true)
const err = ref('')
const conclusion = ref('')
const busy = ref(false)
const peerApproveBusy = ref(false)

async function load() {
  loading.value = true; err.value = ''
  try {
    detail.value = await labApi.diagnosticReportDetail(reportName.value)
    conclusion.value = detail.value?.report?.conclusion || ''
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to load report')
  } finally { loading.value = false }
}
onMounted(load)

const isReleased = computed(() => detail.value?.report?.status === 'Approved')
const isUrgent = computed(() => !!detail.value?.report?.is_urgent)
const urgentAuthorized = computed(() => detail.value?.report?.urgent_review_status === 'Authorized')
const peerReviewPassed = computed(() => !!detail.value?.report?.custom_peer_reviewed)
const pendingCase = computed(() => detail.value?.peer_review_case)
const isOriginalReporter = computed(() =>
  !!pendingCase.value?.original_reporter &&
  pendingCase.value.original_reporter === auth.user?.name,
)
const canApprovePeer = computed(() =>
  !!pendingCase.value && !peerReviewPassed.value && !isOriginalReporter.value,
)
const verifyAllowed = computed(() =>
  !isReleased.value && peerReviewPassed.value && (!isUrgent.value || urgentAuthorized.value),
)

async function verify() {
  if (!verifyAllowed.value) return
  busy.value = true; err.value = ''
  try {
    // approve_report is the source-of-truth release endpoint (matches the
    // workflow's Verify & Release button so gates behave identically).
    await resultsApi.approve({
      report: reportName.value,
      conclusion: conclusion.value || undefined,
    })
    await load()
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to verify & release')
  } finally { busy.value = false }
}

async function approvePeer() {
  if (!pendingCase.value) return
  peerApproveBusy.value = true; err.value = ''
  try {
    await labApi.submitPeerReview({
      name: pendingCase.value.name, outcome: 'Agree',
      review_notes: 'Approved from Verification page — analytes reviewed inline.',
    })
    await load()
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to approve peer review')
  } finally { peerApproveBusy.value = false }
}

// Urgent authorization — server enforces the URR role. Show the button
// whenever the user has that role; server rejects otherwise.
const canAuthorizeUrgent = computed(() => auth.roles.includes('Urgent Review Officer'))
const urgentBusy = ref(false)
async function authorizeUrgent() {
  if (!detail.value?.sample?.name) return
  urgentBusy.value = true; err.value = ''
  try {
    await resultsApi.authorizeUrgent(detail.value.sample.name)
    await load()
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to authorize urgent review')
  } finally { urgentBusy.value = false }
}

function printReport() {
  const params = new URLSearchParams({
    doctype: 'Diagnostic Report', name: reportName.value,
    format: 'Diagnostic Report', no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Report · ${reportName}`" />

  <div class="mb-3 flex items-center gap-2 flex-wrap">
    <button class="btn-ghost !text-xs" @click="router.push('/lab/verification')">← Back to Verification Queue</button>
    <button v-if="detail?.workflow_session" class="btn-ghost !text-xs"
            @click="router.push(`/workflow/${detail.workflow_session}`)">
      ↩ Open Lab Workflow ({{ detail.workflow_session }})
    </button>
  </div>

  <div v-if="loading" class="card p-8 text-center text-surface-400">Loading report…</div>
  <div v-else-if="err && !detail" class="card p-6 text-status-danger">{{ err }}</div>
  <div v-else-if="detail" class="grid grid-cols-1 lg:grid-cols-3 gap-4">

    <!-- LEFT: report + samples + results -->
    <div class="lg:col-span-2 space-y-4">

      <!-- Header -->
      <div class="card p-5">
        <div class="flex items-start justify-between gap-3 flex-wrap mb-3">
          <div>
            <h2 class="text-lg font-semibold">{{ detail.report.name }}</h2>
            <p class="text-sm text-surface-500">{{ detail.report.patient_name || detail.report.patient }}</p>
          </div>
          <div class="flex items-center gap-2 flex-wrap">
            <span v-if="detail.report.is_urgent" class="pill bg-red-100 text-red-800 text-xs font-bold">URGENT</span>
            <span v-if="detail.report.is_critical" class="pill bg-red-100 text-red-800 text-xs font-bold">CRITICAL</span>
            <StatusPill :status="detail.report.status || 'Draft'" />
          </div>
        </div>
        <dl class="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2 text-sm">
          <div><dt class="text-xs text-surface-500">Sample</dt>
            <dd>
              <button v-if="detail.sample" class="text-brand-teal-600 hover:underline"
                @click="router.push(`/lab/samples/${detail.sample.name}`)">{{ detail.sample.name }}</button>
              <span v-else>—</span>
            </dd>
          </div>
          <div><dt class="text-xs text-surface-500">Sample Type</dt><dd>{{ detail.sample?.sample || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Collected</dt><dd>{{ detail.sample?.collected_time?.split('.')[0] || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Practitioner</dt><dd>{{ detail.report.practitioner || detail.sample?.referring_practitioner || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Peer Review</dt>
            <dd>
              <span v-if="detail.report.custom_peer_reviewed" class="text-emerald-700 font-medium">Passed ✓</span>
              <span v-else-if="pendingCase" class="text-amber-700">
                Awaiting — case
                <button class="underline" @click="router.push(`/lab/peer-review/${pendingCase.name}`)">{{ pendingCase.name }}</button>
              </span>
              <span v-else class="text-surface-400">Not required</span>
            </dd>
          </div>
          <div v-if="detail.report.is_urgent"><dt class="text-xs text-surface-500">Urgent Review</dt>
            <dd>
              <span v-if="urgentAuthorized" class="text-emerald-700 font-medium">Authorized ✓</span>
              <span v-else class="text-amber-700">{{ detail.report.urgent_review_status || 'Pending' }}</span>
            </dd>
          </div>
        </dl>
      </div>

      <!-- Results — one card per Lab Test -->
      <div v-if="!detail.lab_tests?.length" class="card p-6 text-sm text-surface-400">
        No results found for this report.
      </div>
      <div v-for="t in detail.lab_tests" :key="t.name" class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <div>
            <h3 class="font-semibold">{{ t.template || t.name }}</h3>
            <p class="text-xs text-surface-500">Lab Test: {{ t.name }}</p>
          </div>
          <StatusPill :status="t.docstatus === 1 ? 'Completed' : 'Draft'" />
        </div>
        <table v-if="t.normal_test_items?.length" class="w-full text-sm">
          <thead>
            <tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-1.5 pr-3">Analyte</th>
              <th class="pr-3">Result</th>
              <th class="pr-3">Unit</th>
              <th class="pr-3">Reference</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in t.normal_test_items" :key="r.name" class="border-b border-surface-100">
              <td class="py-1.5 pr-3 font-medium">{{ r.lab_test_name }}</td>
              <td class="pr-3 font-mono" :class="r.status && r.status !== 'Normal' ? 'text-status-danger font-semibold' : ''">{{ r.result_value || '—' }}</td>
              <td class="pr-3 text-surface-500">{{ r.lab_test_uom || '—' }}</td>
              <td class="pr-3 text-surface-500 whitespace-pre-line text-xs">{{ r.normal_range || '—' }}</td>
              <td><StatusPill :status="r.status || 'Normal'" /></td>
            </tr>
          </tbody>
        </table>
        <div v-for="r in (t.descriptive_test_items || [])" :key="r.name" class="mt-2 text-sm">
          <div class="text-xs text-surface-500">{{ r.lab_test_particulars }}</div>
          <div class="whitespace-pre-line">{{ r.result_value || '—' }}</div>
        </div>
      </div>
    </div>

    <!-- RIGHT: sign-off panel — sticky -->
    <div class="lg:sticky lg:top-4 self-start">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Verify &amp; Release</h3>

        <div v-if="isReleased" class="p-3 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-800 mb-3">
          Report released. Status <strong>Approved</strong>.
          <button class="btn-ghost w-full mt-2 !text-xs" @click="printReport">Print Report</button>
        </div>

        <template v-else>
          <label class="block text-xs text-surface-500 mb-1">Final Conclusion (optional)</label>
          <textarea v-model="conclusion" rows="3"
            class="input w-full px-3 py-2 rounded border border-surface-200 text-sm"
            placeholder="Add a final conclusion / sign-off note..."></textarea>

          <!-- Peer review inline — same button as workflow, so a verifier
               who is ALSO peer-reviewing can close the case without visiting
               a second page. Hidden for the original reporter. -->
          <button v-if="canApprovePeer" class="btn-primary w-full mt-3"
                  :disabled="peerApproveBusy" @click="approvePeer">
            {{ peerApproveBusy ? 'Approving…' : '✓ Approve Peer Review' }}
          </button>
          <div v-else-if="pendingCase && isOriginalReporter"
               class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
            You entered these results — someone else must peer-review this case first.
          </div>
          <!-- Urgent authorization inline — server enforces the URR role. -->
          <button v-if="isUrgent && !urgentAuthorized && canAuthorizeUrgent"
                  class="btn-primary w-full mt-3 !bg-red-600 hover:!bg-red-700"
                  :disabled="urgentBusy" @click="authorizeUrgent">
            {{ urgentBusy ? 'Authorizing…' : '⚡ Authorize Urgent Review' }}
          </button>
          <div v-else-if="isUrgent && !urgentAuthorized"
               class="mt-3 p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
            Urgent case — you don't have the <strong>Urgent Review Officer</strong> role.
          </div>

          <button class="btn-primary w-full mt-3" :disabled="busy || !verifyAllowed"
                  :title="!peerReviewPassed ? 'Peer review must be closed first'
                    : (isUrgent && !urgentAuthorized ? 'Urgent review must be authorized first'
                    : 'Release the report to the patient portal.')"
                  @click="verify">
            {{ busy ? 'Releasing…' : '✓ Verify & Release' }}
          </button>

          <p v-if="!verifyAllowed && !isReleased" class="text-xs text-amber-600 mt-2">
            <span v-if="!peerReviewPassed">Awaiting Peer Review — a reviewer must close the peer review case first.</span>
            <span v-else-if="isUrgent && !urgentAuthorized">Urgent case — awaits authorization by an Urgent Review Officer.</span>
          </p>

          <p v-if="err" class="text-xs text-status-danger mt-2">{{ err }}</p>
        </template>
      </div>
    </div>

  </div>
</template>
