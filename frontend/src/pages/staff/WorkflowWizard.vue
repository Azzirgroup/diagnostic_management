<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Combobox from '@/components/ui/Combobox.vue'
import ResultsStep from '@/components/workflow/ResultsStep.vue'
import {
  patientsApi, workflowApi,
  type PatientLite, type WorkflowSession,
} from '@/api/adms'
import { frappeError } from '@/api/client'
// @ts-ignore — ported genetest component uses a JS <script setup>
import BillingStep from '@/components/workflow/BillingStep.vue'
// @ts-ignore — ported genetest component uses a JS <script setup>
import CollectionStep from '@/components/workflow/CollectionStep.vue'

// Single-page guided lab workflow (Patient → Order → Collection → Results),
// backed by a Lab Workflow Session so it's resumable. Ports the genetest
// WorkflowWizard onto the ADMS doctypes.
const route = useRoute()
const router = useRouter()

const session = ref<WorkflowSession | null>(null)
const step = ref(1)
const busy = ref(false)
const error = ref('')

const STEPS = [
  { n: 1, label: 'Patient', desc: 'Select or register' },
  { n: 2, label: 'Order', desc: 'Choose tests' },
  { n: 3, label: 'Collection', desc: 'Collect & store' },
  { n: 4, label: 'Results', desc: 'Reports' },
]

// ---- Step 1: patient ----
const selectedPatient = ref<PatientLite | null>(null)
const showNewPatient = ref(false)
// Mirror the full /patients/new form so a tech doesn't have to leave the
// workflow to capture everything they'd capture there.
const np = ref({
  first_name: '', last_name: '', sex: 'Female', dob: '',
  mobile: '', email: '', blood_group: '', uid: '', permanent_address: '',
})
const BLOOD_GROUPS = [
  'A Positive', 'A Negative', 'AB Positive', 'AB Negative',
  'B Positive', 'B Negative', 'O Positive', 'O Negative',
]
// True once Billing created at least one Service Request / Sales Invoice in
// this session, so going back to step 2 should show a read-only "already
// submitted" summary instead of opening BillingStep for another submission.
const orderAlreadySubmitted = computed(() => {
  if (!session.value) return false
  if (session.value.service_request) return true
  try {
    const draft = session.value.draft_data ? JSON.parse(session.value.draft_data) : null
    return !!(draft && (draft.invoice || (draft.orders && draft.orders.length)))
  } catch { return false }
})
const submittedSummary = computed(() => {
  if (!session.value?.draft_data) return null
  try {
    const d = JSON.parse(session.value.draft_data)
    return { invoice: d.invoice as string | undefined, orders: (d.orders as string[]) || [] }
  } catch { return null }
})
const patientKey = (p: PatientLite) => p.name
const patientLabel = (p: PatientLite) => p.patient_name || p.name
const patientSub = (p: PatientLite) => `${p.sex || '—'} · ${p.mobile || 'no phone'}`
async function loadPatients(q: string): Promise<PatientLite[]> {
  try { return await patientsApi.search(q, q ? 10 : 50) } catch { return [] }
}

// ---- Step 2: billing (ported genetest component) ----
// BillingStep creates the orders + invoice (+ payment) and links them to the
// session; we just advance to Collection when it emits `continue`.
async function onBillingContinue() {
  if (!session.value) return
  busy.value = true
  try {
    session.value = await workflowApi.save({ name: session.value.name, current_step: 3 })
    step.value = 3
  } finally { busy.value = false }
}

// ---- derived ----
async function reloadSession() {
  if (session.value?.name) session.value = await workflowApi.get(session.value.name)
}

onMounted(async () => {
  const id = route.params.session as string | undefined
  if (id && id !== 'new') {
    try {
      session.value = await workflowApi.get(id)
      step.value = Math.min(session.value.current_step || 1, 4)
      if (session.value.patient) {
        selectedPatient.value = { name: session.value.patient, patient_name: session.value.patient_name || session.value.patient }
      }
    } catch (e: any) { error.value = e?.message || 'Failed to load session' }
  }
})

