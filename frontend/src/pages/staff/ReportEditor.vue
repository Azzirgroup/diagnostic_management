<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'

const template = ref('MRI Brain Without Contrast – Standard')
const clinical = ref('')
const findings = ref('')
const impression = ref('')
const recommendations = ref('')
const addendum = ref(false)
const patient = ref<any>(null)
const study = ref<any>(null)

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    patient.value = null
    study.value = null
  } catch {
    patient.value = null
    study.value = null
  }
})
</script>

<template>
  <Topbar title="Report Editor" />
  <div class="card p-5 mb-4 flex items-center gap-6 flex-wrap">
    <div class="w-14 h-14 rounded-full bg-brand-teal-100 text-brand-teal-700 flex items-center justify-center font-semibold">{{ patient?.initials || '—' }}</div>
    <div>
      <div class="font-semibold">{{ patient?.name || '—' }} <span v-if="patient?.gender" class="pill-info">{{ patient.gender }}</span></div>
      <div class="text-xs text-surface-500">{{ patient?.meta || '' }}</div>
    </div>
    <div class="text-sm text-surface-500">Study: <span class="text-surface-800">{{ study?.name || '—' }}</span></div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <label class="text-sm text-surface-500">Report Template</label>
          <select v-model="template" class="input w-72">
            <option>MRI Brain Without Contrast – Standard</option>
            <option>MRI Brain – Headache Protocol</option>
            <option>MRI Brain – Epilepsy Protocol</option>
            <option>MRI Brain – Stroke Protocol</option>
          </select>
        </div>
        <div class="space-y-4">
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Clinical History</summary>
            <textarea v-model="clinical" class="input mt-2" rows="3" placeholder="Enter clinical history..." maxlength="500"></textarea>
          </details>
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Findings</summary>
            <textarea v-model="findings" class="input mt-2" rows="6" placeholder="Enter findings..." maxlength="2000"></textarea>
          </details>
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Impression</summary>
            <textarea v-model="impression" class="input mt-2" rows="4" placeholder="Enter impression..." maxlength="1000"></textarea>
          </details>
          <details class="border-b border-surface-100 pb-3" open>
            <summary class="cursor-pointer font-semibold text-sm">Recommendations</summary>
            <textarea v-model="recommendations" class="input mt-2" rows="3" placeholder="Enter recommendations..." maxlength="500"></textarea>
          </details>
          <div class="flex items-center gap-3">
            <label class="text-sm">Addendum (Optional)</label>
            <button class="text-xs px-2 py-1 rounded-full" :class="addendum ? 'bg-brand-teal-500 text-white' : 'bg-surface-200 text-surface-500'" @click="addendum = !addendum">
              {{ addendum ? 'On' : 'Off' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Study Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Modality</dt><dd>{{ study?.modality || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Body Part</dt><dd>{{ study?.body || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Referring Doctor</dt><dd>{{ study?.referrer || '—' }}</dd></div>
        </dl>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Voice Dictation</h3>
        <button class="btn-primary w-full">🎙 Click microphone to start dictation</button>
        <p class="text-xs text-surface-500 mt-2">Voice dictation supports English and Urdu.</p>
      </div>
      <div class="card p-5 space-y-2">
        <button class="btn-ghost w-full">Save Draft</button>
        <button class="btn-secondary w-full">Finalize Report</button>
        <button class="btn-ghost w-full">Request Peer Review</button>
      </div>
    </div>
  </div>
</template>
