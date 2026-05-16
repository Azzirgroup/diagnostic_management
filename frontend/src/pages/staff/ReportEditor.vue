<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { getDoc } from '@/api/client'
import { radiologyApi } from '@/api/adms'

const route = useRoute()
const study = ref<Record<string, unknown> | null>(null)
const studyName = ref<string>((route.params.name as string) || '')
const reportName = ref<string | null>(null)
const clinical = ref('')
const findings = ref('')
const impression = ref('')
const recommendations = ref('')
const isCritical = ref(false)
const busy = ref(false)
const lastSaved = ref('')

async function loadStudy() {
  if (!studyName.value) return
  try {
    const doc = await getDoc<Record<string, unknown>>('Service Request', studyName.value)
    study.value = doc
    clinical.value = String(doc.clinical_history_text || '')
  } catch {
    study.value = null
  }
}

onMounted(loadStudy)

async function save(status: 'Draft' | 'Pending' | 'Completed') {
  busy.value = true
  try {
    const r = await radiologyApi.saveReport({
      name: reportName.value || undefined,
      patient: (study.value?.patient as string) || undefined,
      service_request: studyName.value || undefined,
      findings: findings.value,
      impression: impression.value,
      recommendations: recommendations.value,
      is_critical: isCritical.value ? 1 : 0,
      status,
    })
    reportName.value = r.name
    lastSaved.value = new Date().toLocaleTimeString()
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Report Editor" />
  <div class="card p-5 mb-4 flex items-center gap-6 flex-wrap">
    <div>
      <div class="font-semibold">{{ (study?.patient_name as string) || '—' }}</div>
      <div class="text-xs text-surface-500">Study: <span class="text-surface-800">{{ studyName || '—' }}</span></div>
    </div>
    <div class="text-sm text-surface-500">Modality: <span class="text-surface-800">{{ (study?.imaging_modality as string) || '—' }}</span></div>
    <div class="text-sm text-surface-500">Body Part: <span class="text-surface-800">{{ (study?.imaging_body_part as string) || '—' }}</span></div>
    <div v-if="lastSaved" class="ml-auto text-xs text-surface-500">Last saved {{ lastSaved }}</div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="space-y-4">
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Clinical History</summary>
            <textarea v-model="clinical" class="input mt-2 w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="3" placeholder="Enter clinical history..." maxlength="500"></textarea>
          </details>
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Findings</summary>
            <textarea v-model="findings" class="input mt-2 w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="6" placeholder="Enter findings..." maxlength="4000"></textarea>
          </details>
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Impression</summary>
            <textarea v-model="impression" class="input mt-2 w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="4" placeholder="Enter impression..." maxlength="2000"></textarea>
          </details>
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Recommendations</summary>
            <textarea v-model="recommendations" class="input mt-2 w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="3" placeholder="Enter recommendations..." maxlength="1000"></textarea>
          </details>
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" v-model="isCritical" />
            Mark this report as <span class="text-status-danger font-semibold">Critical</span>
          </label>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Study Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Modality</dt><dd>{{ (study?.imaging_modality as string) || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Body Part</dt><dd>{{ (study?.imaging_body_part as string) || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Referring Doctor</dt><dd>{{ (study?.practitioner as string) || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd>{{ (study?.status as string) || '—' }}</dd></div>
        </dl>
      </div>
      <div class="card p-5 space-y-2">
        <button class="btn-ghost w-full" :disabled="busy" @click="save('Draft')">Save Draft</button>
        <button class="btn-secondary w-full" :disabled="busy" @click="save('Pending')">Submit for Verification</button>
        <button class="btn-primary w-full" :disabled="busy" @click="save('Completed')">Finalize Report</button>
      </div>
    </div>
  </div>
</template>
