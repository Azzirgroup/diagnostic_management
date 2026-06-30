<template>
  <div class="step-content max-w-5xl mx-auto px-4">
    <SectionHeader
      :section-number="3"
      title="Sample Collection"
      description="Collect and process lab samples for this workflow"
      color="purple"
    />

    <!-- Notification -->
    <div v-if="notification.message" :class="[
      'rounded-lg border px-4 py-3 mb-4 flex items-center gap-2 text-sm',
      notification.type === 'error' ? 'bg-red-50 border-red-200 text-red-700' :
      notification.type === 'success' ? 'bg-green-50 border-green-200 text-green-700' :
      'bg-blue-50 border-blue-200 text-blue-700'
    ]">
      <FeatherIcon :name="notification.type === 'error' ? 'alert-circle' : 'check-circle'" class="w-4 h-4 flex-shrink-0" />
      <span class="flex-1">{{ notification.message }}</span>
      <button @click="notification = { type: '', message: '' }" class="ml-auto p-0.5 hover:bg-black/5 rounded">
        <FeatherIcon name="x" class="w-3.5 h-3.5" />
      </button>
    </div>

    <!-- Loading -->
    <div v-if="samplesLoading" class="bg-white rounded-lg border border-gray-200 p-12 text-center">
      <div class="animate-spin rounded-full h-8 w-8 border-2 border-gray-200 border-t-purple-600 mx-auto mb-3"></div>
      <p class="text-sm text-gray-500">Loading lab samples...</p>
    </div>

    <!-- No Samples -->
    <div v-else-if="samples.length === 0" class="bg-white rounded-lg border border-gray-200 p-8 text-center">
      <FeatherIcon name="alert-circle" class="w-10 h-10 text-amber-400 mx-auto mb-3" />
      <h3 class="text-base font-semibold text-gray-900 mb-1">No Lab Samples Found</h3>
      <p class="text-sm text-gray-500 mb-4">Samples are created when the Sales Invoice is submitted.</p>
    </div>

    <!-- Samples Loaded -->
    <template v-else>
      <!-- Summary + sample selector (master) -->
      <div class="bg-white rounded-lg border border-gray-200 p-4 mb-4">
        <div class="flex items-center justify-between flex-wrap gap-3 mb-3">
          <p class="text-sm text-gray-600"><strong class="text-gray-900">{{ testedCount }}</strong> of {{ samples.length }} sample(s) complete</p>
          <div class="flex items-center gap-2">
            <button v-if="toCollectCount > 0" @click="handleCollect" :disabled="collecting"
              class="px-3 py-1.5 rounded-lg text-sm font-medium bg-brand-navy-700 text-white hover:opacity-90 disabled:opacity-50">
              {{ collecting ? 'Collecting…' : `Collect ${toCollectCount} Pending` }}
            </button>
            <!-- Continue allowed as soon as AT LEAST ONE sample is ready.
                 The "every sample complete" rule kicks in at Finish Workflow
                 on the Results step — letting tests with shorter TATs flow
                 into reporting without waiting for the slowest sample. -->
            <button v-if="anyTested" @click="emit('continue', { skipped: true })"
              class="px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 bg-green-600 text-white hover:bg-green-700"
              :title="allTested ? 'All samples ready — continue to Results' :
                      'At least one sample is ready. You can start entering results; the report Finish step will wait for the remaining samples.'">
              Continue to Results
              <FeatherIcon name="arrow-right" class="w-4 h-4" />
            </button>
            <span v-else class="text-xs text-amber-600 flex items-center gap-1.5">
              <FeatherIcon name="alert-circle" class="w-3.5 h-3.5" />
              Mark at least one sample Complete or Stored to continue
            </span>
          </div>
        </div>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
          <button
            v-for="(sample, idx) in samples"
            :key="sample.name"
            @click="selectedIdx = idx"
            :class="['text-left p-3 rounded-lg border transition-colors',
              idx === selectedIdx ? 'border-brand-navy-700 ring-1 ring-brand-navy-700 bg-brand-navy-700/5' : 'border-gray-200 hover:border-gray-300']"
          >
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-sm text-gray-900 truncate">{{ sample.sample_id || sample.name }}</span>
              <FeatherIcon v-if="terminalStatuses.includes(sample.status)" name="check-circle" class="w-4 h-4 text-green-600 shrink-0" />
            </div>
            <div class="text-xs text-gray-500 truncate">{{ sample.sample_type || 'Sample' }}</div>
            <div class="flex items-center gap-1.5 mt-1.5">
              <span :class="statusBadgeClass(sample.status)">{{ sample.status }}</span>
              <span v-if="sample.is_urgent" class="text-[10px] font-semibold text-red-600">URGENT</span>
            </div>
          </button>
        </div>
      </div>

      <!-- Selected sample detail -->
      <div class="space-y-4 mb-6">
        <div
          v-for="(sample, idx) in samples"
          :key="sample.name"
          v-show="idx === selectedIdx"
          class="bg-white rounded-lg border border-gray-200 overflow-hidden"
        >
          <!-- Sample ID Header -->
          <div class="px-5 py-3 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <FeatherIcon name="droplet" class="w-5 h-5 text-purple-600" />
              <div>
                <span class="font-semibold text-gray-900">{{ sample.sample_id || sample.name }}</span>
                <span class="text-sm text-gray-500 ml-2">{{ sample.sample_type || '' }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <span v-if="sample.is_urgent" class="px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">URGENT</span>
              <span :class="statusBadgeClass(sample.status)">{{ sample.status }}</span>
            </div>
          </div>

          <!-- Status Stepper -->
          <div class="px-5 py-4 border-b border-gray-100">
            <div class="flex items-center justify-between">
              <div
                v-for="(step, stepIdx) in statusSteps"
                :key="step.value"
                class="flex items-center"
                :class="stepIdx < statusSteps.length - 1 ? 'flex-1' : ''"
              >
                <div class="flex flex-col items-center">
                  <div :class="[
                    'w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium border-2 transition-colors',
                    getStepState(sample.status, step.value) === 'completed'
                      ? 'bg-green-500 border-green-500 text-white'
                      : getStepState(sample.status, step.value) === 'current'
                        ? 'bg-amber-500 border-amber-500 text-white'
                        : 'bg-white border-gray-300 text-gray-400'
                  ]">
                    <FeatherIcon
                      v-if="getStepState(sample.status, step.value) === 'completed'"
                      name="check"
                      class="w-4 h-4"
                    />
                    <FeatherIcon
                      v-else-if="getStepState(sample.status, step.value) === 'current'"
                      name="clock"
                      class="w-4 h-4"
                    />
                    <span v-else>{{ stepIdx + 1 }}</span>
                  </div>
                  <span :class="[
                    'text-[10px] mt-1 text-center whitespace-nowrap',
                    getStepState(sample.status, step.value) === 'completed' ? 'text-green-700 font-medium'
                      : getStepState(sample.status, step.value) === 'current' ? 'text-amber-700 font-medium'
                      : 'text-gray-400'
                  ]">{{ step.label }}</span>
                </div>
                <!-- Connector line -->
                <div
                  v-if="stepIdx < statusSteps.length - 1"
                  :class="[
                    'flex-1 h-0.5 mx-1 mt-[-16px]',
                    getStepState(sample.status, step.value) === 'completed' ? 'bg-green-400' : 'bg-gray-200'
                  ]"
                ></div>
              </div>
            </div>
          </div>

          <div class="p-5">
            <!-- Update Status (for any non-terminal status) -->
            <div v-if="!['Disposed', 'Rejected'].includes(sample.status)" class="mb-4">
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-semibold text-gray-900">Advance Status</h4>
                <label class="flex items-center gap-2 cursor-pointer select-none">
                  <span class="text-xs font-medium" :class="formData[idx].is_urgent ? 'text-red-600' : 'text-gray-500'">Urgent</span>
                  <button type="button" @click="toggleUrgent(idx)"
                    :class="['relative inline-flex h-5 w-9 items-center rounded-full transition-colors', formData[idx].is_urgent ? 'bg-red-500' : 'bg-gray-300']">
                    <span :class="['inline-block h-4 w-4 transform rounded-full bg-white transition-transform', formData[idx].is_urgent ? 'translate-x-4' : 'translate-x-1']"></span>
                  </button>
                </label>
              </div>

              <div class="flex flex-wrap items-center gap-2">
                <!-- Primary: one-click next step -->
                <button
                  v-if="nextStepFor(sample.status)"
                  @click="quickUpdate(idx, nextStepFor(sample.status))"
                  :disabled="statusUpdating[idx]"
                  class="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold bg-brand-navy-700 text-white hover:opacity-90 disabled:opacity-50 transition-colors"
                >
                  <FeatherIcon v-if="statusUpdating[idx]" name="loader" class="w-4 h-4 animate-spin" />
                  <FeatherIcon v-else name="arrow-right" class="w-4 h-4" />
                  {{ statusUpdating[idx] ? 'Updating…' : `Mark as ${labelFor(nextStepFor(sample.status))}` }}
                </button>

                <!-- Fast track -->
                <button
                  v-if="['To Be Collected', 'Collected', 'In Transit', 'Received', 'In Processing'].includes(sample.status) && fastTrackPending !== sample.name"
                  @click="fastTrackPending = sample.name"
                  :disabled="statusUpdating[idx]"
                  class="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 disabled:opacity-50"
                >
                  <FeatherIcon name="zap" class="w-3.5 h-3.5" /> Fast-track to Complete
                </button>

                <!-- Jump to a later step (skip ahead) -->
                <select
                  v-if="laterSteps(sample.status).length"
                  :value="''"
                  @change="(e) => e.target.value && quickUpdate(idx, e.target.value)"
                  :disabled="statusUpdating[idx]"
                  class="px-2.5 py-2 border border-gray-300 rounded-lg text-sm text-gray-600 bg-white focus:ring-1 focus:ring-brand-navy-700"
                >
                  <option value="">Skip to…</option>
                  <option v-for="opt in laterSteps(sample.status)" :key="opt" :value="opt">{{ labelFor(opt) }}</option>
                </select>

                <!-- Reject (off-ramp) -->
                <button
                  @click="quickUpdate(idx, 'Rejected')"
                  :disabled="statusUpdating[idx]"
                  class="ml-auto text-sm text-red-600 hover:underline"
                >Reject sample</button>
              </div>

              <!-- Fast track confirm -->
              <div v-if="fastTrackPending === sample.name" class="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <FeatherIcon name="alert-triangle" class="w-4 h-4 text-amber-600" />
                  <span class="text-sm text-amber-800">Fast-track <strong>{{ sample.sample_id || sample.name }}</strong> to Complete? This skips the intermediate steps.</span>
                </div>
                <div class="flex gap-2 flex-shrink-0">
                  <button @click="fastTrackPending = null" class="px-3 py-1 text-sm text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50">Cancel</button>
                  <button @click="confirmFastTrack(idx)" class="px-3 py-1 text-sm text-white bg-green-600 rounded-lg hover:bg-green-700">Confirm</button>
                </div>
              </div>
            </div>

            <!-- Department Barcodes -->
            <div class="mb-4">
              <div class="flex items-center justify-between mb-2">
                <h4 class="text-sm font-semibold text-gray-900">Department Barcodes ({{ (sample.department_barcodes || []).length }})</h4>
                <div class="flex items-center gap-2">
                  <button @click="printAllDeptBarcodes(sample)"
                    v-if="sample.department_barcodes && sample.department_barcodes.length"
                    class="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-gray-600 bg-gray-100 rounded-lg hover:bg-gray-200">
                    <FeatherIcon name="printer" class="w-3 h-3" />
                    Print All Barcodes
                  </button>
                  <button @click="toggleAddDept(idx)"
                    class="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-blue-600 bg-blue-50 rounded-lg hover:bg-blue-100">
                    <FeatherIcon name="plus" class="w-3 h-3" />
                    Add Department
                  </button>
                </div>
              </div>

              <!-- Add Department Barcode Form -->
              <div v-if="showAddDept[idx]" class="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <div v-if="deptErrors[idx]" class="mb-2 text-sm text-red-600">{{ deptErrors[idx] }}</div>
                <div class="flex gap-2 items-end">
                  <div class="flex-1">
                    <label class="text-xs text-gray-600 font-medium">Department</label>
                    <select v-model="newDept[idx]"
                      class="w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:ring-1 focus:ring-blue-500 focus:border-blue-500 bg-white">
                      <option value="">Select department</option>
                      <option v-for="d in getAvailableDepts(sample)" :key="d" :value="d">{{ d }}</option>
                    </select>
                  </div>
                  <button @click="generateDeptBarcode(idx, sample)"
                    :disabled="!newDept[idx] || generatingDept[idx]"
                    class="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50 flex items-center gap-1.5">
                    <FeatherIcon v-if="generatingDept[idx]" name="loader" class="w-3.5 h-3.5 animate-spin" />
                    <FeatherIcon v-else name="zap" class="w-3.5 h-3.5" />
                    {{ generatingDept[idx] ? 'Generating...' : 'Generate' }}
                  </button>
                  <button @click="showAddDept[idx] = false; deptErrors[idx] = ''"
                    class="px-3 py-1.5 border border-gray-300 rounded text-sm hover:bg-gray-50">Cancel</button>
                </div>
              </div>

              <div v-if="sample.department_barcodes && sample.department_barcodes.length" class="border border-gray-200 rounded overflow-hidden">
                <table class="w-full text-sm">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Department</th>
                      <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Barcode ID</th>
                      <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Generated</th>
                      <th class="text-center px-3 py-2 text-xs font-medium text-gray-500 uppercase">Print</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="db in sample.department_barcodes" :key="db.barcode_id">
                      <td class="px-3 py-2 text-gray-900">{{ db.department_name || db.department }}</td>
                      <td class="px-3 py-2">
                        <div class="flex items-center gap-2">
                          <BarcodeRenderer
                            v-if="db.barcode_id"
                            :value="db.barcode_id"
                            :height="28"
                            :width="1"
                            :display-value="true"
                            :font-size="8"
                            :margin="1"
                            compact
                          />
                          <span v-else class="text-gray-400 text-xs">-</span>
                        </div>
                      </td>
                      <td class="px-3 py-2 text-gray-500 text-xs">{{ db.generated_datetime ? formatDatetime(db.generated_datetime) : '-' }}</td>
                      <td class="px-3 py-2 text-center">
                        <button v-if="db.barcode_id" @click="printDeptBarcode(db, sample)"
                          class="p-1 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded">
                          <FeatherIcon name="printer" class="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="text-sm text-gray-400 italic">No department barcodes generated yet.</div>
            </div>

            <!-- Lab Tests linked to this sample -->
            <div v-if="sample.lab_tests && sample.lab_tests.length" class="mb-4">
              <h4 class="text-sm font-semibold text-gray-900 mb-2">Lab Tests ({{ sample.lab_tests.length }})</h4>
              <div class="border border-gray-200 rounded overflow-hidden">
                <table class="w-full text-sm">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Test</th>
                      <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Department</th>
                      <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Status</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-gray-100">
                    <tr v-for="lt in sample.lab_tests" :key="lt.lab_test">
                      <td class="px-3 py-2">
                        <span class="font-medium text-gray-900">{{ lt.lab_test_name || lt.lab_test }}</span>
                        <span v-if="lt.template" class="text-xs text-gray-400 ml-1">({{ lt.template }})</span>
                      </td>
                      <td class="px-3 py-2 text-gray-600">{{ lt.department || '-' }}</td>
                      <td class="px-3 py-2">
                        <span :class="[
                          'px-2 py-0.5 rounded text-xs font-medium',
                          lt.status === 'Completed' || lt.status === 'Approved' ? 'bg-green-100 text-green-700' :
                          lt.status === 'Processing' ? 'bg-purple-100 text-purple-700' :
                          lt.status === 'Rejected' || lt.status === 'Cancelled' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        ]">{{ lt.status || 'Pending' }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Timeline: Collected / Received / Processed -->
            <div class="grid grid-cols-3 gap-3">
              <div class="bg-gray-50 rounded-lg px-3 py-2">
                <div class="text-[10px] uppercase tracking-wide text-gray-400 font-medium">Collected</div>
                <div class="text-sm text-gray-900 mt-0.5">
                  {{ sample.collection_datetime ? formatDatetime(sample.collection_datetime) : 'Pending' }}
                </div>
              </div>
              <div class="bg-gray-50 rounded-lg px-3 py-2">
                <div class="text-[10px] uppercase tracking-wide text-gray-400 font-medium">Received</div>
                <div class="text-sm text-gray-900 mt-0.5">
                  {{ sample.received_datetime ? formatDatetime(sample.received_datetime) : 'Pending' }}
                </div>
              </div>
              <div class="bg-gray-50 rounded-lg px-3 py-2">
                <div class="text-[10px] uppercase tracking-wide text-gray-400 font-medium">Processed</div>
                <div class="text-sm text-gray-900 mt-0.5">
                  {{ sample.processed_datetime ? formatDatetime(sample.processed_datetime) : 'Pending' }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

    </template>

    <!-- Overlay -->
    <div v-if="collecting" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg px-6 py-4 flex items-center gap-3 shadow-lg">
        <div class="animate-spin rounded-full h-5 w-5 border-2 border-gray-200 border-t-brand-navy-700"></div>
        <span class="text-sm text-gray-700">Collecting samples...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { call } from '@/api/client'
import FeatherIcon from '@/components/ui/FeatherIcon.vue'
import JsBarcode from 'jsbarcode'
import SectionHeader from '@/components/ui/SectionHeader.vue'
import BarcodeRenderer from '@/components/common/BarcodeRenderer.vue'

const props = defineProps({
  session: { type: Object, required: true },
  collectionData: { type: Object, default: null },
  billingData: { type: Object, default: null }
})

const emit = defineEmits(['continue'])

const samples = ref([])
const formData = ref([])
const selectedIdx = ref(0)
const samplesLoading = ref(false)
const collecting = ref(false)
const statusUpdating = ref({})
const notification = ref({ type: '', message: '' })
const fastTrackPending = ref(null)

// Department barcode state
const allDepartments = ref([])
const showAddDept = ref({})
const newDept = ref({})
const generatingDept = ref({})
const deptErrors = ref({})

// Status pipeline steps
const statusSteps = [
  { value: 'To Be Collected', label: 'To Collect' },
  { value: 'Collected', label: 'Collected' },
  { value: 'In Transit', label: 'In Transit' },
  { value: 'Received', label: 'Received' },
  { value: 'In Processing', label: 'Processing' },
  { value: 'Tested', label: 'Complete' },
  { value: 'Stored', label: 'Stored' }
]

const statusOrder = statusSteps.map(s => s.value)

const getStepState = (currentStatus, stepValue) => {
  const currentIdx = statusOrder.indexOf(currentStatus)
  const stepIdx = statusOrder.indexOf(stepValue)
  if (currentIdx < 0) return 'pending'
  if (stepIdx < currentIdx) return 'completed'
  if (stepIdx === currentIdx) return 'current'
  return 'pending'
}

const getNextStatuses = (currentStatus) => {
  const idx = statusOrder.indexOf(currentStatus)
  if (idx < 0) return statusOrder
  const next = statusOrder.slice(idx + 1)
  if (!next.includes('Rejected')) next.push('Rejected')
  return next
}

// The immediate next step in the pipeline (skips the Rejected off-ramp).
const nextStepFor = (currentStatus) => {
  const idx = statusOrder.indexOf(currentStatus)
  return idx >= 0 && idx < statusOrder.length - 1 ? statusOrder[idx + 1] : null
}
// Friendly label for a status value (e.g. "Tested" -> "Complete").
const labelFor = (value) => (statusSteps.find(s => s.value === value)?.label) || value
// Steps you can jump to beyond the immediate next one.
const laterSteps = (currentStatus) => {
  const idx = statusOrder.indexOf(currentStatus)
  return idx >= 0 ? statusOrder.slice(idx + 2) : []
}
// One-click status change (sets the form value then runs the existing handler).
const quickUpdate = async (idx, status) => {
  formData.value[idx].new_status = status
  await handleStatusUpdate(idx)
}

const statusBadgeClass = (status) => {
  const map = {
    'To Be Collected': 'bg-amber-100 text-amber-800',
    'Collected': 'bg-green-100 text-green-800',
    'In Transit': 'bg-blue-100 text-blue-800',
    'Received': 'bg-indigo-100 text-indigo-800',
    'In Processing': 'bg-purple-100 text-purple-800',
    'Tested': 'bg-teal-100 text-teal-800',
    'Stored': 'bg-gray-100 text-gray-800',
    'Rejected': 'bg-red-100 text-red-800',
    'Disposed': 'bg-gray-100 text-gray-600'
  }
  return 'px-2 py-0.5 rounded text-xs font-medium ' + (map[status] || 'bg-gray-100 text-gray-600')
}

const toCollectCount = computed(() =>
  samples.value.filter(s => s.status === 'To Be Collected').length
)
const terminalStatuses = ['Tested', 'Stored', 'Disposed']
const testedCount = computed(() =>
  samples.value.filter(s => terminalStatuses.includes(s.status)).length
)
const allTested = computed(() =>
  samples.value.length > 0 && samples.value.every(s => terminalStatuses.includes(s.status))
)
// Partial-release gate: as soon as ANY sample is at a terminal status the
// tech can move to Results and start entering values. The "all samples
// done" check is then enforced at the Lab Report Finish step, not here.
const anyTested = computed(() =>
  samples.value.length > 0 && samples.value.some(s => terminalStatuses.includes(s.status))
)

const formatDatetime = (dt) => {
  if (!dt) return ''
  return new Date(dt).toLocaleString('en-KE', { dateStyle: 'medium', timeStyle: 'short' })
}

const loadSamples = async () => {
  if (!props.session?.name) return
  samplesLoading.value = true
  try {
    const result = await call('diagnostic_management.api.collection_workflow.get_session_lab_samples', {
      session_id: props.session.name
    })
    samples.value = result?.samples || []
    formData.value = samples.value.map(s => ({
      sample_name: s.name,
      new_status: '',
      is_urgent: !!s.is_urgent
    }))
    if (selectedIdx.value >= samples.value.length) selectedIdx.value = 0
  } catch (err) {
    console.error('Failed to load samples:', err)
    notification.value = { type: 'error', message: 'Failed to load lab samples.' }
  } finally {
    samplesLoading.value = false
  }
}

// Toggle + persist the urgent flag immediately (no status change needed)
const toggleUrgent = async (idx) => {
  const sample = samples.value[idx]
  const next = !formData.value[idx].is_urgent
  formData.value[idx].is_urgent = next
  try {
    await call('diagnostic_management.api.collection_workflow.set_sample_urgent', {
      sample_name: sample.name,
      is_urgent: next ? 1 : 0
    })
    samples.value[idx].is_urgent = next ? 1 : 0
    notification.value = { type: 'success', message: `${sample.sample_id || sample.name} ${next ? 'marked urgent' : 'urgent cleared'}` }
  } catch (err) {
    formData.value[idx].is_urgent = !next // revert on failure
    notification.value = { type: 'error', message: 'Failed to update urgent flag' }
  }
}

// Update single sample status
const handleStatusUpdate = async (idx) => {
  const sample = samples.value[idx]
  const form = formData.value[idx]
  if (!form.new_status) return

  statusUpdating.value = { ...statusUpdating.value, [idx]: true }
  try {
    const result = await call('diagnostic_management.api.collection_workflow.update_lab_sample_status', {
      sample_name: sample.name,
      new_status: form.new_status,
      is_urgent: form.is_urgent ? 1 : 0
    })
    if (result?.success) {
      samples.value[idx].status = result.new_status
      if (result.collection_datetime) samples.value[idx].collection_datetime = result.collection_datetime
      if (result.received_datetime) samples.value[idx].received_datetime = result.received_datetime
      if (result.processed_datetime) samples.value[idx].processed_datetime = result.processed_datetime
      samples.value[idx].is_urgent = form.is_urgent ? 1 : 0
      form.new_status = ''
      notification.value = { type: 'success', message: `${sample.sample_id || sample.name} updated to ${result.new_status}` }
    }
  } catch (err) {
    console.error('Status update failed:', err)
    let msg = 'Failed to update status'
    if (err.messages?.length) msg = err.messages.map(m => typeof m === 'object' ? m.message : m).join('. ')
    else if (err.message) msg = err.message
    notification.value = { type: 'error', message: msg }
  } finally {
    statusUpdating.value = { ...statusUpdating.value, [idx]: false }
  }
}

// Fast Track to Tested
const confirmFastTrack = async (idx) => {
  const sample = samples.value[idx]
  fastTrackPending.value = null

  statusUpdating.value = { ...statusUpdating.value, [idx]: true }
  try {
    const result = await call('diagnostic_management.api.collection_workflow.update_sample_processing_status', {
      session_id: props.session.name,
      sample_name: sample.name,
      status: 'Tested',
      data: { fast_track: true }
    })

    samples.value[idx].status = 'Tested'
    if (result.received_datetime) samples.value[idx].received_datetime = result.received_datetime
    if (result.processed_datetime) samples.value[idx].processed_datetime = result.processed_datetime
    notification.value = { type: 'success', message: `${sample.sample_id || sample.name} fast tracked to Tested` }

    // Reload to get updated data
    setTimeout(() => loadSamples(), 1500)
  } catch (err) {
    console.error('Fast track failed:', err)
    let msg = 'Failed to fast track sample'
    if (err.messages?.length) msg = err.messages.map(m => typeof m === 'object' ? m.message : m).join('. ')
    else if (err.message) msg = err.message
    notification.value = { type: 'error', message: msg }
  } finally {
    statusUpdating.value = { ...statusUpdating.value, [idx]: false }
  }
}

// Collect all "To Be Collected" samples at once
const handleCollect = async () => {
  const samplesData = samples.value
    .map((s, idx) => {
      if (s.status !== 'To Be Collected') return null
      return { sample_name: s.name, is_urgent: formData.value[idx].is_urgent ? 1 : 0 }
    })
    .filter(Boolean)

  if (samplesData.length === 0) {
    return
  }

  collecting.value = true
  try {
    const result = await call('diagnostic_management.api.collection_workflow.collect_lab_samples', {
      session_id: props.session.name,
      samples_data: samplesData
    })
    if (result?.success) {
      notification.value = { type: 'success', message: result.message || 'Samples collected' }
      await loadSamples()
    }
  } catch (err) {
    console.error('Failed to collect samples:', err)
    let msg = 'Failed to collect samples'
    if (err.messages?.length) msg = err.messages.map(m => typeof m === 'object' ? m.message : m).join('. ')
    else if (err.message) msg = err.message
    notification.value = { type: 'error', message: msg }
  } finally {
    collecting.value = false
  }
}

// Department barcode helpers
const toggleAddDept = (idx) => {
  showAddDept.value = { ...showAddDept.value, [idx]: !showAddDept.value[idx] }
  if (!newDept.value[idx]) newDept.value = { ...newDept.value, [idx]: '' }
  deptErrors.value = { ...deptErrors.value, [idx]: '' }
}

const getAvailableDepts = (sample) => {
  const existing = new Set((sample.department_barcodes || []).map(b => b.department))
  return allDepartments.value.filter(d => !existing.has(d))
}

const generateDeptBarcode = async (idx, sample) => {
  if (!newDept.value[idx] || !sample.name) return
  deptErrors.value = { ...deptErrors.value, [idx]: '' }
  generatingDept.value = { ...generatingDept.value, [idx]: true }
  try {
    await call('diagnostic_management.api.collection_workflow.add_department_barcode', {
      sample_name: sample.name,
      department: newDept.value[idx]
    })
    await loadSamples()
    newDept.value = { ...newDept.value, [idx]: '' }
    showAddDept.value = { ...showAddDept.value, [idx]: false }
    notification.value = { type: 'success', message: 'Department barcode generated successfully' }
  } catch (err) {
    let msg = 'Failed to generate barcode'
    if (err.messages?.length) msg = err.messages.map(m => typeof m === 'object' ? m.message : m).join('. ')
    else if (err.message) msg = err.message
    deptErrors.value = { ...deptErrors.value, [idx]: msg }
  } finally {
    generatingDept.value = { ...generatingDept.value, [idx]: false }
  }
}

// Generate barcode SVG string client-side
const makeBarcodeSvg = (value) => {
  if (!value) return ''
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  try {
    JsBarcode(svg, value, {
      format: 'CODE128', width: 1, height: 30,
      displayValue: false, margin: 0
    })
    return svg.outerHTML
  } catch (e) { return '' }
}

const formatDatetimeLabel = (dt) => {
  if (!dt) return ''
  const d = new Date(dt)
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const yyyy = d.getFullYear()
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${dd}/${mm}/${yyyy} ${hh}:${mi}:${ss}`
}

const buildPatientLine = (patientName, age, sex) => {
  let line = (patientName || '').toUpperCase()
  if (age) line += ', ' + age
  if (sex) line += '  ' + sex.charAt(0).toUpperCase()
  return line
}

const calculateAge = (dob) => {
  if (!dob) return ''
  const birth = new Date(dob)
  const today = new Date()
  let years = today.getFullYear() - birth.getFullYear()
  let months = today.getMonth() - birth.getMonth()
  if (months < 0 || (months === 0 && today.getDate() < birth.getDate())) { years--; months += 12 }
  if (today.getDate() < birth.getDate()) months--
  if (years > 0) return years + ' years'
  if (months > 0) return months + ' months'
  return Math.floor((today - birth) / (1000 * 60 * 60 * 24)) + ' days'
}

// Print department barcodes
const printDeptBarcode = async (bc, sample) => {
  const barcodeSvg = makeBarcodeSvg(bc.barcode_id)
  if (!barcodeSvg) {
    notification.value = { type: 'error', message: 'No barcode to print' }
    return
  }

  let patientName = sample.patient_name || ''
  let age = ''
  let sex = ''
  let patientId = sample.patient || ''
  try {
    const p = await call('frappe.client.get_value', {
      doctype: 'Patient', filters: { name: sample.patient },
      fieldname: ['patient_name', 'dob', 'sex']
    })
    if (p) {
      patientName = p.patient_name || patientName
      age = calculateAge(p.dob)
      sex = p.sex || ''
    }
  } catch (e) { /* use what we have */ }

  const collectionDt = formatDatetimeLabel(sample.collection_datetime || sample.creation)
  const sexChar = sex ? sex.charAt(0).toUpperCase() : ''
  const nameAgeSexLine = [(patientName || '').toUpperCase(), age, sexChar].filter(Boolean).join('  ')
  const deptName = (bc.department_name || bc.department || '').toUpperCase()

  const printContent = `
    <div class="label">
      <div class="label-line">${patientId}</div>
      <div class="label-line">${nameAgeSexLine}</div>
      <div class="barcode-svg">${barcodeSvg}</div>
      <div class="label-line center">${bc.barcode_id}</div>
      <div class="label-line">${collectionDt}</div>
      <div class="label-line">${deptName}</div>
    </div>`

  const win = window.open('', '_blank')
  if (!win) return
  win.document.write(`<html><head><title></title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Courier New', Courier, monospace; }
.label { width: 50mm; padding: 0.5mm 1.5mm; overflow: hidden; }
.label-line { font-weight: bold; font-size: 10px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.label-line.center { text-align: center; font-size: 8px; }
.barcode-svg { text-align: center; overflow: hidden; line-height: 0; margin: 0; }
.barcode-svg svg { width: 100%; height: 28px; }
@media print {
  @page { size: 50mm 25mm; margin: 0; }
  body { margin: 0; padding: 0; }
}
</style></head><body>${printContent}
<script>setTimeout(function() { window.print(); }, 500);<\/script>
</body></html>`)
  win.document.close()
}

const printAllDeptBarcodes = async (sample) => {
  const barcodes = sample.department_barcodes || []
  if (!barcodes.length) {
    notification.value = { type: 'error', message: 'No department barcodes to print' }
    return
  }

  let patientName = sample.patient_name || ''
  let age = ''
  let sex = ''
  let patientId = sample.patient || ''
  try {
    const p = await call('frappe.client.get_value', {
      doctype: 'Patient', filters: { name: sample.patient },
      fieldname: ['patient_name', 'dob', 'sex']
    })
    if (p) {
      patientName = p.patient_name || patientName
      age = calculateAge(p.dob)
      sex = p.sex || ''
    }
  } catch (e) { /* use what we have */ }

  const collectionDt = formatDatetimeLabel(sample.collection_datetime || sample.creation)
  const sexChar = sex ? sex.charAt(0).toUpperCase() : ''
  const nameAgeSexLine = [(patientName || '').toUpperCase(), age, sexChar].filter(Boolean).join('  ')

  const printContent = barcodes.map(bc => {
    const barcodeSvg = makeBarcodeSvg(bc.barcode_id)
    if (!barcodeSvg) return ''
    const deptName = (bc.department_name || bc.department || '').toUpperCase()
    return `
      <div class="label">
        <div class="label-line">${patientId}</div>
        <div class="label-line">${nameAgeSexLine}</div>
        <div class="barcode-svg">${barcodeSvg}</div>
        <div class="label-line center">${bc.barcode_id}</div>
        <div class="label-line">${collectionDt}</div>
        <div class="label-line">${deptName}</div>
      </div>`
  }).join('')

  const win = window.open('', '_blank')
  if (!win) return
  win.document.write(`<html><head><title></title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Courier New', Courier, monospace; }
.label { width: 50mm; padding: 0.5mm 1.5mm; page-break-after: always; overflow: hidden; }
.label:last-child { page-break-after: auto; }
.label-line { font-weight: bold; font-size: 10px; line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.label-line.center { text-align: center; font-size: 8px; }
.barcode-svg { text-align: center; overflow: hidden; line-height: 0; margin: 0; }
.barcode-svg svg { width: 100%; height: 28px; }
@media print {
  @page { size: 50mm 25mm; margin: 0; }
  body { margin: 0; padding: 0; }
  .label { page-break-after: always; }
  .label:last-child { page-break-after: auto; }
}
</style></head><body>${printContent}
<script>setTimeout(function() { window.print(); }, 500);<\/script>
</body></html>`)
  win.document.close()
}

const loadDepartments = async () => {
  try {
    allDepartments.value = await call('diagnostic_management.api.collection_workflow.get_medical_departments') || []
  } catch (err) { console.error('Failed to load departments:', err) }
}

onMounted(() => { loadDepartments() })

watch(() => props.session?.name, () => loadSamples(), { immediate: true })
</script>

<style scoped>
.step-content {
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
