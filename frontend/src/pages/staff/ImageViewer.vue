<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { call, getDoc } from '@/api/client'

const route = useRoute()
const router = useRouter()
const study = ref<Record<string, any> | null>(null)
const files = ref<Array<{ name: string; file_url: string; file_name: string; is_private: number }>>([])
const loading = ref(false)
const uploading = ref(false)
const activeFile = ref<typeof files.value[number] | null>(null)
const error = ref('')

const studyName = computed(() => (route.params.name as string) || '')

function isImage(f: { file_name?: string; file_url?: string }) {
  const x = (f.file_name || f.file_url || '').toLowerCase()
  return /\.(png|jpe?g|gif|webp|bmp|tiff?|svg)$/.test(x)
}
function isDicom(f: { file_name?: string; file_url?: string }) {
  const x = (f.file_name || f.file_url || '').toLowerCase()
  return /\.(dcm|dicom)$/.test(x)
}
function isPdf(f: { file_name?: string; file_url?: string }) {
  return /\.pdf$/i.test(f.file_name || f.file_url || '')
}

async function loadStudy() {
  if (!studyName.value) return
  loading.value = true
  try {
    study.value = await getDoc<Record<string, any>>('Service Request', studyName.value)
    await loadFiles()
  } catch {
    study.value = null
  } finally { loading.value = false }
}

async function loadFiles() {
  if (!studyName.value) return
  try {
    const list = await call<Array<any>>('frappe.client.get_list', {
      doctype: 'File',
      fields: ['name', 'file_name', 'file_url', 'is_private'],
      filters: { attached_to_doctype: 'Service Request', attached_to_name: studyName.value },
      limit_page_length: 50,
      order_by: 'creation desc',
    })
    files.value = list || []
    activeFile.value = files.value.find(isImage) || files.value[0] || null
  } catch {
    files.value = []
  }
}

async function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  if (!input.files || !input.files.length || !studyName.value) return
  uploading.value = true
  error.value = ''
  try {
    for (const f of Array.from(input.files)) {
      const form = new FormData()
      form.append('file', f, f.name)
      form.append('doctype', 'Service Request')
      form.append('docname', studyName.value)
      form.append('folder', 'Home/Attachments')
      form.append('is_private', '1')
      const resp = await fetch('/api/method/upload_file', {
        method: 'POST',
        body: form,
        credentials: 'include',
        headers: {
          'X-Frappe-CSRF-Token': (window as any).csrf_token || '',
        },
      })
      if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`)
    }
    input.value = ''
    await loadFiles()
  } catch (e: any) {
    error.value = e?.message || 'Upload failed'
  } finally { uploading.value = false }
}

onMounted(loadStudy)
</script>

<template>
  <Topbar :title="`Imaging Study · ${studyName || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading study…</div>

  <div v-else-if="study" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-lg">{{ study.patient_name }}</h3>
            <div class="text-xs text-surface-500 mt-1">
              {{ study.imaging_modality || study.template_dn || '—' }}
              <span v-if="study.imaging_body_part"> · {{ study.imaging_body_part }}</span>
            </div>
          </div>
          <StatusPill :status="(study.status || '').replace('-Request Status','')" />
        </div>

        <div v-if="activeFile" class="bg-surface-900 rounded-lg p-2 flex items-center justify-center min-h-[400px]">
          <img v-if="isImage(activeFile)" :src="activeFile.file_url" :alt="activeFile.file_name" class="max-h-[600px] mx-auto" />
          <iframe v-else-if="isPdf(activeFile)" :src="activeFile.file_url" class="w-full h-[600px] bg-white rounded"></iframe>
          <div v-else-if="isDicom(activeFile)" class="text-center text-white p-8">
            <div class="text-2xl mb-2">DICOM</div>
            <div class="text-sm">{{ activeFile.file_name }}</div>
            <div class="text-xs text-surface-300 mt-1">Inline DICOM rendering requires a viewer (Cornerstone.js / Orthanc).</div>
            <a :href="activeFile.file_url" target="_blank" class="inline-block mt-3 text-brand-teal-300 hover:underline text-sm">Download to view in DICOM viewer →</a>
          </div>
          <div v-else class="text-center text-white p-8">
            <div class="text-2xl mb-2">File</div>
            <div class="text-sm">{{ activeFile.file_name }}</div>
            <a :href="activeFile.file_url" target="_blank" class="inline-block mt-3 text-brand-teal-300 hover:underline text-sm">Download →</a>
          </div>
        </div>
        <div v-else class="bg-surface-50 border-2 border-dashed border-surface-200 rounded-lg p-10 text-center text-surface-400">
          No images attached yet. Upload below to add to this study.
        </div>
      </div>

      <div v-if="files.length" class="card p-4">
        <div class="text-xs text-surface-500 mb-3 uppercase tracking-wider">Series &amp; Files ({{ files.length }})</div>
        <div class="flex gap-2 overflow-x-auto">
          <button v-for="f in files" :key="f.name"
            :class="['flex-shrink-0 w-28 h-28 rounded border-2 overflow-hidden bg-surface-100',
              activeFile?.name === f.name ? 'border-brand-teal-500' : 'border-surface-200']"
            @click="activeFile = f">
            <img v-if="isImage(f)" :src="f.file_url" :alt="f.file_name" class="w-full h-full object-cover" />
            <div v-else class="w-full h-full flex flex-col items-center justify-center text-xs text-surface-500 p-1">
              <span class="text-xl mb-1">{{ isDicom(f) ? 'DCM' : isPdf(f) ? 'PDF' : 'FILE' }}</span>
              <span class="truncate w-full text-center">{{ f.file_name }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Study Info</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Study ID</dt><dd>{{ study.name }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Modality</dt><dd>{{ study.imaging_modality || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Body Part</dt><dd>{{ study.imaging_body_part || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Contrast</dt><dd>{{ study.contrast_required ? 'Yes' : 'No' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Priority</dt><dd>{{ (study.priority || '').replace('-Priority','') || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Practitioner</dt><dd>{{ study.practitioner || '—' }}</dd></div>
          <div v-if="study.clinical_history_text" class="pt-3 border-t border-surface-100">
            <dt class="text-surface-500">Clinical History</dt>
            <dd class="mt-1 whitespace-pre-wrap text-surface-700">{{ study.clinical_history_text }}</dd>
          </div>
        </dl>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-3">Upload Image / File</h3>
        <input type="file" multiple accept="image/*,.pdf,.dcm,.dicom"
          class="block w-full text-sm text-surface-500 file:mr-3 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-brand-teal-50 file:text-brand-teal-700 hover:file:bg-brand-teal-100"
          :disabled="uploading"
          @change="onFileChange" />
        <p v-if="error" class="text-sm text-status-danger mt-2">{{ error }}</p>
        <p v-if="uploading" class="text-sm text-surface-500 mt-2">Uploading…</p>
        <p class="text-xs text-surface-400 mt-2">JPG, PNG, PDF, DICOM. Files attach to the imaging order.</p>
      </div>

      <div class="card p-5">
        <button class="btn-primary w-full mb-2" @click="router.push(`/radiology/report/${studyName}`)">Open Report Editor</button>
        <button class="btn-ghost w-full" @click="router.push('/radiology/worklist')">Back to Worklist</button>
      </div>
    </div>
  </div>

  <div v-else class="card p-12 text-center text-surface-400">
    Study not found.
    <button class="btn-ghost block mx-auto mt-3" @click="router.push('/radiology/worklist')">Back to Worklist</button>
  </div>
</template>
