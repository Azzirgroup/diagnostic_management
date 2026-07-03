<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import StatusPill from '@/components/ui/StatusPill.vue'
// @ts-ignore — genetest SignaturePad uses a JS <script setup>
import SignaturePad from '@/components/common/SignaturePad.vue'
import { resultsApi, labReportsApi, type SampleResults, type SampleRow } from '@/api/adms'
import { frappeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// Same ladder as Lab Report Numeric Result.status — kept in sync so badges
// on the print format match what the technologist picked here.
const STATUS_OPTIONS = [
  'Normal','High','Low','Abnormal','Critical','Optimal','Intermediate',
  'Deficiency','Insufficiency','Sufficiency','Potential Toxicity',
  'Pre-diabetic','Diabetic',
] as const

// Sample-centric results (matches genetest: ONE report per Lab Sample,
// aggregating every test on that sample). Master-detail: pick a sample,
// enter results for all its tests, complete & release as one report.
const props = defineProps<{
  session: { name?: string; order_detail?: { samples?: SampleRow[]; reports?: Array<{ name: string; status?: string; docname?: string; sample_collection?: string; is_urgent?: number; urgent_review_status?: string }> } | null }
}>()
const emit = defineEmits<{ (e: 'reload'): void; (e: 'finish'): void }>()

// `samples` = every sample on the workflow (used by Finish-gating computeds
// below — those must still see the pending samples, otherwise Finish would
// fire as soon as the partial subset is done).
const samples = computed(() => props.session?.order_detail?.samples ?? [])
// `readySamples` = only samples that have actually reached a terminal
// Collection state. THESE are what render as tabs the tech can click into
// to enter results. A "To Be Collected" sample no longer shows up here —
// the tech is directed back to Collection (via the amber banner) instead
// of being able to enter results for an un-collected sample.
const _COLLECTION_TERMINAL = ['Tested', 'Stored', 'Disposed']
const readySamples = computed(() =>
  samples.value.filter((s: any) => _COLLECTION_TERMINAL.includes(s.workflow_status)),
)
const reports = computed(() => props.session?.order_detail?.reports ?? [])
const selectedIdx = ref(0)
const detail = ref<SampleResults | null>(null)
const critical = ref(false)
const conclusion = ref('')
const signature = ref('')          // technologist
const pathologistSignature = ref('')
const diagnosis = ref('')
const clinicalNotes = ref('')
const pathologistName = ref('')
// "Reserve image space on print" — when ticked the Lab Report HTML reserves
// a 6cm blank box above the signatures so a stamp/manual signature/scanned
// image fits there. Optional image upload fills that box. Both carried
// through approve_report into the Lab Report doc.
const hasImageSpace = ref(false)
const imageSpaceImage = ref<string>('')          // data URL the user picked
const imageSpaceFileInput = ref<HTMLInputElement | null>(null)
// Sister flag: when ticked, the printed Lab Report HTML hides all trend
// charts. Carried via approve_report into the Lab Report doc.
const hideGraphs = ref(false)
async function onPreReleaseImagePicked(ev: Event) {
  const t = ev.target as HTMLInputElement
  const file = t.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { error.value = 'Pick an image file'; t.value = ''; return }
  if (file.size > 4 * 1024 * 1024) { error.value = 'Image must be < 4 MB'; t.value = ''; return }
  imageSpaceImage.value = await new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.onerror = () => reject(new Error('read failed'))
    r.readAsDataURL(file)
  })
  hasImageSpace.value = true   // picking an image implies reserving space
  t.value = ''
}
function clearPreReleaseImage() { imageSpaceImage.value = '' }
const loading = ref(false)
const saving = ref(false)
const error = ref('')

// selectedSample comes from readySamples — the un-collected sample is no
// longer a clickable tab, so it can never become the active selection.
const selectedSample = computed(() => readySamples.value[selectedIdx.value])
const reportFor = (sample?: string) => reports.value.find((r) => r.sample_collection === sample || r.docname === sample)
const sampleDone = (sample?: string) => !!reportFor(sample)          // report exists ⇒ results completed
const released = (sample?: string) => reportFor(sample)?.status === 'Approved'
// Mandatory peer review is now a GATE BEFORE Verify & Release (mirrors
// the urgent-review flow). On Save & Complete a Peer Review Case is auto-
// created. Until a reviewer closes it with Agree / Minor Disagreement
// (which flips `custom_peer_reviewed` to 1 on the Diagnostic Report),
// the tech's Verify & Release button stays disabled.
const peerReviewed = (sample?: string) => !!(reportFor(sample) as any)?.custom_peer_reviewed
const awaitingPeerReview = (sample?: string) =>
  !!reportFor(sample) && !peerReviewed(sample) && reportFor(sample)?.status !== 'Approved'