async function gotoStep(n: number) {
  if (n <= (session.value?.current_step || 1)) step.value = n
}

// Step 1 → 2
async function pickPatient(p: PatientLite) {
  selectedPatient.value = p
  busy.value = true; error.value = ''
  try {
    if (!session.value) {
      session.value = await workflowApi.create(p.name)
      router.replace(`/workflow/${session.value.name}`)
    } else {
      session.value = await workflowApi.save({ name: session.value.name, patient: p.name, current_step: 2 })
    }
    step.value = 2
  } catch (e: any) { error.value = e?.message || 'Failed' } finally { busy.value = false }
}
async function createPatient() {
  if (!np.value.first_name.trim()) { error.value = 'First name required'; return }
  if (!np.value.sex) { error.value = 'Gender required'; return }
  busy.value = true; error.value = ''
  try {
    // Strip empty optional fields so we don't carry "" into the doc insert.
    const payload: Record<string, string> = {
      first_name: np.value.first_name.trim(),
      sex: np.value.sex,
    }
    for (const k of ['last_name','dob','mobile','email','blood_group','uid','permanent_address'] as const) {
      const v = (np.value[k] || '').trim()
      if (v) payload[k] = v
    }
    const r = await patientsApi.createBasic(payload as any)
    await pickPatient({ name: r.name, patient_name: r.patient_name })
    showNewPatient.value = false
  } catch (e: any) { error.value = frappeError(e, 'Failed to create patient') }
  finally { busy.value = false }
}

async function toResults() {
  if (!session.value) return
  session.value = await workflowApi.save({ name: session.value.name, current_step: 4 })
  step.value = 4
}

// Step 4
async function finish() {
  if (!session.value) return
  busy.value = true
  try { await workflowApi.complete(session.value.name); router.push('/workflow') } finally { busy.value = false }
}
</script>

