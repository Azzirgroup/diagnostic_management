<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { labReportsApi, type LabReportDetail, type LabReportResultRow } from '@/api/adms'
import { frappeError } from '@/api/client'

// Frontend detail page for a single Lab Report — what the LabReports list now
// links to instead of dropping the user into the ERPNext Desk form.

const route = useRoute()
const router = useRouter()
const detail = ref<LabReportDetail | null>(null)
const loading = ref(false)
const error = ref('')

async function load() {
  const name = route.params.name as string | undefined
  if (!name) return
  loading.value = true; error.value = ''
  try { detail.value = await labReportsApi.detail(name) }
  catch (e: any) { error.value = frappeError(e, 'Failed to load Lab Report') }
  finally { loading.value = false }
}
onMounted(load)
watch(() => route.params.name, load)

function openPrint() {
  if (!detail.value) return
  const params = new URLSearchParams({
    doctype: 'Lab Report', name: detail.value.name, format: 'Lab Report', no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}
function openDeskForm() {
  if (!detail.value) return
  window.open(`/app/lab-report/${detail.value.name}`, '_blank')
}

// Persistent "Reserve image space on print" toggle + optional image upload.
const savingImageSpace = ref(false)
const imageSpaceSavedAt = ref<number | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

async function toggleImageSpace(checked: boolean) {
  if (!detail.value) return
  savingImageSpace.value = true
  try {
    const res = await labReportsApi.setImageSpace(detail.value.name, checked ? 1 : 0)
    detail.value.custom_has_image_space = res.custom_has_image_space
    detail.value.custom_image_space_image = res.custom_image_space_image
    imageSpaceSavedAt.value = Date.now()
    setTimeout(() => { imageSpaceSavedAt.value = null }, 2000)
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to update image-space preference')
  } finally {
    savingImageSpace.value = false
  }
}

// File → data URL → persist on Lab Report. We keep it as a data URL so the
// print HTML can embed it directly via <img src="..."> without an extra
// File doc roundtrip. Frappe's Attach Image field accepts a data URL string.
async function onImagePicked(ev: Event) {
  if (!detail.value) return
  const target = ev.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    error.value = 'Please pick an image file (PNG, JPG, etc.)'
    target.value = ''; return
  }
  if (file.size > 4 * 1024 * 1024) {
    error.value = 'Image must be under 4 MB.'
    target.value = ''; return
  }
  const dataUrl: string = await new Promise((resolve, reject) => {
    const r = new FileReader()
    r.onload = () => resolve(r.result as string)
    r.onerror = () => reject(new Error('Failed to read file'))
    r.readAsDataURL(file)
  })
  savingImageSpace.value = true
  try {
    // Auto-tick the checkbox when the user uploads — they obviously want it.
    const res = await labReportsApi.setImageSpace(detail.value.name, 1, dataUrl)
    detail.value.custom_has_image_space = res.custom_has_image_space
    detail.value.custom_image_space_image = res.custom_image_space_image
    imageSpaceSavedAt.value = Date.now()
    setTimeout(() => { imageSpaceSavedAt.value = null }, 2000)
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to upload image')
  } finally {
    savingImageSpace.value = false
    target.value = ''  // allow re-uploading the same file
  }
}

async function removeImage() {
  if (!detail.value) return
  savingImageSpace.value = true
  try {
    const res = await labReportsApi.setImageSpace(
      detail.value.name, detail.value.custom_has_image_space ? 1 : 0, null, 1)
    detail.value.custom_image_space_image = res.custom_image_space_image
    imageSpaceSavedAt.value = Date.now()
    setTimeout(() => { imageSpaceSavedAt.value = null }, 2000)
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to remove image')
  } finally { savingImageSpace.value = false }
}

// "Don't show graphs" toggle — sister flag to has_image_space, lives in
// the same API endpoint, persists on the same Lab Report row.
async function toggleShowGraphs(checked: boolean) {
  if (!detail.value) return
  savingImageSpace.value = true
  try {
    const res = await labReportsApi.setImageSpace(
      detail.value.name, detail.value.custom_has_image_space ? 1 : 0,
      undefined, 0, checked ? 1 : 0)
    detail.value.custom_show_graphs = res.custom_show_graphs
    imageSpaceSavedAt.value = Date.now()
    setTimeout(() => { imageSpaceSavedAt.value = null }, 2000)
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to update show-graphs preference')
  } finally { savingImageSpace.value = false }
}

// Patient age (years) for the header.
function patientAge(dob?: string): string {
  if (!dob) return ''
  try {
    const birth = new Date(dob)
    const now = new Date()
    let years = now.getFullYear() - birth.getFullYear()
    const m = now.getMonth() - birth.getMonth()
    if (m < 0 || (m === 0 && now.getDate() < birth.getDate())) years--
    return `${years} y`
  } catch { return '' }
}

// Helpers to display the result tables consistently.
const numericRows = computed(() => detail.value?.numeric_results ?? [])
const singleRows = computed(() => detail.value?.lab_report_tests ?? [])
const groupedRows = computed(() => detail.value?.grouped_results ?? [])
const descriptiveRows = computed(() => detail.value?.descriptive_results ?? [])
const qualitativeRows = computed(() => detail.value?.qualitative_results ?? [])

// Group rows by section header (test_category, falling back to group_name).
function groupedBySection(rows: LabReportResultRow[]) {
  const out: Record<string, LabReportResultRow[]> = {}
  for (const r of rows) {
    const key = r.test_category || r.group_name || 'General'
    if (!out[key]) out[key] = []
    out[key].push(r)
  }
  return out
}

const numericGrouped = computed(() => groupedBySection(numericRows.value))
const singleGrouped = computed(() => groupedBySection(singleRows.value))
const groupedGrouped = computed(() => groupedBySection(groupedRows.value))
const descriptiveGrouped = computed(() => groupedBySection(descriptiveRows.value))
const qualitativeGrouped = computed(() => groupedBySection(qualitativeRows.value))

function flagClass(r: LabReportResultRow): string {
  if (!r.status) return ''
  if (r.status === 'High') return 'bg-red-100 text-red-700'
  if (r.status === 'Low') return 'bg-blue-100 text-blue-700'
  if (r.status === 'Critical') return 'bg-red-200 text-red-900 font-bold'
  if (r.status === 'Normal') return 'bg-emerald-100 text-emerald-700'
  return 'bg-surface-100 text-surface-600'
}
</script>

<template>
  <Topbar :title="`Lab Report · ${detail?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back to Lab Reports</button>

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>
  <div v-else-if="error" class="card p-6 text-sm text-status-danger">{{ error }}</div>
  <div v-else-if="!detail" class="card p-12 text-center text-surface-400">Report not found.</div>

  <div v-else class="space-y-4">
    <!-- Header card with patient + report meta + actions -->
    <div class="card p-5">
      <div class="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h2 class="text-xl font-semibold text-surface-800">{{ detail.patient_name || detail.patient?.patient_name || '—' }}</h2>
          <div class="text-sm text-surface-500 mt-1">
            <span v-if="detail.patient_sex">{{ detail.patient_sex }}</span>
            <span v-if="patientAge(detail.patient?.dob)" class="ml-2">{{ patientAge(detail.patient?.dob) }}</span>
            <span v-if="detail.patient?.name" class="ml-2">· MRN <span class="text-surface-700">{{ detail.patient.name }}</span></span>
          </div>
          <div class="text-xs text-surface-400 mt-1">
            Report ID: <span class="font-medium text-surface-700">{{ detail.name }}</span>
            <span v-if="detail.report_date" class="ml-3">· Date: {{ detail.report_date }}</span>
            <span v-if="detail.department" class="ml-3">· Dept: {{ detail.department }}</span>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <StatusPill :status="detail.status"/>
          <button class="btn-primary !py-1.5 !text-xs" @click="openPrint">Print</button>
          <button class="btn-ghost !py-1.5 !text-xs" @click="openDeskForm">Open in Desk</button>
        </div>
      </div>

      <div v-if="detail.samples?.length" class="mt-3 pt-3 border-t border-surface-100 text-xs text-surface-500">
        <span class="font-medium text-surface-600">Sample(s):</span>
        <span v-for="s in detail.samples" :key="s.lab_sample" class="ml-2 inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-50">
          {{ s.lab_sample }}
          <span v-if="s.sample_type" class="text-surface-400">· {{ s.sample_type }}</span>
        </span>
      </div>

      <!-- Print preference: reserve a blank box above the signatures, and
           optionally drop an image into that box (stamp / scanned signature /
           anything). Persists onto the Lab Report doc.  -->
      <div class="mt-3 pt-3 border-t border-surface-100 flex items-start gap-4 flex-wrap">
        <div class="flex-1 min-w-[260px]">
          <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
            <input type="checkbox" class="accent-brand-navy-700"
              :checked="!!detail.custom_has_image_space"
              :disabled="savingImageSpace"
              @change="toggleImageSpace(($event.target as HTMLInputElement).checked)" />
            <span class="font-medium text-surface-700">Reserve image space on print</span>
          </label>
          <p class="text-xs text-surface-500 mt-0.5">
            Adds a 6cm blank box above the signature section. Upload an image to fill it; leave empty for a manual stamp.
          </p>
        </div>
        <!-- Image upload + thumbnail -->
        <div class="flex items-center gap-2">
          <input ref="fileInputRef" type="file" accept="image/*" class="hidden"
            :disabled="savingImageSpace" @change="onImagePicked" />
          <div v-if="detail.custom_image_space_image"
            class="flex items-center gap-2 px-2 py-1 rounded border border-surface-200 bg-surface-50">
            <img :src="detail.custom_image_space_image" alt="Image space"
              class="max-h-12 max-w-[80px] object-contain bg-white border border-surface-100 rounded" />
            <div class="flex flex-col gap-0.5">
              <button class="text-xs text-brand-teal-600 hover:underline"
                :disabled="savingImageSpace" @click="fileInputRef?.click()">Replace</button>
              <button class="text-xs text-red-600 hover:underline"
                :disabled="savingImageSpace" @click="removeImage">Remove</button>
            </div>
          </div>
          <button v-else class="btn-ghost !py-1 !text-xs"
            :disabled="savingImageSpace" @click="fileInputRef?.click()">
            📎 Upload image
          </button>
        </div>
        <span v-if="savingImageSpace" class="text-xs text-surface-400 self-center">Saving…</span>
        <span v-else-if="imageSpaceSavedAt" class="text-xs text-emerald-600 self-center">Saved</span>
      </div>

      <!-- Show graphs on print (hidden by default) -->
      <div class="mt-2 pt-2 border-t border-surface-100">
        <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
          <input type="checkbox" class="accent-brand-navy-700"
            :checked="!!detail.custom_show_graphs"
            :disabled="savingImageSpace"
            @change="toggleShowGraphs(($event.target as HTMLInputElement).checked)" />
          <span class="font-medium text-surface-700">Show graphs on print</span>
          <span class="text-xs text-surface-500">Off by default; tick to add trend charts.</span>
        </label>
      </div>
    </div>

    <!-- Numeric (Compound) — grouped by section -->
    <div v-if="numericRows.length" class="card p-5">
      <h3 class="font-semibold mb-3">Numeric Results</h3>
      <div v-for="(rows, section) in numericGrouped" :key="`num-${section}`" class="mb-4">
        <div v-if="Object.keys(numericGrouped).length > 1" class="text-sm font-medium text-surface-700 mb-2">{{ section }}</div>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Analyte</th><th>Result</th><th>Unit</th><th>Reference</th><th>Flag</th>
          </tr></thead>
          <tbody>
            <tr v-for="r in rows" :key="r.name"
              :class="['border-b border-surface-100', r.is_abnormal && 'bg-red-50/40']">
              <td class="py-2">{{ r.test_name }}</td>
              <td class="font-medium">
                {{ r.result_value || '—' }}
                <span v-if="r.is_critical" class="text-red-700 font-bold ml-1">!!</span>
              </td>
              <td class="text-surface-500">{{ r.uom || '—' }}</td>
              <td class="text-surface-500">{{ r.reference_range || '—' }}</td>
              <td>
                <span v-if="r.status" :class="['text-xs font-semibold px-1.5 py-0.5 rounded', flagClass(r)]">
                  {{ r.status }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="detail.section_comments?.[section]" class="mt-2 px-3 py-2 rounded bg-amber-50 border-l-4 border-amber-400 text-xs text-amber-800 italic">
          {{ detail.section_comments[section] }}
        </div>
      </div>
    </div>

    <!-- Single (Lab Report Tests) -->
    <div v-if="singleRows.length" class="card p-5">
      <h3 class="font-semibold mb-3">Single Tests</h3>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">Test</th><th>Result</th><th>Unit</th><th>Reference</th><th>Flag</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in singleRows" :key="r.name"
            :class="['border-b border-surface-100', r.is_abnormal && 'bg-red-50/40']">
            <td class="py-2">{{ r.test_name }}</td>
            <td class="font-medium">{{ r.result_value || '—' }}</td>
            <td class="text-surface-500">{{ r.uom || '—' }}</td>
            <td class="text-surface-500">{{ r.reference_range || '—' }}</td>
            <td><span v-if="r.status" :class="['text-xs font-semibold px-1.5 py-0.5 rounded', flagClass(r)]">{{ r.status }}</span></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Grouped -->
    <div v-if="groupedRows.length" class="card p-5">
      <h3 class="font-semibold mb-3">Grouped Tests</h3>
      <div v-for="(rows, group) in groupedGrouped" :key="`grp-${group}`" class="mb-4">
        <div class="text-sm font-medium text-surface-700 mb-2">{{ group }}</div>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Analyte</th><th>Result</th><th>Unit</th><th>Reference</th><th>Flag</th>
          </tr></thead>
          <tbody>
            <tr v-for="r in rows" :key="r.name"
              :class="['border-b border-surface-100', r.is_abnormal && 'bg-red-50/40']">
              <td class="py-2">{{ r.test_name }}</td>
              <td class="font-medium">{{ r.result_value || '—' }}</td>
              <td class="text-surface-500">{{ r.uom || '—' }}</td>
              <td class="text-surface-500">{{ r.reference_range || '—' }}</td>
              <td><span v-if="r.status" :class="['text-xs font-semibold px-1.5 py-0.5 rounded', flagClass(r)]">{{ r.status }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-if="detail.section_comments?.[group]" class="mt-2 px-3 py-2 rounded bg-amber-50 border-l-4 border-amber-400 text-xs text-amber-800 italic">
          {{ detail.section_comments[group] }}
        </div>
      </div>
    </div>

    <!-- Qualitative -->
    <div v-if="qualitativeRows.length" class="card p-5">
      <h3 class="font-semibold mb-3">Qualitative Tests</h3>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">Test</th><th>Result</th><th>Flag</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in qualitativeRows" :key="r.name"
            :class="['border-b border-surface-100', r.is_abnormal && 'bg-red-50/40']">
            <td class="py-2">{{ r.test_name }}</td>
            <td class="font-medium">{{ r.result_value || '—' }}</td>
            <td>
              <span v-if="r.is_abnormal" class="text-xs font-semibold px-1.5 py-0.5 rounded bg-red-100 text-red-700">Abnormal</span>
              <span v-else class="text-xs font-semibold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">Normal</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Descriptive -->
    <div v-if="descriptiveRows.length" class="card p-5">
      <h3 class="font-semibold mb-3">Descriptive Tests</h3>
      <div v-for="r in descriptiveRows" :key="r.name" class="mb-3">
        <div class="text-xs text-surface-500">{{ r.test_name }}</div>
        <p class="text-sm text-surface-800 whitespace-pre-wrap mt-1">{{ r.result_value || '—' }}</p>
      </div>
    </div>

    <!-- Clinical sign-off (accreditation + pathologist remarks intentionally
         hidden per requirements; columns kept in case existing data has values). -->
    <div v-if="detail.diagnosis || detail.clinical_notes || detail.pathologist_name" class="card p-5">
      <h3 class="font-semibold mb-3">Clinical Sign-off</h3>
      <dl class="text-sm space-y-2">
        <div v-if="detail.diagnosis">
          <dt class="text-xs text-surface-500">Provisional Diagnosis</dt>
          <dd class="text-surface-800">{{ detail.diagnosis }}</dd>
        </div>
        <div v-if="detail.clinical_notes">
          <dt class="text-xs text-surface-500">Clinical Notes</dt>
          <dd class="text-surface-800 whitespace-pre-wrap">{{ detail.clinical_notes }}</dd>
        </div>
        <div v-if="detail.pathologist_name">
          <dt class="text-xs text-surface-500">Reported By</dt>
          <dd class="text-surface-800">{{ detail.pathologist_name }}
            <span v-if="detail.pathologist_qualification" class="text-surface-500">· {{ detail.pathologist_qualification }}</span>
          </dd>
        </div>
      </dl>
    </div>

    <!-- Signatures -->
    <div v-if="detail.lab_technician_signature || detail.pathologist_signature" class="card p-5">
      <h3 class="font-semibold mb-3">Signatures</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div v-if="detail.lab_technician_signature">
          <div class="text-xs text-surface-500 mb-1">Lab Technologist</div>
          <img :src="detail.lab_technician_signature" alt="Lab Technologist signature" class="max-h-20 border border-surface-200 rounded p-1 bg-white" />
        </div>
        <div v-if="detail.pathologist_signature">
          <div class="text-xs text-surface-500 mb-1">Consultant Pathologist</div>
          <img :src="detail.pathologist_signature" alt="Pathologist signature" class="max-h-20 border border-surface-200 rounded p-1 bg-white" />
        </div>
      </div>
    </div>

    <!-- Empty-state -->
    <div v-if="!numericRows.length && !singleRows.length && !groupedRows.length && !descriptiveRows.length && !qualitativeRows.length" class="card p-6 text-center text-surface-400">
      This report has no result rows yet.
    </div>
  </div>
</template>