const pendingPeerReviewCount = computed(() =>
  samples.value.filter((s: any) => awaitingPeerReview(s.name)).length,
)
// Finish-Workflow gates check ALL samples (not just ready ones) so the
// workflow can't be finished while a sample is still un-collected.
const allDone = computed(() => samples.value.length > 0 && samples.value.every((s) => sampleDone(s.name)))
const doneCount = computed(() => samples.value.filter((s) => sampleDone(s.name)).length)
// Surfaced in the amber banner at the top of the page.
const pendingCollectionSamples = computed(() =>
  samples.value.filter((s: any) => !_COLLECTION_TERMINAL.includes(s.workflow_status)),
)
const allTestsCompleted = computed(() => !!detail.value && detail.value.lab_tests.length > 0 && detail.value.lab_tests.every((t) => t.docstatus === 1))

// Urgent-review gate: an urgent sample's report must be authorized by an
// "Urgent Review Officer" before Verify & Release becomes available.
const isUrgent = computed(() => !!(detail.value?.is_urgent || selectedSample.value?.is_urgent))
const urgentAuthorized = computed(() => !!detail.value?.urgent_authorized)
const canAuthorizeUrgent = computed(() => !!detail.value?.can_authorize_urgent || auth.roles.includes('Urgent Review Officer'))
// Verify & Release is gated by two independent checks:
//   - Peer review must have passed (custom_peer_reviewed=1 on DR)
//   - If the case is urgent, urgent review must also be authorized
// Both must hold before the tech can release.
const peerReviewPassedForSelected = computed(() =>
  !!selectedSample.value && peerReviewed(selectedSample.value.name),
)
const verifyAllowed = computed(() =>
  peerReviewPassedForSelected.value && (!isUrgent.value || urgentAuthorized.value),
)
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
    // Pass the workflow session id so the backend scopes Lab Tests to this
    // session's orders' Sales Invoice — instead of pulling every historical
    // Lab Test that ever touched this reused Sample Collection.
    detail.value = await resultsApi.getSample(selectedSample.value.name, props.session?.name || undefined)
    critical.value = false
    conclusion.value = ''
  } catch (e: any) { error.value = e?.message || 'Failed to load sample' }
  finally { loading.value = false }
}
watch(selectedIdx, loadDetail)
// Re-clamp the selected index against readySamples (the actual tab set) so
// when the user goes back and finishes another sample, the new tab appears
// and selection stays valid.
watch(readySamples, () => {
  if (selectedIdx.value >= readySamples.value.length) selectedIdx.value = 0
  loadDetail()
}, { immediate: true })

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
        normal: t.normal_test_items.map((r) => ({ name: r.name, result_value: r.result_value ?? '', status: r.status ?? 'Normal' })),
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
      pathologist_name: pathologistName.value || undefined,
      has_image_space: hasImageSpace.value ? 1 : 0,
      image_space_image: imageSpaceImage.value || undefined,
      hide_graphs: hideGraphs.value ? 1 : 0,
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

// Persistent "Reserve image space" toggle for the released-state UI. Each
// sample has its own Lab Report; we cache its name + current flag value per
// sample so the released branch can render + edit the checkbox without an
// extra round-trip on every click.
const releasedLabReport = ref<Record<string, { name: string; hasImageSpace: boolean; imageUrl: string | null; hideGraphs: boolean }>>({})
const togglingImageSpace = ref(false)
const releasedFileInput = ref<HTMLInputElement | null>(null)
async function loadLabReportForSelected() {
  if (!selectedSample.value) return
  const key = selectedSample.value.name
  if (releasedLabReport.value[key]) return
  try {
    const lrName = await resultsApi.labReportForSample(key)
    if (!lrName) return
    const lr = await labReportsApi.detail(lrName)
    releasedLabReport.value[key] = {
      name: lrName,
      hasImageSpace: !!lr.custom_has_image_space,
      imageUrl: lr.custom_image_space_image || null,
      hideGraphs: !!lr.custom_hide_graphs,
    }
  } catch { /* silent — checkbox just shows unchecked */ }
}
watch(selectedIdx, loadLabReportForSelected)
watch(samples, loadLabReportForSelected, { immediate: true })