<template>
  <div class="flex gap-4">
    <!-- Sidebar progress -->
    <aside class="w-52 shrink-0">
      <div class="card p-3 sticky top-4">
        <div class="text-xs font-semibold text-surface-500 uppercase tracking-wide px-2 py-1">Workflow</div>
        <button
          v-for="s in STEPS" :key="s.n"
          class="w-full text-left flex items-center gap-3 px-2 py-2.5 rounded-lg"
          :class="[step === s.n ? 'bg-brand-navy-50' : 'hover:bg-surface-50', s.n <= (session?.current_step || 1) ? 'cursor-pointer' : 'opacity-40 cursor-not-allowed']"
          @click="gotoStep(s.n)"
        >
          <span class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2"
            :class="s.n < step ? 'bg-brand-teal-500 text-white border-brand-teal-500'
                  : s.n === step ? 'bg-brand-teal-100 text-brand-teal-700 border-brand-teal-500'
                  : 'bg-surface-100 text-surface-400 border-surface-300'">
            <span v-if="s.n < step">✓</span><span v-else>{{ s.n }}</span>
          </span>
          <span>
            <span class="block text-sm font-medium" :class="step === s.n ? 'text-brand-navy-700' : 'text-surface-700'">{{ s.label }}</span>
            <span class="block text-xs text-surface-400">{{ s.desc }}</span>
          </span>
        </button>
        <div v-if="session" class="px-2 pt-2 mt-2 border-t border-surface-100 text-xs text-surface-400">{{ session.name }}</div>
      </div>
    </aside>

    <!-- Step content -->
    <main class="flex-1 min-w-0">
      <div class="flex items-center justify-between mb-4">
        <h1 class="text-2xl font-semibold text-surface-800">Lab Workflow</h1>
        <button class="btn-ghost !py-1.5 !text-xs" @click="router.push('/workflow')">Exit</button>
      </div>
      <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg mb-3">{{ error }}</p>

      <!-- Step 1: Patient -->
      <div v-if="step === 1" class="card p-5">
        <h3 class="font-semibold mb-3">1. Select Patient</h3>
        <Combobox
          placeholder="Click to see all patients, or search…"
          :load-options="loadPatients" :option-key="patientKey" :option-label="patientLabel" :option-subtitle="patientSub"
          :model-label="selectedPatient?.patient_name"
          @select="pickPatient"
        />
        <div class="mt-3">
          <button class="text-sm text-brand-teal-600 hover:underline" @click="showNewPatient = !showNewPatient">
            {{ showNewPatient ? 'Cancel' : '+ Register new patient' }}
          </button>
        </div>
        <div v-if="showNewPatient" class="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <label class="block text-xs text-surface-500 mb-1">First Name <span class="text-status-danger">*</span></label>
            <input v-model="np.first_name" class="input" placeholder="First name" />
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Last Name</label>
            <input v-model="np.last_name" class="input" placeholder="Last name" />
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Gender <span class="text-status-danger">*</span></label>
            <select v-model="np.sex" class="input">
              <option value="" disabled>Select…</option>
              <option>Female</option><option>Male</option><option>Other</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Date of Birth</label>
            <input v-model="np.dob" class="input" type="date" />
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Mobile</label>
            <input v-model="np.mobile" class="input" type="tel" placeholder="+92…" />
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Email</label>
            <input v-model="np.email" class="input" type="email" placeholder="patient@example.com" />
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Blood Group</label>
            <select v-model="np.blood_group" class="input">
              <option value="">—</option>
              <option v-for="bg in BLOOD_GROUPS" :key="bg" :value="bg">{{ bg }}</option>
            </select>
          </div>
          <div>
            <label class="block text-xs text-surface-500 mb-1">Patient ID / UID</label>
            <input v-model="np.uid" class="input" placeholder="National ID, MRN, etc." />
          </div>
          <div class="md:col-span-2">
            <label class="block text-xs text-surface-500 mb-1">Address</label>
            <textarea v-model="np.permanent_address" class="input" rows="2"></textarea>
          </div>
          <button class="btn-primary md:col-span-2" :disabled="busy" @click="createPatient">{{ busy ? 'Saving…' : 'Register &amp; Continue' }}</button>
        </div>
      </div>

      <!-- Step 2: Billing. If this session already submitted the order, show a
           read-only summary instead of letting the user re-bill. -->
      <div v-else-if="step === 2 && session && orderAlreadySubmitted" class="card p-5">
        <h3 class="font-semibold mb-3">2. Order — already submitted</h3>
        <div class="rounded-lg border border-amber-200 bg-amber-50 p-3 mb-4 text-sm text-amber-800">
          ⚠ This workflow's order has already been submitted. It can't be modified from here.
        </div>
        <dl class="text-sm grid grid-cols-1 sm:grid-cols-2 gap-y-2 mb-4">
          <dt class="text-surface-500">Patient</dt><dd>{{ session.patient_name || session.patient || '—' }}</dd>
          <dt class="text-surface-500">Sales Invoice</dt>
          <dd>
            <button v-if="submittedSummary?.invoice" class="text-brand-teal-600 hover:underline"
              @click="router.push(`/billing/${submittedSummary.invoice}`)">{{ submittedSummary.invoice }}</button>
            <span v-else>—</span>
          </dd>
          <dt class="text-surface-500">Service Requests</dt>
          <dd>
            <div v-if="submittedSummary?.orders?.length" class="flex flex-wrap gap-2">
              <button v-for="o in submittedSummary.orders" :key="o" class="text-brand-teal-600 hover:underline"
                @click="router.push(`/orders/${o}`)">{{ o }}</button>
            </div>
            <span v-else>—</span>
          </dd>
        </dl>
        <div class="flex justify-end">
          <button class="btn-primary" @click="step = 3">Continue to Collection →</button>
        </div>
      </div>

      <!-- Step 2: Billing (ported genetest component) — only when not yet submitted -->
      <BillingStep v-else-if="step === 2 && session" :session="(session as any)" @continue="onBillingContinue" />

      <!-- Step 3: Collection (full genetest port) -->
      <CollectionStep v-else-if="step === 3 && session" :session="(session as any)" @continue="toResults" />

      <!-- Step 4: Results -->
      <ResultsStep v-else-if="session" :session="(session as any)" @reload="reloadSession" @finish="finish" />
    </main>
  </div>
</template>
