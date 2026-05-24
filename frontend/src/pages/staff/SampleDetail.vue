<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import WorkflowStepper from '@/components/ui/WorkflowStepper.vue'
import { getDoc, call } from '@/api/client'
import { collectionApi } from '@/api/adms'

const route = useRoute()
const router = useRouter()
const sample = ref<Record<string, any> | null>(null)
const labTests = ref<Array<{ name: string; status?: string; template?: string }>>([])
const orderQuery = computed(() => (route.query.order as string | undefined) || sample.value?.service_request)

// Specimen lifecycle — mirrors the backend STATUS_ORDER (genetest-style).
const STATUS_ORDER = ['To Be Collected', 'Collected', 'In Transit', 'Received', 'In Processing', 'Tested', 'Stored']

const workflowStatus = computed<string>(() =>
  sample.value?.workflow_status || (sample.value?.collected_time ? 'Collected' : 'To Be Collected'),
)
const statusIdx = computed(() => STATUS_ORDER.indexOf(workflowStatus.value))
const isRejected = computed(() => workflowStatus.value === 'Rejected' || (sample.value?.received_condition && sample.value.received_condition !== 'Acceptable'))
const nextStatuses = computed(() => {
  if (isRejected.value) return []
  const rest = statusIdx.value >= 0 ? STATUS_ORDER.slice(statusIdx.value + 1) : STATUS_ORDER
  return [...rest, 'Rejected']
})
const canResult = computed(() => ['In Processing', 'Tested', 'Stored'].includes(workflowStatus.value))
const isCollected = computed(() => !!sample.value?.collected_time || statusIdx.value >= 1)

const newStatus = ref('')
const submitting = ref(false)

async function load() {
  try {
    const name = route.params.name as string
    sample.value = await getDoc('Sample Collection', name)
    labTests.value = await call<Array<{ name: string; status?: string; template?: string }>>('frappe.client.get_list', {
      doctype: 'Lab Test', filters: { sample: name },
      fields: ['name', 'status', 'template'], limit_page_length: 50,
    }).catch(() => [])
  } catch {
    sample.value = null
  }
}
onMounted(load)

async function advance(status?: string) {
  const target = status || newStatus.value
  if (!sample.value || !target) return
  submitting.value = true
  try {
    await collectionApi.advanceStatus(sample.value.name, target)
    newStatus.value = ''
    await load()
  } finally { submitting.value = false }
}

function openCollectionForm() {
  router.push(`/lab/sample/${route.params.name}/collect${orderQuery.value ? `?order=${orderQuery.value}` : ''}`)
}
function goResults() {
  router.push(orderQuery.value ? `/orders/${orderQuery.value}` : '/lab/verification')
}

