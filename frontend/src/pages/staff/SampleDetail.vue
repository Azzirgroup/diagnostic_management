<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { getDoc, call } from '@/api/client'

const route = useRoute()
const router = useRouter()
const sample = ref<any>(null)
const rejectionReason = ref('Hemolysis')
const severity = ref<'Low' | 'Medium' | 'High'>('High')
const notes = ref('')
const recollection = ref(true)
const targetDate = ref('')
const targetTime = ref('09:00')
const notify = ref(true)
const submitting = ref(false)

onMounted(async () => {
  sample.value = await getDoc('Sample Collection', route.params.name as string)
})

async function confirmRejection() {
  submitting.value = true
  try {
    await call('diagnostic_management.api.sample.reject', {
      sample: sample.value.name,
      reason: rejectionReason.value,
      severity: severity.value,
      notes: notes.value,
      recollection_required: recollection.value,
      target_date: targetDate.value,
      target_time: targetTime.value,
      notify_caller: notify.value,
    })
    router.push('/lab/accession')
  } catch {
    // backend handles audit; surface a soft toast in real impl
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Topbar title="Sample Detail / Rejection" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back to Samples</button>
  <div v-if="sample" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-4">Sample Overview</h3>
        <dl class="grid grid-cols-2 gap-y-3 text-sm">
          <dt class="text-surface-500">Sample ID</dt><dd>{{ sample.name }}</dd>
          <dt class="text-surface-500">Specimen Type</dt><dd>{{ sample.sample || '—' }}</dd>
          <dt class="text-surface-500">Volume</dt><dd>{{ sample.sample_qty || '—' }}</dd>
          <dt class="text-surface-500">Container</dt><dd>{{ sample.container || '—' }}</dd>
          <dt class="text-surface-500">Collected At</dt><dd>{{ sample.collected_time }}</dd>
        </dl>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Specimen Condition</h3>
        <ul class="text-sm space-y-1.5">
          <li class="flex justify-between"><span>Hemolysis</span><span class="text-status-warning">Moderate</span></li>
          <li class="flex justify-between"><span>Clot Detected</span><span class="text-status-success">No</span></li>
          <li class="flex justify-between"><span>Lipemia</span><span class="text-status-success">No</span></li>
          <li class="flex justify-between"><span>Volume Insufficient</span><span class="text-status-danger">Yes (&lt; 1.0 mL)</span></li>
        </ul>
      </div>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-4 flex items-center justify-between">
        <span>Rejection Workflow</span>
        <span class="pill-danger">REJECTED</span>
      </h3>
      <label class="block text-xs text-surface-500 mb-1">Rejection Reason</label>
      <select v-model="rejectionReason" class="input mb-3">
        <option>Hemolysis</option>
        <option>Clotted</option>
        <option>Insufficient Volume</option>
        <option>Wrong Tube</option>
        <option>Other</option>
      </select>
      <div class="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Severity</label>
          <select v-model="severity" class="input"><option>Low</option><option>Medium</option><option>High</option></select>
        </div>
        <div class="flex items-end">
          <label class="flex items-center gap-2 text-sm">
            <input v-model="notify" type="checkbox" class="accent-brand-teal-500"/>
            Notify caller/doctor
          </label>
        </div>
      </div>
      <label class="flex items-center gap-2 text-sm mb-3">
        <input v-model="recollection" type="checkbox" class="accent-brand-teal-500"/>
        Recollection Required
      </label>
      <div v-if="recollection" class="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Target Date</label>
          <input v-model="targetDate" type="date" class="input"/>
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Target Time</label>
          <input v-model="targetTime" type="time" class="input"/>
        </div>
      </div>
      <label class="block text-xs text-surface-500 mb-1">Corrective Action / Notes</label>
      <textarea v-model="notes" class="input mb-3" rows="3" placeholder="Advise phlebotomist to avoid tourniquet >1 min. Ensure proper mixing and adequate fill volume."></textarea>
      <button class="btn-primary w-full" :disabled="submitting" @click="confirmRejection">
        Confirm Rejection
      </button>
      <button class="btn-secondary w-full mt-2">Request Recollection</button>
      <button class="btn-ghost w-full mt-2">Override</button>
    </div>
  </div>
</template>
