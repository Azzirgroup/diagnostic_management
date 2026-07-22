<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { labApi } from '@/api/adms'
import { frappeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

// Full-page peer-review detail — sibling to the queue's DetailPane. Renders
// the case metadata, the underlying Diagnostic Report + Lab Tests + all
// analyte rows, the sample(s), and the review actions on ONE page so the
// reviewer never has to leave for context.
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const caseName = computed(() => String(route.params.name || ''))
const detail = ref<Awaited<ReturnType<typeof labApi.peerReviewDetail>> | null>(null)
const loading = ref(true)
const err = ref('')
const reviewNotes = ref('')
const busy = ref(false)

const isOriginalReporter = computed(() =>
  !!detail.value?.case?.original_reporter &&
  detail.value.case.original_reporter === auth.user?.name,
)
const canAmend = computed(() => !isOriginalReporter.value)
const isClosed = computed(() => detail.value?.case?.status === 'Closed')

async function load() {
  loading.value = true; err.value = ''
  try {
    detail.value = await labApi.peerReviewDetail(caseName.value)
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to load peer review case')
  } finally { loading.value = false }
}
onMounted(load)

async function submit(outcome: string) {
  busy.value = true; err.value = ''
  try {
    await labApi.submitPeerReview({
      name: caseName.value, outcome, review_notes: reviewNotes.value,
    })
    router.push('/lab/peer-review')
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to submit peer review')
  } finally { busy.value = false }
}

async function submitCorrection() {
  busy.value = true; err.value = ''
  try {
    const r = await labApi.submitPeerReviewCorrection({
      name: caseName.value, review_notes: reviewNotes.value,
      discrepancy_severity: 'Major',
    })
    alert(`Report ${r.report} sent back for correction. The tech can now edit result values in place; each edit is audit-logged.`)
    router.push('/lab/peer-review')
  } catch (e: any) {
    err.value = frappeError(e, 'Failed to send back for correction')
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar :title="`Peer Review · ${caseName}`" />

  <div class="mb-3 flex items-center gap-2 flex-wrap">
    <button class="btn-ghost !text-xs" @click="router.push('/lab/peer-review')">← Back to Queue</button>
    <button v-if="detail?.workflow_session" class="btn-ghost !text-xs"
            @click="router.push(`/workflow/${detail.workflow_session}`)">
      ↩ Open Lab Workflow ({{ detail.workflow_session }})
    </button>
  </div>

  <div v-if="loading" class="card p-8 text-center text-surface-400">Loading case…</div>
  <div v-else-if="err && !detail" class="card p-6 text-status-danger">{{ err }}</div>
  <div v-else-if="detail" class="grid grid-cols-1 lg:grid-cols-3 gap-4">

    <!-- LEFT: case + results (2/3) -->
    <div class="lg:col-span-2 space-y-4">

      <!-- Case metadata -->
      <div class="card p-5">
        <div class="flex items-start justify-between gap-3 flex-wrap mb-3">
          <div>
            <h2 class="text-lg font-semibold">{{ detail.case.name }}</h2>
            <p class="text-sm text-surface-500">{{ detail.case.patient_name || detail.case.patient }}</p>
          </div>
          <StatusPill :status="detail.case.status" />
        </div>
        <dl class="grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-2 text-sm">
          <div><dt class="text-xs text-surface-500">Section</dt><dd>{{ detail.case.section || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Priority</dt><dd>{{ detail.case.priority || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Reporter</dt><dd>{{ detail.case.original_reporter || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Diagnostic Report</dt>
            <dd>
              <button v-if="detail.diagnostic_report" class="text-brand-teal-600 hover:underline"
                @click="router.push(`/reports/${detail.diagnostic_report.name}`)">{{ detail.diagnostic_report.name }}</button>
              <span v-else>—</span>
            </dd>
          </div>
          <div><dt class="text-xs text-surface-500">Sample</dt><dd>{{ detail.sample || '—' }}</dd></div>
          <div><dt class="text-xs text-surface-500">Outcome</dt><dd>{{ detail.case.outcome || '—' }}</dd></div>
        </dl>
      </div>

      <!-- Results — one card per Lab Test -->
      <div v-if="!detail.lab_tests?.length" class="card p-6 text-sm text-surface-400">
        No results found for this case.
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

      <!-- Reporter's conclusion -->
      <div v-if="detail.diagnostic_report?.conclusion" class="card p-4">
        <h4 class="text-sm font-semibold text-surface-800 mb-1">Reporter's conclusion</h4>
        <p class="text-sm whitespace-pre-line">{{ detail.diagnostic_report.conclusion }}</p>
      </div>
    </div>

    <!-- RIGHT: review action panel (1/3) — sticky so it stays visible -->
    <div class="lg:sticky lg:top-4 self-start">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Your Review</h3>

        <div v-if="isClosed" class="p-3 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-800 mb-3">
          Case already closed with outcome <strong>{{ detail.case.outcome }}</strong>. No further action needed.
          <div v-if="detail.case.review_notes" class="mt-2 text-xs text-emerald-700 whitespace-pre-line">
            <span class="font-medium">Notes:</span> {{ detail.case.review_notes }}
          </div>
        </div>

        <template v-else>
          <label class="block text-xs text-surface-500 mb-1">Review Notes (Required)</label>
          <textarea v-model="reviewNotes" rows="4"
            class="input w-full px-3 py-2 rounded border border-surface-200 text-sm"
            placeholder="Enter your comparison, comments, or additional findings..."></textarea>

          <div v-if="isOriginalReporter" class="mt-3 p-3 bg-amber-50 border border-amber-200 rounded text-xs text-amber-800">
            You entered these results — someone else must peer-review this case. Ask a colleague to log in and close it.
          </div>
          <template v-else>
            <p v-if="!reviewNotes.trim()" class="text-xs text-amber-600 mt-2">
              Enter Review Notes to enable the submit buttons.
            </p>
            <button class="btn-primary w-full mt-3" :disabled="busy || !reviewNotes.trim()"
              @click="submit('Agree')">{{ busy ? 'Submitting…' : '✓ Submit · Agree' }}</button>
            <button class="btn-secondary w-full mt-2" :disabled="busy || !reviewNotes.trim()"
              @click="submit('Minor Disagreement')">Submit · Minor Disagree</button>
            <button class="btn-danger-ghost w-full mt-2" :disabled="busy || !reviewNotes.trim()"
              @click="submit('Major Disagreement')">Submit · Major Disagree</button>
            <button v-if="canAmend" class="btn-danger w-full mt-2" :disabled="busy || !reviewNotes.trim()"
              :title="'Sends the report back to the tech for in-place correction. Lab Tests stay submitted; each edit is audit-logged.'"
              @click="submitCorrection">Send Back for Correction</button>
          </template>

          <p v-if="err" class="text-xs text-status-danger mt-2">{{ err }}</p>
        </template>
      </div>
    </div>

  </div>
</template>
