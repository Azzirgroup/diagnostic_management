<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import StatusPill from '@/components/ui/StatusPill.vue'
// @ts-ignore — genetest SignaturePad uses a JS <script setup>
import SignaturePad from '@/components/common/SignaturePad.vue'
import { resultsApi, type SampleResults, type SampleRow } from '@/api/adms'
import { frappeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// Sample-centric results (matches genetest: ONE report per Lab Sample,
// aggregating every test on that sample). Master-detail: pick a sample,
// enter results for all its tests, complete & release as one report.
const props = defineProps<{
  session: { name?: string; order_detail?: { samples?: SampleRow[]; reports?: Array<{ name: string; status?: string; docname?: string; sample_collection?: string; is_urgent?: number; urgent_review_status?: string }> } | null }
}>()
const emit = defineEmits<{ (e: 'reload'): void; (e: 'finish'): void }>()

const samples = computed(() => props.session?.order_detail?.samples ?? [])
const reports = computed(() => props.session?.order_detail?.reports ?? [])
const selectedIdx = ref(0)
const detail = ref<SampleResults | null>(null)
const critical = ref(false)
const conclusion = ref('')
const signature = ref('')          // technologist
const pathologistSignature = ref('')
const diagnosis = ref('')
const clinicalNotes = ref('')
const pathologistRemarks = ref('')
const accreditation = ref('')
const pathologistName = ref('')
const loading = ref(false)
const saving = ref(false)
const error = ref('')

const selectedSample = computed(() => samples.value[selectedIdx.value])
const reportFor = (sample?: string) => reports.value.find((r) => r.sample_collection === sample || r.docname === sample)
const sampleDone = (sample?: string) => !!reportFor(sample)          // report exists ⇒ results completed
const released = (sample?: string) => reportFor(sample)?.status === 'Approved'
const allDone = computed(() => samples.value.length > 0 && samples.value.every((s) => sampleDone(s.name)))
const doneCount = computed(() => samples.value.filter((s) => sampleDone(s.name)).length)
const allTestsCompleted = computed(() => !!detail.value && detail.value.lab_tests.length > 0 && detail.value.lab_tests.every((t) => t.docstatus === 1))

// Urgent-review gate: an urgent sample's report must be authorized by an
// "Urgent Review Officer" before Verify & Release becomes available.
const isUrgent = computed(() => !!(detail.value?.is_urgent || selectedSample.value?.is_urgent))
const urgentAuthorized = computed(() => !!detail.value?.urgent_authorized)
const canAuthorizeUrgent = computed(() => !!detail.value?.can_authorize_urgent || auth.roles.includes('Urgent Review Officer'))
// Non-urgent → always allowed. Urgent → only once authorized.
const verifyAllowed = computed(() => !isUrgent.value || urgentAuthorized.value)
// Across the WHOLE workflow: is there any sample whose report is urgent and
// hasn't been authorized yet? Used to give the user a specific reason when
// Finish is locked on an urgent case.
const pendingUrgentAuth = computed(() =>
  reports.value.some((r) => !!r.is_urgent && r.urgent_review_status !== 'Authorized')
)
// Finish Workflow gate: every sample's report must be Verified & Released
// (status === 'Approved'). This implicitly subsumes the urgent gate (an
// urgent case can't be released without authorization) but the hint is more
// specific when urgent authorization is the actual blocker.
const allReleased = computed(() => samples.value.length > 0 && samples.value.every((s) => released(s.name)))

async function loadDetail() {
  if (!selectedSample.value) { detail.value = null; return }
  loading.value = true; error.value = ''
  try {
    detail.value = await resultsApi.getSample(selectedSample.value.name)
    critical.value = false
    conclusion.value = ''
  } catch (e: any) { error.value = e?.message || 'Failed to load sample' }
  finally { loading.value = false }
}
watch(selectedIdx, loadDetail)
watch(samples, () => { if (selectedIdx.value >= samples.value.length) selectedIdx.value = 0; loadDetail() }, { immediate: true })

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
// Split "Negative\nPositive\nTrace" into a clean string list.
function optionsList(raw?: string): string[] {
  return (raw || '').split(/\r?\n/).map((s) => s.trim()).filter(Boolean)
}
// Abnormal for non-numeric result types: anything that isn't the configured
// "normal" range (case-insensitive) gets flagged. Empty result = no flag yet.
function abnormalQualitative(value?: string, range?: string): boolean {
  if (!value || !range) return false
  return value.trim().toLowerCase() !== range.trim().toLowerCase()
}
function isAbnormal(r: { result_value?: string; normal_range?: string; result_type?: string }): boolean {
  const t = (r.result_type || 'Numeric').toLowerCase()
  if (t === 'numeric') return abnormal(r.result_value, r.normal_range)
  if (t === 'select' || t === 'data') return abnormalQualitative(r.result_value, r.normal_range)
  return false
}

async function save(complete: boolean) {
  if (!detail.value || !selectedSample.value) return
  saving.value = true; error.value = ''
  try {
    await resultsApi.saveSample({
      sample: selectedSample.value.name,
      tests: detail.value.lab_tests.map((t) => ({
        name: t.name,
        normal: t.normal_test_items.map((r) => ({ name: r.name, result_value: r.result_value ?? '', lab_test_comment: r.lab_test_comment ?? '' })),
        descriptive: t.descriptive_test_items.map((r) => ({ name: r.name, result_value: r.result_value ?? '' })),
      })),
      complete: complete ? 1 : 0,
      is_critical: critical.value ? 1 : 0,
      conclusion: conclusion.value || undefined,
    })
    emit('reload')
    await loadDetail()
  } catch (e: any) { error.value = frappeError(e, 'Failed to save results') }
  finally { saving.value = false }
}

async function verify() {
  const rep = reportFor(selectedSample.value?.name)
  if (!rep) return
  saving.value = true; error.value = ''
  try {
    await resultsApi.approve({
      report: rep.name,
      signature: signature.value || undefined,
      pathologist_signature: pathologistSignature.value || undefined,
      diagnosis: diagnosis.value || undefined,
      clinical_notes: clinicalNotes.value || undefined,
      pathologist_remarks: pathologistRemarks.value || undefined,
      accreditation_type: accreditation.value || undefined,
      pathologist_name: pathologistName.value || undefined,
    })
    emit('reload')
  } catch (e: any) { error.value = frappeError(e, 'Failed to release report') }
  finally { saving.value = false }
}

async function authorizeUrgent() {
  if (!selectedSample.value) return
  saving.value = true; error.value = ''
  try {
    await resultsApi.authorizeUrgent(selectedSample.value.name)
    emit('reload')
    await loadDetail()
  } catch (e: any) { error.value = frappeError(e, 'Failed to authorize urgent review') }
  finally { saving.value = false }
}

async function printReport() {
  if (!selectedSample.value) return
  saving.value = true; error.value = ''
  try {
    // Build (or fetch) the verbatim genetest Lab Report for this sample, then print it.
    const lr = await resultsApi.labReportForSample(selectedSample.value.name)
    if (!lr) { error.value = 'No lab report available for this sample yet.'; return }
    const params = new URLSearchParams({ doctype: 'Lab Report', name: lr, format: 'Lab Report', no_letterhead: '0' })
    window.open(`/printview?${params.toString()}`, '_blank')
  } catch (e: any) { error.value = frappeError(e, 'Failed to open lab report') }
  finally { saving.value = false }
}
</script>

<template>
  <div class="space-y-4">
    <!-- Summary + finish -->
    <div class="card p-4 flex items-center justify-between flex-wrap gap-3">
      <div>
        <h3 class="font-semibold">Results</h3>
        <p class="text-sm text-surface-500"><strong class="text-surface-800">{{ doneCount }}</strong> of {{ samples.length }} sample report(s) done</p>
      </div>
      <div v-if="allDone" class="flex items-center gap-3">
        <span v-if="pendingUrgentAuth" class="text-xs text-amber-600">Urgent case awaits authorization — Finish locked</span>
        <span v-else-if="!allReleased" class="text-xs text-amber-600">Verify &amp; Release every sample before finishing</span>
        <button class="btn-primary" :disabled="!allReleased"
          :title="!allReleased ? (pendingUrgentAuth ? 'An Urgent Review Officer must authorize the urgent case first' : 'Verify & Release each sample before finishing the workflow') : ''"
          @click="emit('finish')">Finish Workflow →</button>
      </div>
      <span v-else class="text-xs text-amber-600">Complete results for every sample to finish</span>
    </div>

    <div v-if="!samples.length" class="card p-8 text-center text-surface-400">No samples on this workflow.</div>

    <!-- Sample selector -->
    <div v-if="samples.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
      <button v-for="(s, i) in samples" :key="s.name" @click="selectedIdx = i"
        :class="['text-left p-3 rounded-lg border transition-colors',
          i === selectedIdx ? 'border-brand-navy-700 ring-1 ring-brand-navy-700 bg-brand-navy-700/5' : 'border-surface-200 hover:border-surface-300']">
        <div class="text-sm font-medium text-surface-800 truncate">{{ s.name }}</div>
        <div class="text-xs text-surface-500 truncate">{{ s.sample || 'Sample' }}</div>
        <div class="mt-1.5 flex items-center gap-1.5 flex-wrap">
          <StatusPill :status="released(s.name) ? 'Released' : sampleDone(s.name) ? 'Completed' : 'Pending'" />
          <span v-if="s.is_urgent" class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700">URGENT</span>
        </div>
      </button>
    </div>

    <!-- Selected sample's report (all its tests) -->
    <div v-if="selectedSample" class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold flex items-center gap-2">
          {{ selectedSample.name }} · {{ detail?.sample_type || selectedSample.sample }}
          <span v-if="isUrgent" class="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700">URGENT</span>
        </h3>
        <StatusPill :status="released(selectedSample.name) ? 'Released' : sampleDone(selectedSample.name) ? 'Completed' : 'Pending'" />
      </div>
      <p v-if="error" class="text-sm text-status-danger mb-3">{{ error }}</p>
      <div v-if="loading" class="text-sm text-surface-400 py-4">Loading…</div>

      <template v-else-if="detail">
        <div v-if="!detail.lab_tests.length" class="text-sm text-surface-400">No lab tests on this sample.</div>

        <!-- One block per test on the sample -->
        <div v-for="t in detail.lab_tests" :key="t.name" class="mb-5">
          <div class="flex items-center gap-2 mb-2">
            <h4 class="text-sm font-semibold text-surface-800">{{ t.template || t.name }}</h4>
            <StatusPill :status="t.docstatus === 1 ? 'Completed' : 'Draft'" />
          </div>

          <table v-if="t.normal_test_items.length" class="w-full text-sm mb-2">
            <thead><tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-1.5 pr-3">Analyte</th><th class="pr-3 w-36">Result</th><th class="pr-3">Unit</th><th class="pr-3">Reference</th><th>Comment</th>
            </tr></thead>
            <tbody>
              <tr v-for="r in t.normal_test_items" :key="r.name" class="border-b border-surface-100">
                <td class="py-1.5 pr-3 font-medium">{{ r.lab_test_name }}</td>
                <td class="pr-3">
                  <div class="flex items-center gap-1">
                    <!-- Dynamic input per result_type from the picked reference row.
                         Select falls back to a text input if no options were configured,
                         so the field stays usable instead of locking the user to "—". -->
                    <select v-if="(r.result_type || 'Numeric') === 'Select' && optionsList(r.result_options).length"
                      v-model="r.result_value" :disabled="t.docstatus === 1"
                      :class="['input !py-1.5', isAbnormal(r) ? '!border-status-danger text-status-danger font-semibold' : '']">
                      <option value="">—</option>
                      <option v-for="opt in optionsList(r.result_options)" :key="opt" :value="opt">{{ opt }}</option>
                    </select>
                    <input v-else-if="(r.result_type || 'Numeric') === 'Date'"
                      v-model="r.result_value" :disabled="t.docstatus === 1" type="date"
                      class="input !py-1.5" />
                    <input v-else-if="(r.result_type || 'Numeric') === 'Numeric'"
                      v-model="r.result_value" :disabled="t.docstatus === 1" type="number" step="any"
                      :class="['input !py-1.5', isAbnormal(r) ? '!border-status-danger text-status-danger font-semibold' : '']" />
                    <input v-else
                      v-model="r.result_value" :disabled="t.docstatus === 1"
                      :class="['input !py-1.5', isAbnormal(r) ? '!border-status-danger text-status-danger font-semibold' : '']" />
                    <span v-if="isAbnormal(r)" class="text-status-danger text-xs" title="Outside reference">⚠</span>
                  </div>
                </td>
                <td class="pr-3 text-surface-500">{{ r.lab_test_uom || '—' }}</td>
                <td class="pr-3 text-surface-500 whitespace-pre-line">{{ r.normal_range || '—' }}</td>
                <td><input v-model="r.lab_test_comment" :disabled="t.docstatus === 1" class="input !py-1.5" placeholder="—" /></td>
              </tr>
            </tbody>
          </table>

          <div v-for="r in t.descriptive_test_items" :key="r.name" class="mb-2">
            <label class="block text-xs text-surface-500 mb-1">{{ r.lab_test_particulars }}</label>
            <textarea v-model="r.result_value" :disabled="t.docstatus === 1" rows="2" class="input"></textarea>
          </div>

          <div v-if="!t.normal_test_items.length && !t.descriptive_test_items.length" class="text-sm text-surface-400">
            This test's template has no result components configured.
          </div>
        </div>

        <!-- Footer: enter or verify -->
        <template v-if="!allTestsCompleted && detail.lab_tests.length">
          <div class="flex items-center gap-4 mb-3 border-t border-surface-100 pt-3">
            <label class="flex items-center gap-2 text-sm">
              <input v-model="critical" type="checkbox" class="accent-status-danger" />
              <span :class="critical ? 'text-status-danger font-medium' : ''">Critical result</span>
            </label>
          </div>
          <textarea v-model="conclusion" rows="2" class="input mb-3" placeholder="Conclusion / interpretation (optional)"></textarea>
          <div class="flex justify-end gap-2">
            <button class="btn-ghost" :disabled="saving" @click="save(false)">{{ saving ? 'Saving…' : 'Save Draft' }}</button>
            <button class="btn-primary" :disabled="saving" @click="save(true)">{{ saving ? 'Saving…' : 'Save & Complete' }}</button>
          </div>
        </template>
        <template v-else-if="allTestsCompleted">
          <div class="border-t border-surface-100 pt-4">
            <div v-if="!released(selectedSample.name)">
              <!-- Urgent review gate -->
              <div v-if="isUrgent && !urgentAuthorized" class="mb-4 rounded-lg border border-red-200 bg-red-50 p-3">
                <div class="flex items-center gap-2 text-sm font-semibold text-red-700">
                  <span class="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700">URGENT</span>
                  Awaiting Urgent Review authorization
                </div>
                <p class="text-xs text-red-600 mt-1">
                  This urgent case must be authorized by an Urgent Review Officer before it can be verified &amp; released.
                </p>
                <div class="mt-2">
                  <button v-if="canAuthorizeUrgent" class="btn-primary !bg-red-600 hover:!bg-red-700"
                    :disabled="saving" @click="authorizeUrgent">
                    {{ saving ? 'Authorizing…' : 'Authorize Urgent Review' }}
                  </button>
                  <span v-else class="text-xs text-red-500">You do not have the Urgent Review Officer role.</span>
                </div>
              </div>
              <div v-else-if="isUrgent && urgentAuthorized" class="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 flex items-center justify-between gap-3">
                <span class="text-xs font-medium text-emerald-700">✓ Urgent review authorized — you may now verify &amp; release.</span>
                <button class="btn-primary" :disabled="saving" @click="verify">
                  {{ saving ? 'Releasing…' : 'Verify &amp; Release' }}
                </button>
              </div>
              <h4 class="font-semibold mb-3">Clinical Notes &amp; Sign-off</h4>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <div>
                  <label class="block text-xs text-surface-500 mb-1">Provisional Diagnosis</label>
                  <input v-model="diagnosis" class="input" placeholder="—" />
                </div>
                <div>
                  <label class="block text-xs text-surface-500 mb-1">Accreditation</label>
                  <input v-model="accreditation" class="input" placeholder="e.g. ISO 15189" />
                </div>
                <div class="sm:col-span-2">
                  <label class="block text-xs text-surface-500 mb-1">Clinical Notes</label>
                  <textarea v-model="clinicalNotes" rows="2" class="input"></textarea>
                </div>
                <div class="sm:col-span-2">
                  <label class="block text-xs text-surface-500 mb-1">Pathologist Remarks</label>
                  <textarea v-model="pathologistRemarks" rows="2" class="input"></textarea>
                </div>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-3">
                <div>
                  <SignaturePad v-model="signature" label="Lab Technologist signature" :height="110" />
                </div>
                <div>
                  <SignaturePad v-model="pathologistSignature" label="Consultant Pathologist signature" :height="110" />
                  <input v-model="pathologistName" class="input mt-2" placeholder="Pathologist name" />
                </div>
              </div>
              <div class="flex items-center justify-end">
                <button v-if="verifyAllowed" class="btn-primary" :disabled="saving" @click="verify">{{ saving ? 'Releasing…' : 'Verify & Release' }}</button>
                <span v-else class="text-xs text-surface-400">Verify &amp; Release unlocks once urgent review is authorized.</span>
              </div>
            </div>
            <div v-else class="flex items-center justify-between">
              <span class="pill-success">Released</span>
              <button class="btn-ghost" @click="printReport">Print Report</button>
            </div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>