function printDoc(format: string) {
  if (!sample.value) return
  const params = new URLSearchParams({ doctype: 'Sample Collection', name: sample.value.name, format, no_letterhead: '0' })
  window.open(`/printview?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Sample · ${sample?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <WorkflowStepper :order="orderQuery" :sample="(route.params.name as string)" current="store" />

  <div v-if="sample" class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h3 class="font-semibold text-lg">{{ sample.name }}</h3>
            <div class="text-sm text-surface-500 mt-1">{{ sample.patient_name }} · MRN {{ sample.patient }}</div>
          </div>
          <StatusPill :status="isRejected ? 'Rejected' : workflowStatus" />
        </div>
      </div>

      <!-- Specimen lifecycle stepper -->
      <div class="card p-5">
        <h3 class="font-semibold mb-4">Specimen Status</h3>
        <div class="flex items-start flex-wrap gap-y-3">
          <template v-for="(s, i) in STATUS_ORDER" :key="s">
            <div class="flex flex-col items-center text-center" style="min-width: 64px;">
              <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2"
                :class="i < statusIdx ? 'bg-brand-teal-500 text-white border-brand-teal-500'
                      : i === statusIdx ? 'bg-brand-teal-100 text-brand-teal-700 border-brand-teal-500'
                      : 'bg-surface-100 text-surface-400 border-surface-300'">
                <span v-if="i < statusIdx">✓</span><span v-else>{{ i + 1 }}</span>
              </span>
              <span class="text-[10px] mt-1 leading-tight" :class="i <= statusIdx ? 'text-surface-700 font-medium' : 'text-surface-400'">{{ s }}</span>
            </div>
            <div v-if="i < STATUS_ORDER.length - 1" class="h-px flex-1 mt-3.5 min-w-[8px]" :class="i < statusIdx ? 'bg-brand-teal-400' : 'bg-surface-200'"></div>
          </template>
        </div>
        <p v-if="isRejected" class="text-sm text-status-danger mt-3">This sample was rejected.</p>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-4">Patient Details</h3>
        <dl class="grid grid-cols-2 gap-y-3 text-sm">
          <dt class="text-surface-500">Series</dt><dd>{{ sample.naming_series || '—' }}</dd>
          <dt class="text-surface-500">Patient</dt><dd>{{ sample.patient_name || '—' }} <span class="text-surface-400">({{ sample.patient }})</span></dd>
          <dt class="text-surface-500">Age</dt><dd>{{ sample.patient_age || '—' }}</dd>
          <dt class="text-surface-500">Gender</dt><dd>{{ sample.patient_sex || '—' }}</dd>
          <dt class="text-surface-500">Referring Practitioner</dt><dd>{{ sample.referring_practitioner || '—' }}</dd>
          <dt class="text-surface-500">Company</dt><dd>{{ sample.company || '—' }}</dd>
          <dt class="text-surface-500">Collection Point</dt><dd>{{ sample.collection_point || '—' }}</dd>
          <dt class="text-surface-500">Order (Service Request)</dt>
          <dd>
            <button v-if="sample.service_request" class="text-brand-teal-600 hover:underline" @click="router.push(`/orders/${sample.service_request}`)">{{ sample.service_request }}</button>
            <span v-else>—</span>
          </dd>
        </dl>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-4">Sample Details</h3>
        <dl class="grid grid-cols-2 gap-y-3 text-sm">
          <dt class="text-surface-500">Sample</dt><dd>{{ sample.sample || '—' }}</dd>
          <dt class="text-surface-500">UOM</dt><dd>{{ sample.sample_uom || '—' }}</dd>
          <dt class="text-surface-500">Quantity</dt><dd>{{ sample.sample_qty ?? '—' }}</dd>
          <dt class="text-surface-500">Barcode</dt><dd class="font-mono">{{ sample.barcode || '—' }}</dd>
          <dt class="text-surface-500">Container / Tube</dt><dd>{{ sample.container || '—' }}</dd>
          <dt class="text-surface-500">No. of prints</dt><dd>{{ sample.num_print ?? '—' }}</dd>
          <dt class="text-surface-500">Collected By</dt><dd>{{ sample.collected_by || '—' }}</dd>
          <dt class="text-surface-500">Collected On</dt><dd>{{ (sample.collected_time as string)?.split('.')[0] || '—' }}</dd>
        </dl>
      </div>

      <!-- Linked Lab Tests (auto-created from the order) -->
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Lab Tests ({{ labTests.length }})</h3>
        <table v-if="labTests.length" class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200"><th class="py-2">Test</th><th>Template</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="lt in labTests" :key="lt.name" class="border-b border-surface-100">
              <td class="py-2">{{ lt.name }}</td>
              <td>{{ lt.template || '—' }}</td>
              <td><StatusPill :status="lt.status || 'Draft'" /></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="text-sm text-surface-400 py-2">No lab tests linked yet.</div>
      </div>

      <div v-if="sample.sample_details || sample.rejection_reason_text" class="card p-5">
        <h3 class="font-semibold mb-3">Notes</h3>
        <div v-if="sample.sample_details" class="text-sm mb-2"><span class="text-surface-500">Collection: </span>{{ sample.sample_details }}</div>
        <div v-if="sample.rejection_reason_text" class="text-sm text-status-danger"><span class="text-surface-500">Rejection: </span>{{ sample.rejection_reason_text }}</div>
      </div>
    </div>

    <div class="space-y-4">
      <!-- Advance status -->
      <div v-if="!isRejected && workflowStatus !== 'Stored'" class="card p-5">
        <h3 class="font-semibold mb-3">Update Status</h3>
        <button v-if="nextStatuses[0] && nextStatuses[0] !== 'Rejected'" class="btn-primary w-full mb-3"
          :disabled="submitting" @click="advance(nextStatuses[0])">
          Move to {{ nextStatuses[0] }} →
        </button>
        <label class="block text-xs text-surface-500 mb-1">Or set status</label>
        <select v-model="newStatus" class="input mb-2">
          <option value="">Select…</option>
          <option v-for="s in nextStatuses" :key="s" :value="s">{{ s }}</option>
        </select>
        <button class="btn-ghost w-full" :disabled="!newStatus || submitting" @click="advance()">Update Status</button>
      </div>

      <div v-if="canResult" class="card p-5">
        <button class="btn-primary w-full" @click="goResults">Continue to Results →</button>
      </div>

      <!-- Print / actions -->
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Actions</h3>
        <button v-if="!isCollected" class="btn-secondary w-full mb-2" @click="openCollectionForm">Record Collection</button>
        <button v-else class="btn-ghost w-full mb-2" @click="openCollectionForm">Edit Collection Details</button>
        <button class="btn-ghost w-full mb-2" @click="printDoc('Specimen Label')">Print Specimen Label</button>
        <button class="btn-ghost w-full mb-2" @click="printDoc('Sample Collection Receipt')">Print Receipt</button>
      </div>
    </div>
  </div>
  <div v-else class="card p-12 text-center text-surface-400">Loading sample…</div>
</template>