async function toggleReleasedImageSpace(checked: boolean) {
  if (!selectedSample.value) return
  const entry = releasedLabReport.value[selectedSample.value.name]
  if (!entry) return
  togglingImageSpace.value = true
  try {
    const r = await labReportsApi.setImageSpace(entry.name, checked ? 1 : 0)
    entry.hasImageSpace = !!r.custom_has_image_space
    entry.imageUrl = r.custom_image_space_image
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to update image-space preference')
  } finally {
    togglingImageSpace.value = false
  }
}

async function onReleasedImagePicked(ev: Event) {
  if (!selectedSample.value) return
  const entry = releasedLabReport.value[selectedSample.value.name]
  if (!entry) return
  const t = ev.target as HTMLInputElement
  const file = t.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) { error.value = 'Pick an image file'; t.value = ''; return }
  if (file.size > 4 * 1024 * 1024) { error.value = 'Image must be < 4 MB'; t.value = ''; return }
  const dataUrl: string = await new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.onerror = () => reject(new Error('read failed'))
    r.readAsDataURL(file)
  })
  togglingImageSpace.value = true
  try {
    const r = await labReportsApi.setImageSpace(entry.name, 1, dataUrl)
    entry.hasImageSpace = !!r.custom_has_image_space
    entry.imageUrl = r.custom_image_space_image
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to upload image')
  } finally {
    togglingImageSpace.value = false
    t.value = ''
  }
}

async function removeReleasedImage() {
  if (!selectedSample.value) return
  const entry = releasedLabReport.value[selectedSample.value.name]
  if (!entry) return
  togglingImageSpace.value = true
  try {
    const r = await labReportsApi.setImageSpace(entry.name, entry.hasImageSpace ? 1 : 0, null, 1)
    entry.imageUrl = r.custom_image_space_image
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to remove image')
  } finally { togglingImageSpace.value = false }
}

