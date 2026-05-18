<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { getDoc } from '@/api/client'
import { sampleApi } from '@/api/adms'

const route = useRoute()
const router = useRouter()
const sample = ref<Record<string, any> | null>(null)

// Rejection form state — collapsed until the user clicks "Reject Sample".
const showReject = ref(false)
const rejectionReason = ref<'Haemolysed' | 'Clotted' | 'Insufficient' | 'Wrong Tube' | 'Other'>('Haemolysed')
const severity = ref<'Low' | 'Medium' | 'High'>('High')
const notes = ref('')
const recollection = ref(true)
const targetDate = ref('')
const targetTime = ref('09:00')
const notify = ref(true)

// Acceptance form state.
const destination = ref('')
const acceptNote = ref('')

const submitting = ref(false)

async function load() {
  try {
    sample.value = await getDoc('Sample Collection', route.params.name as string)
  } catch {
    sample.value = null
  }
}
onMounted(load)

const condition = computed(() => sample.value?.received_condition as string | undefined)
const isAccepted = computed(() => condition.value === 'Acceptable')
const isRejected = computed(() => !!condition.value && condition.value !== 'Acceptable')
const isPending = computed(() => !condition.value)

async function confirmAccept() {
  if (!sample.value) return
  submitting.value = true
  try {
    await sampleApi.accept(sample.value.name, destination.value || undefined, acceptNote.value)
    await load()
    destination.value = ''
    acceptNote.value = ''
  } finally { submitting.value = false }
}

async function confirmReject() {
  if (!sample.value) return
  submitting.value = true
  try {
    await sampleApi.reject({
      sample: sample.value.name,
      reason: rejectionReason.value,
      severity: severity.value,
      notes: notes.value,
      recollection_required: recollection.value,
      target_date: targetDate.value,
      target_time: targetTime.value,
      notify_caller: notify.value,
    })
    showReject.value = false
    await load()
  } finally { submitting.value = false }
}

function printLabel() {
  if (!sample.value) return
  const params = new URLSearchParams({
    doctype: 'Sample Collection',
    name: sample.value.name as string,
    format: 'Specimen Label',
    no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}

function downloadLabelPdf() {
  if (!sample.value) return
  const params = new URLSearchParams({
    doctype: 'Sample Collection',
    name: sample.value.name as string,
    format: 'Specimen Label',
    no_letterhead: '0',
  })
  window.open(`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Sample · ${sample?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="sample" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h3 class="font-semibold text-lg">{{ sample.name }}</h3>
            <div class="text-sm text-surface-500 mt-1">{{ sample.patient_name }} · MRN {{ sample.patient }}</div>
          </div>
          <div class="flex items-center gap-2">
            <StatusPill :status="sample.status || 'Pending'" />
            <span v-if="isAccepted" class="pill-success">Accepted</span>
            <span v-if="isRejected" class="pill-danger">Rejected · {{ condition }}</span>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-4">Sample Details</h3>
        <dl class="grid grid-cols-2 gap-y-3 text-sm">
          <dt class="text-surface-500">Sample ID</dt><dd>{{ sample.name }}</dd>
          <dt class="text-surface-500">Specimen Type</dt><dd>{{ sample.sample || '—' }}</dd>
          <dt class="text-surface-500">Volume</dt><dd>{{ sample.sample_qty ?? '—' }} {{ sample.sample_uom || '' }}</dd>
          <dt class="text-surface-500">Barcode</dt><dd class="font-mono">{{ sample.barcode || '—' }}</dd>
          <dt class="text-surface-500">Collected By</dt><dd>{{ sample.collected_by || '—' }}</dd>
          <dt class="text-surface-500">Collected At</dt><dd>{{ (sample.collected_time as string)?.split('.')[0] || '—' }}</dd>
          <dt class="text-surface-500">Collection Point</dt><dd>{{ sample.collection_point || '—' }}</dd>
          <dt class="text-surface-500">Order (Service Request)</dt><dd>{{ sample.service_request || '—' }}</dd>
          <dt class="text-surface-500">Received Condition</dt><dd>{{ condition || 'Not recorded' }}</dd>
          <template v-if="sample.rejection_reason_text">
            <dt class="text-surface-500">Rejection Notes</dt>
            <dd class="text-status-danger">{{ sample.rejection_reason_text }}</dd>
          </template>
        </dl>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Actions</h3>
        <button class="btn-secondary w-full mb-2" @click="printLabel">Print Label</button>
        <button class="btn-ghost w-full mb-2" @click="downloadLabelPdf">Download PDF</button>
      </div>

      <div v-if="isPending" class="card p-5">
        <h3 class="font-semibold mb-3">Accept Sample</h3>
        <input v-model="destination" placeholder="Route to bench (optional)" class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-2" />
        <textarea v-model="acceptNote" rows="2" placeholder="Acceptance notes" class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-2"></textarea>
        <button class="btn-primary w-full" :disabled="submitting" @click="confirmAccept">Accept &amp; Route</button>
        <button class="btn-danger-ghost w-full mt-2" @click="showReject = !showReject">{{ showReject ? 'Hide rejection form' : 'Reject Sample…' }}</button>
      </div>

      <div v-if="isPending && showReject" class="card p-5">
        <h3 class="font-semibold mb-3 text-status-danger">Rejection Workflow</h3>
        <label class="block text-xs text-surface-500 mb-1">Reason</label>
        <select v-model="rejectionReason" class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-3">
          <option>Haemolysed</option>
          <option>Clotted</option>
          <option>Insufficient</option>
          <option>Wrong Tube</option>
          <option>Other</option>
        </select>
        <div class="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label class="block text-xs text-surface-500 mb-1">Severity</label>
            <select v-model="severity" class="w-full px-2 py-2 rounded border border-surface-200 text-sm">
              <option>Low</option><option>Medium</option><option>High</option>
            </select>
          </div>
          <div class="flex items-end">
            <label class="flex items-center gap-2 text-sm">
              <input v-model="notify" type="checkbox" class="accent-brand-teal-500"/> Notify caller
            </label>
          </div>
        </div>
        <label class="flex items-center gap-2 text-sm mb-3">
          <input v-model="recollection" type="checkbox" class="accent-brand-teal-500"/> Recollection required
        </label>
        <div v-if="recollection" class="grid grid-cols-2 gap-3 mb-3">
          <input v-model="targetDate" type="date" class="px-2 py-2 rounded border border-surface-200 text-sm"/>
          <input v-model="targetTime" type="time" class="px-2 py-2 rounded border border-surface-200 text-sm"/>
        </div>
        <label class="block text-xs text-surface-500 mb-1">Notes</label>
        <textarea v-model="notes" rows="3" class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-3" placeholder="Corrective action / clinician note"></textarea>
        <button class="btn-danger w-full" :disabled="submitting" @click="confirmReject">Confirm Rejection</button>
      </div>

      <div v-if="!isPending" class="card p-5 text-sm text-surface-500">
        This sample has already been {{ isAccepted ? 'accepted into the lab' : 'rejected' }}.
        Further changes can be made on the Sample Collection desk form.
      </div>
    </div>
  </div>
  <div v-else class="card p-12 text-center text-surface-400">Loading sample…</div>
</template>
