<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { criticalApi, type CriticalResultPayload } from '@/api/adms'
import { frappeError } from '@/api/client'

// Detail page for a critical Diagnostic Report. Two main jobs:
// (1) Show the FULL result — every lab test on the linked sample, with each
//     analyte's value vs reference range and an abnormal flag. The
//     `result_payload` endpoint returns either a sample-shaped or lab-test-
//     shaped body (whichever the report points at).
// (2) Let a clinician submit a peer review (outcome + notes + discrepancy
//     severity), which creates a Peer Review Case on the fly and closes it +
//     acknowledges the critical finding in one round-trip.

interface LogEntry {
  name: string
  severity?: string
  status?: string
  detected_at?: string
  notified_at?: string
  acknowledged_at?: string
  acknowledged_by?: string
  ack_notes?: string
  notification_channel?: string
  escalation_level?: number
  test_or_modality?: string
  summary?: string
}

const route = useRoute()
const router = useRouter()
const report = ref<Record<string, any> & { log?: LogEntry[] } | null>(null)
const payload = ref<CriticalResultPayload | null>(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')

// Peer review form
const outcome = ref<'Agree' | 'Minor Disagreement' | 'Major Disagreement' | 'Amendment Required'>('Agree')
const discrepancy = ref<'' | 'None' | 'Minor' | 'Major' | 'Critical'>('')
const reviewNotes = ref('')
const concurrence = ref<number | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [meta, body] = await Promise.all([
      criticalApi.detail(route.params.name as string),
      criticalApi.resultPayload(route.params.name as string).catch(() => null),
    ])
    report.value = meta as any
    payload.value = body
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to load critical finding')
  } finally {
    loading.value = false
  }
}
onMounted(load)

const isAcked = computed(() => !!report.value?.critical_acknowledged)

// Inline reference-range parser → abnormal flag (same logic as ResultsStep).
function bounds(r?: string): { low?: number; high?: number } {
  if (!r) return {}
  const nums = (r.match(/-?\d+(\.\d+)?/g) || []).map(Number)
  if (/[<≤]/.test(r) && nums.length) return { high: nums[0] }
  if (/[>≥]/.test(r) && nums.length) return { low: nums[0] }
  if (nums.length >= 2) return { low: nums[0], high: nums[1] }
  return {}
}
function abnormal(value?: string, range?: string): boolean {
  const v = parseFloat(value || '')
  if (isNaN(v)) return false
  const { low, high } = bounds(range)
  return (low != null && v < low) || (high != null && v > high)
}
function flagFor(value?: string, range?: string): string {
  const v = parseFloat(value || '')
  if (isNaN(v)) return ''
  const { low, high } = bounds(range)
  if (high != null && v > high) return 'HIGH'
  if (low != null && v < low) return 'LOW'
  if (low != null || high != null) return 'NORMAL'
  return ''
}

const labTests = computed(() => {
  if (!payload.value) return []
  if (payload.value.shape === 'sample') return payload.value.sample?.lab_tests || []
  if (payload.value.shape === 'lab_test' && payload.value.lab_test) return [payload.value.lab_test as any]
  return []
})