async function toggleReleasedHideGraphs(checked: boolean) {
  if (!selectedSample.value) return
  const entry = releasedLabReport.value[selectedSample.value.name]
  if (!entry) return
  togglingImageSpace.value = true
  try {
    const r = await labReportsApi.setImageSpace(
      entry.name, entry.hasImageSpace ? 1 : 0, undefined, 0, checked ? 1 : 0)
    entry.hideGraphs = !!r.custom_hide_graphs
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to update hide-graphs preference')
  } finally { togglingImageSpace.value = false }
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
    <!-- Pending-collection callout — shown when the tech is in Results but
         some samples are still in earlier states (To Be Collected /
         Collected / Processing). Finish Workflow stays blocked until
         every sample is processed AND has a report. -->
    <div v-if="pendingCollectionSamples.length"
         class="card p-3 bg-amber-50 border-amber-200 text-sm flex items-start gap-2">
      <FeatherIcon name="alert-triangle" class="w-4 h-4 text-amber-600 mt-0.5 shrink-0" />
      <div>
        <div class="font-medium text-amber-900">
          {{ pendingCollectionSamples.length }} of {{ samples.length }} sample(s) still pending in Collection
        </div>
        <div class="text-amber-800 text-xs mt-0.5">
          You can enter results for the ready sample(s) now, but the Lab Report
          can't be finished until every sample is marked Complete or Stored.
          Go back to the <strong>Collection</strong> step to finish:
          <span class="font-mono">{{ pendingCollectionSamples.map((s: any) => s.name).join(', ') }}</span>
        </div>
      </div>
    </div>

    <!-- Summary + finish -->
    <div class="card p-4 flex items-center justify-between flex-wrap gap-3">
      <div>
        <h3 class="font-semibold">Results</h3>
        <p class="text-sm text-surface-500"><strong class="text-surface-800">{{ doneCount }}</strong> of {{ samples.length }} sample report(s) done</p>
      </div>
      <div v-if="allDone" class="flex items-center gap-3">
        <span v-if="pendingUrgentAuth" class="text-xs text-amber-600">Urgent case awaits authorization — Finish locked</span>
        <span v-else-if="pendingPeerReviewCount > 0" class="text-xs text-amber-600">
          {{ pendingPeerReviewCount }} sample{{ pendingPeerReviewCount === 1 ? '' : 's' }}
          awaiting Peer Review — a reviewer must close each case before Finish
        </span>
        <span v-else-if="!allReleased" class="text-xs text-amber-600">Verify &amp; Release every sample before finishing</span>
        <button class="btn-primary" :disabled="!allReleased"
          :title="!allReleased ? (pendingUrgentAuth ? 'An Urgent Review Officer must authorize the urgent case first' : 'Verify & Release each sample before finishing the workflow') : ''"
          @click="emit('finish')">Finish Workflow →</button>
      </div>
      <span v-else class="text-xs text-amber-600">Complete results for every sample to finish</span>
    </div>

    <div v-if="!samples.length" class="card p-8 text-center text-surface-400">No samples on this workflow.</div>
    <div v-else-if="!readySamples.length" class="card p-8 text-center text-surface-400">
      No samples are ready for results yet. Mark at least one sample Complete or Stored
      in the <strong>Collection</strong> step before entering results.
    </div>

    <!-- Sample selector — only ready samples (Tested/Stored/Disposed) -->
    <div v-if="readySamples.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
      <button v-for="(s, i) in readySamples" :key="s.name" @click="selectedIdx = i"
        :class="['text-left p-3 rounded-lg border transition-colors',
          i === selectedIdx ? 'border-brand-navy-700 ring-1 ring-brand-navy-700 bg-brand-navy-700/5' : 'border-surface-200 hover:border-surface-300']">
        <div class="text-sm font-medium text-surface-800 truncate">{{ s.name }}</div>
        <div class="text-xs text-surface-500 truncate">{{ s.sample || 'Sample' }}</div>
        <div class="mt-1.5 flex items-center gap-1.5 flex-wrap">
          <StatusPill :status="released(s.name) ? 'Released'
                              : awaitingPeerReview(s.name) ? 'Awaiting Peer Review'
                              : sampleDone(s.name) ? 'Completed'
                              : 'Pending'" />
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
        <StatusPill :status="released(selectedSample.name) ? 'Released'
                            : awaitingPeerReview(selectedSample.name) ? 'Awaiting Peer Review'
                            : sampleDone(selectedSample.name) ? 'Completed'
                            : 'Pending'" />
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
              <th class="py-1.5 pr-3">Analyte</th><th class="pr-3 w-36">Result</th><th class="pr-3">Unit</th><th class="pr-3">Reference</th><th class="w-44">Status</th>
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
                <td>
                  <select v-model="r.status" :disabled="t.docstatus === 1" class="input !py-1.5">
                    <option v-for="opt in STATUS_OPTIONS" :key="opt" :value="opt">{{ opt }}</option>
                  </select>
                </td>
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
                <span class="text-xs font-medium text-emerald-700">
                  ✓ Urgent review authorized{{ peerReviewPassedForSelected ? ' — you may now verify & release.' : ' — still awaiting Peer Review.' }}
                </span>
                <!-- Only show the quick-verify button when peer review has also
                     passed. Otherwise the click would just hit the server gate
                     and dump a raw error at the user. -->
                <button v-if="peerReviewPassedForSelected" class="btn-primary" :disabled="saving" @click="verify">
                  {{ saving ? 'Releasing…' : 'Verify &amp; Release' }}
                </button>
                <span v-else class="text-xs text-amber-700 font-medium">
                  Awaiting Peer Review — a reviewer must close the peer review case first.
                </span>
              </div>
              <h4 class="font-semibold mb-3">Clinical Notes &amp; Sign-off</h4>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
                <div class="sm:col-span-2">
                  <label class="block text-xs text-surface-500 mb-1">Provisional Diagnosis</label>
                  <input v-model="diagnosis" class="input" placeholder="—" />
                </div>
                <div class="sm:col-span-2">
                  <label class="block text-xs text-surface-500 mb-1">Clinical Notes</label>
                  <textarea v-model="clinicalNotes" rows="2" class="input"></textarea>
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
              <!-- Print preference: reserve a blank box on the Lab Report
                   print and optionally upload an image to fill it. -->
              <div class="flex items-start gap-3 text-sm border-t border-surface-100 pt-3 mb-3 flex-wrap">
                <div class="flex-1 min-w-[240px]">
                  <label class="flex items-center gap-2 cursor-pointer select-none">
                    <input id="rs-imgspace" v-model="hasImageSpace" type="checkbox" class="accent-brand-navy-700" />
                    <span>Reserve image space on print</span>
                  </label>
                  <p class="text-xs text-surface-500 mt-0.5 ml-6">Adds a blank box above the signature area; upload an image to fill it.</p>
                </div>
                <input ref="imageSpaceFileInput" type="file" accept="image/*" class="hidden"
                  @change="onPreReleaseImagePicked" />
                <div v-if="imageSpaceImage"
                  class="flex items-center gap-2 px-2 py-1 rounded border border-surface-200 bg-surface-50">
                  <img :src="imageSpaceImage" alt="Image space preview"
                    class="max-h-12 max-w-[80px] object-contain bg-white border border-surface-100 rounded" />
                  <div class="flex flex-col gap-0.5">
                    <button type="button" class="text-xs text-brand-teal-600 hover:underline" @click="imageSpaceFileInput?.click()">Replace</button>
                    <button type="button" class="text-xs text-red-600 hover:underline" @click="clearPreReleaseImage">Remove</button>
                  </div>
                </div>
                <button v-else type="button" class="btn-ghost !py-1 !text-xs self-center"
                  @click="imageSpaceFileInput?.click()">📎 Upload image</button>
              </div>
              <!-- Don't show graphs on print -->
              <div class="flex items-center gap-2 text-sm pt-2 mb-3">
                <input id="rs-hidegraphs" v-model="hideGraphs" type="checkbox" class="accent-brand-navy-700" />
                <label for="rs-hidegraphs" class="cursor-pointer select-none">
                  Don't show graphs on print
                  <span class="text-xs text-surface-500 ml-1">(suppress trend charts)</span>
                </label>
              </div>
              <div class="flex items-center justify-end">
                <button v-if="verifyAllowed" class="btn-primary" :disabled="saving" @click="verify">{{ saving ? 'Releasing…' : 'Verify & Release' }}</button>
                <span v-else-if="!peerReviewPassedForSelected" class="text-xs text-amber-600">
                  Awaiting Peer Review — a reviewer must close the peer review case before Verify &amp; Release unlocks.
                </span>
                <span v-else class="text-xs text-surface-400">Verify &amp; Release unlocks once urgent review is authorized.</span>
              </div>
            </div>
            <div v-else>
              <div class="flex items-center justify-between mb-3">
                <span class="pill-success">Released</span>
                <button class="btn-ghost" @click="printReport">Print Report</button>
              </div>
              <!-- Even after release the technologist may want to change the
                   "image space" preference, swap the image, and reprint. -->
              <div v-if="releasedLabReport[selectedSample.name]"
                class="flex items-start gap-3 text-sm border-t border-surface-100 pt-3 flex-wrap">
                <div class="flex-1 min-w-[240px]">
                  <label :for="`rs-imgspace-released-${selectedSample.name}`" class="flex items-center gap-2 cursor-pointer select-none">
                    <input :id="`rs-imgspace-released-${selectedSample.name}`" type="checkbox"
                      class="accent-brand-navy-700"
                      :checked="releasedLabReport[selectedSample.name].hasImageSpace"
                      :disabled="togglingImageSpace"
                      @change="toggleReleasedImageSpace(($event.target as HTMLInputElement).checked)" />
                    <span>Reserve image space on print</span>
                  </label>
                  <p class="text-xs text-surface-500 mt-0.5 ml-6">Adds a blank box above the signatures; upload an image to fill it.</p>
                </div>
                <input ref="releasedFileInput" type="file" accept="image/*" class="hidden"
                  @change="onReleasedImagePicked" />
                <div v-if="releasedLabReport[selectedSample.name].imageUrl"
                  class="flex items-center gap-2 px-2 py-1 rounded border border-surface-200 bg-surface-50">
                  <img :src="releasedLabReport[selectedSample.name].imageUrl || ''" alt="Image space"
                    class="max-h-12 max-w-[80px] object-contain bg-white border border-surface-100 rounded" />
                  <div class="flex flex-col gap-0.5">
                    <button type="button" class="text-xs text-brand-teal-600 hover:underline"
                      :disabled="togglingImageSpace" @click="releasedFileInput?.click()">Replace</button>
                    <button type="button" class="text-xs text-red-600 hover:underline"
                      :disabled="togglingImageSpace" @click="removeReleasedImage">Remove</button>
                  </div>
                </div>
                <button v-else type="button" class="btn-ghost !py-1 !text-xs self-center"
                  :disabled="togglingImageSpace" @click="releasedFileInput?.click()">📎 Upload image</button>
                <span v-if="togglingImageSpace" class="text-xs text-surface-400 self-center">Saving…</span>
              </div>
              <!-- Don't show graphs on print (released-state mirror) -->
              <div v-if="releasedLabReport[selectedSample.name]"
                class="flex items-center gap-2 text-sm pt-2">
                <input :id="`rs-hidegraphs-released-${selectedSample.name}`" type="checkbox"
                  class="accent-brand-navy-700"
                  :checked="releasedLabReport[selectedSample.name].hideGraphs"
                  :disabled="togglingImageSpace"
                  @change="toggleReleasedHideGraphs(($event.target as HTMLInputElement).checked)" />
                <label :for="`rs-hidegraphs-released-${selectedSample.name}`" class="cursor-pointer select-none">
                  Don't show graphs on print
                  <span class="text-xs text-surface-500 ml-1">(suppress trend charts)</span>
                </label>
              </div>
            </div>
          </div>
        </template>
      </template>
    </div>
  </div>
</template>