async function submitReview() {
  if (!report.value) return
  busy.value = true
  error.value = ''
  try {
    await criticalApi.submitPeerReview({
      report: report.value.name,
      outcome: outcome.value,
      review_notes: reviewNotes.value,
      discrepancy_severity: discrepancy.value || undefined,
      concurrence: concurrence.value == null ? undefined : Number(concurrence.value),
    })
    reviewNotes.value = ''
    await load()
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to submit peer review')
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar :title="`Critical Finding · ${report?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>
  <div v-else-if="!report" class="card p-12 text-center text-surface-400">
    Critical finding not found.
    <button class="btn-ghost block mx-auto mt-3" @click="router.push('/critical-findings')">Back to list</button>
  </div>

  <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <!-- Patient header -->
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h3 class="font-semibold text-lg">{{ report.patient_name || report.name }}</h3>
            <div class="text-xs text-surface-500 mt-1">Report {{ report.docname || report.name }} · MRN {{ report.patient || '—' }}</div>
          </div>
          <div class="flex items-center gap-2">
            <span class="pill-danger">CRITICAL</span>
            <StatusPill :status="report.status" />
            <span v-if="isAcked" class="pill-success">Reviewed</span>
          </div>
        </div>
      </div>

      <!-- FULL RESULT — every lab test on the linked sample, all result rows -->
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold">Full Result</h3>
          <span v-if="payload?.shape === 'sample'" class="text-xs text-surface-500">Sample {{ payload.sample?.sample }} · {{ payload.sample?.sample_type || 'Unknown' }}</span>
        </div>
        <div v-if="!labTests.length" class="text-sm text-surface-400 py-4">No result rows available for this report.</div>
        <div v-for="t in labTests" :key="t.name" class="mb-5 last:mb-0">
          <div class="flex items-center gap-2 mb-2">
            <h4 class="text-sm font-semibold text-surface-800">{{ t.template }}</h4>
            <StatusPill :status="t.status || (t.docstatus === 1 ? 'Completed' : 'Draft')" />
            <span class="text-xs text-surface-400">{{ t.name }}</span>
          </div>
          <table v-if="t.normal_test_items && t.normal_test_items.length" class="w-full text-sm mb-2">
            <thead><tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-2">Analyte</th><th>Result</th><th>Unit</th><th>Reference</th><th>Flag</th>
            </tr></thead>
            <tbody>
              <tr v-for="r in t.normal_test_items" :key="r.name"
                  :class="['border-b border-surface-100', abnormal(r.result_value, r.normal_range) && 'bg-red-50/40']">
                <td class="py-2">{{ r.lab_test_name }}</td>
                <td class="font-medium">
                  {{ r.result_value || '—' }}
                  <span v-if="abnormal(r.result_value, r.normal_range)" class="text-status-danger text-xs ml-1" title="Out of range">⚠</span>
                </td>
                <td>{{ r.lab_test_uom || '—' }}</td>
                <td class="text-surface-500">{{ r.normal_range || '—' }}</td>
                <td>
                  <span v-if="flagFor(r.result_value, r.normal_range)"
                    :class="['text-xs font-semibold px-1.5 py-0.5 rounded',
                      flagFor(r.result_value, r.normal_range) === 'HIGH' ? 'bg-red-100 text-red-700'
                      : flagFor(r.result_value, r.normal_range) === 'LOW' ? 'bg-blue-100 text-blue-700'
                      : 'bg-emerald-100 text-emerald-700']">
                    {{ flagFor(r.result_value, r.normal_range) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="t.descriptive_test_items && t.descriptive_test_items.length" class="space-y-2">
            <div v-for="r in t.descriptive_test_items" :key="r.name" class="text-sm border-b border-surface-100 py-2">
              <div class="text-xs text-surface-500">{{ r.lab_test_particulars }}</div>
              <div>{{ r.result_value || '—' }}</div>
            </div>
          </div>
          <div v-if="(!t.normal_test_items || !t.normal_test_items.length) && (!t.descriptive_test_items || !t.descriptive_test_items.length)"
               class="text-xs text-surface-400 italic">No result rows entered</div>
        </div>
      </div>

      <!-- Reporter sign-off, if any -->
      <div v-if="payload?.report?.diagnosis || payload?.report?.clinical_notes || payload?.report?.pathologist_remarks" class="card p-5">
        <h3 class="font-semibold mb-3">Reporter Sign-off</h3>
        <dl class="text-sm space-y-2">
          <div v-if="payload.report.diagnosis"><dt class="text-xs text-surface-500">Provisional Diagnosis</dt><dd>{{ payload.report.diagnosis }}</dd></div>
          <div v-if="payload.report.clinical_notes"><dt class="text-xs text-surface-500">Clinical Notes</dt><dd class="whitespace-pre-wrap">{{ payload.report.clinical_notes }}</dd></div>
          <div v-if="payload.report.pathologist_remarks"><dt class="text-xs text-surface-500">Pathologist Remarks</dt><dd class="whitespace-pre-wrap">{{ payload.report.pathologist_remarks }}</dd></div>
          <div v-if="payload.report.pathologist_name"><dt class="text-xs text-surface-500">Reported By</dt><dd>{{ payload.report.pathologist_name }}</dd></div>
        </dl>
      </div>

      <!-- Escalation Timeline -->
      <div class="card p-5">
        <h3 class="font-semibold mb-4">Escalation Timeline</h3>
        <div v-if="!report.log || !report.log.length" class="text-sm text-surface-400 py-4">
          No log entries yet.
        </div>
        <ol v-else class="space-y-3">
          <li v-for="(l, i) in report.log" :key="l.name" class="flex gap-3 text-sm">
            <div class="flex flex-col items-center">
              <div :class="[
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold',
                l.status === 'Acknowledged' ? 'bg-status-success-bg text-status-success'
                  : l.status === 'Escalated' ? 'bg-status-danger-bg text-status-danger'
                  : 'bg-status-warning-bg text-status-warning']">
                {{ i + 1 }}
              </div>
              <div v-if="i < report.log.length - 1" class="w-px h-full bg-surface-200 mt-1"></div>
            </div>
            <div class="flex-1 pb-3">
              <div class="flex items-center gap-2">
                <strong>{{ l.status }}</strong>
                <span v-if="l.severity" class="pill-warning text-xs">{{ l.severity }}</span>
                <span v-if="l.escalation_level" class="pill-danger text-xs">Level {{ l.escalation_level }}</span>
              </div>
              <div class="text-xs text-surface-500 mt-0.5">
                {{ l.detected_at || l.notified_at || l.acknowledged_at }}
                <span v-if="l.acknowledged_by"> · by {{ l.acknowledged_by }}</span>
                <span v-if="l.notification_channel"> · via {{ l.notification_channel }}</span>
              </div>
              <p v-if="l.summary" class="text-sm mt-1 text-surface-700">{{ l.summary }}</p>
              <p v-if="l.ack_notes" class="text-sm mt-1 text-status-success">"{{ l.ack_notes }}"</p>
            </div>
          </li>
        </ol>
      </div>
    </div>

    <!-- Right column: summary + peer review form -->
    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Practitioner</dt><dd>{{ report.practitioner || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Created</dt><dd>{{ report.creation?.split('.')[0] }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Reviewed</dt><dd>{{ isAcked ? 'Yes' : 'No' }}</dd></div>
          <div v-if="report.critical_acknowledged_at" class="flex justify-between"><dt class="text-surface-500">Reviewed At</dt><dd>{{ report.critical_acknowledged_at }}</dd></div>
        </dl>
      </div>

      <div v-if="!isAcked" class="card p-5">
        <h3 class="font-semibold mb-3">Submit Peer Review</h3>
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
        <label class="block text-xs text-surface-500 mb-1">Concurrence (%)</label>
        <input v-model.number="concurrence" type="number" min="0" max="100" class="input mb-3" placeholder="e.g. 90" />
        <label class="block text-xs text-surface-500 mb-1">Reviewer Notes</label>
        <textarea v-model="reviewNotes" rows="3" placeholder="Agreement / disagreement, follow-up actions…" class="input w-full mb-3"></textarea>
        <p v-if="error" class="text-sm text-status-danger mb-2">{{ error }}</p>
        <button class="btn-primary w-full" :disabled="busy" @click="submitReview">
          {{ busy ? 'Submitting…' : 'Submit Peer Review' }}
        </button>
      </div>
      <div v-else class="card p-5 text-sm text-surface-500">
        Peer review submitted{{ report.critical_acknowledged_at ? ' on ' + report.critical_acknowledged_at : '' }}.
      </div>
    </div>
  </div>
</template>
