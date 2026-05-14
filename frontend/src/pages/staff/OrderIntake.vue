<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { getList, createDoc } from '@/api/client'
import SearchBar from '@/components/ui/SearchBar.vue'

type Test = { name: string; lab_test_name: string; lab_test_rate?: number; tat?: string; sample?: string }

const patientSearch = ref('')
const patients = ref<any[]>([])
const selectedPatient = ref<any>(null)

const testQuery = ref('')
const tab = ref<'lab' | 'rad' | 'pkg' | 'fav'>('lab')
const tests = ref<Test[]>([])
const selectedTests = ref<Test[]>([])

const priority = ref<'Routine' | 'High' | 'Stat'>('Routine')
const referringDoctor = ref('')
const collectionInstructions = ref('')
const fastingNotes = ref('')
const discountPct = ref(0)
const submitting = ref(false)
const error = ref('')
const router = useRouter()

const subtotal = computed(() => selectedTests.value.reduce((s, t) => s + (t.lab_test_rate || 0), 0))
const tax = computed(() => Math.round(subtotal.value * 0.16))
const total = computed(() => Math.round(subtotal.value * (1 - discountPct.value / 100)) + tax.value)

async function searchPatients() {
  if (!patientSearch.value) return (patients.value = [])
  patients.value = await getList({
    doctype: 'Patient',
    fields: ['name', 'patient_name', 'sex', 'mobile', 'dob'],
    filters: { patient_name: ['like', `%${patientSearch.value}%`] },
    limit_page_length: 6,
  })
}

async function loadTests() {
  tests.value = await getList<Test>({
    doctype: 'Lab Test Template',
    fields: ['name', 'lab_test_name', 'lab_test_rate', 'sample'],
    filters: testQuery.value ? { lab_test_name: ['like', `%${testQuery.value}%`] } : undefined,
    limit_page_length: 30,
  })
}
onMounted(loadTests)

function addTest(t: Test) {
  if (selectedTests.value.find((s) => s.name === t.name)) return
  selectedTests.value.push(t)
}

function removeTest(name: string) {
  selectedTests.value = selectedTests.value.filter((t) => t.name !== name)
}

async function submitOrder() {
  if (!selectedPatient.value) { error.value = 'Please select a patient.'; return }
  if (!selectedTests.value.length) { error.value = 'Please add at least one test.'; return }
  submitting.value = true
  error.value = ''
  try {
    // Service Request is the canonical Marley/FHIR order doctype.
    const doc = await createDoc<any>('Service Request', {
      patient: selectedPatient.value.name,
      patient_name: selectedPatient.value.patient_name,
      priority: priority.value,
      subject: selectedTests.value.map((t) => t.lab_test_name).join(', '),
      template_dt: 'Lab Test Template',
      template_dn: selectedTests.value[0].name,
      status: 'Active',
      occurrence_date: new Date().toISOString().slice(0, 10),
    })
    router.push(`/orders/${doc.name}`)
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to create order'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Topbar title="Order Intake" />

  <!-- Patient -->
  <div class="card p-5 mb-4">
    <div class="text-sm font-semibold text-surface-800 mb-3">1. Select Patient</div>
    <SearchBar v-model="patientSearch" placeholder="Search by name, MRN, phone number..." @update:modelValue="searchPatients" />
    <div v-if="patients.length" class="mt-3 grid grid-cols-1 md:grid-cols-3 gap-2">
      <button
        v-for="p in patients"
        :key="p.name"
        class="text-left p-3 border border-surface-200 rounded-lg hover:border-brand-teal-500 hover:bg-brand-teal-50/30"
        :class="{ 'border-brand-teal-500 bg-brand-teal-50/40': selectedPatient?.name === p.name }"
        @click="selectedPatient = p"
      >
        <div class="font-medium text-surface-800">{{ p.patient_name }}</div>
        <div class="text-xs text-surface-500">{{ p.sex || '—' }} · {{ p.mobile || 'no phone' }}</div>
      </button>
    </div>
    <div v-else-if="selectedPatient" class="mt-3 text-sm text-surface-700">
      Selected: <span class="font-medium">{{ selectedPatient.patient_name }}</span>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <!-- Tests -->
    <div class="lg:col-span-2 card p-5">
      <div class="text-sm font-semibold text-surface-800 mb-4">1. Select Tests / Services</div>
      <div class="flex gap-2 mb-4">
        <button :class="['btn-ghost', tab === 'lab' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'lab'">Laboratory</button>
        <button :class="['btn-ghost', tab === 'rad' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'rad'">Radiology</button>
        <button :class="['btn-ghost', tab === 'pkg' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'pkg'">Packages</button>
        <button :class="['btn-ghost', tab === 'fav' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'fav'">Favorites</button>
      </div>
      <SearchBar v-model="testQuery" placeholder="Search tests (e.g., CBC, Lipid Profile...)" @update:modelValue="loadTests" />

      <div class="mt-3 flex flex-wrap gap-2">
        <button
          v-for="t in tests.slice(0, 6)" :key="t.name"
          class="btn-ghost !py-1.5 !text-xs"
          @click="addTest(t)"
        >
          + {{ t.lab_test_name }}
        </button>
      </div>

      <div class="mt-5 font-semibold text-sm text-surface-700">Selected Tests ({{ selectedTests.length }})</div>
      <table class="w-full mt-2 text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">Test</th><th>Specimen</th><th class="text-right">Price</th><th></th>
        </tr></thead>
        <tbody>
          <tr v-if="!selectedTests.length"><td colspan="4" class="py-6 text-center text-surface-400">No tests selected</td></tr>
          <tr v-for="t in selectedTests" :key="t.name" class="border-b border-surface-100">
            <td class="py-2">{{ t.lab_test_name }}</td>
            <td>{{ t.sample || '—' }}</td>
            <td class="text-right">{{ (t.lab_test_rate || 0).toLocaleString() }}</td>
            <td class="text-right"><button class="text-status-danger" @click="removeTest(t.name)">×</button></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Order settings + billing -->
    <div class="space-y-4">
      <div class="card p-5">
        <div class="text-sm font-semibold text-surface-800 mb-3">2. Order Settings</div>
        <label class="block text-xs text-surface-500 mb-1">Priority</label>
        <select v-model="priority" class="input mb-3">
          <option value="Routine">Routine</option>
          <option value="High">High</option>
          <option value="Stat">Stat</option>
        </select>
        <label class="block text-xs text-surface-500 mb-1">Referring Doctor (Optional)</label>
        <input v-model="referringDoctor" class="input mb-3" placeholder="Search doctor by name" />
        <label class="block text-xs text-surface-500 mb-1">Collection Instructions</label>
        <textarea v-model="collectionInstructions" class="input mb-3" rows="2" placeholder="e.g., Draw from left arm, avoid hemolysis..." maxlength="200"></textarea>
        <label class="block text-xs text-surface-500 mb-1">Fasting / Preparation Notes</label>
        <textarea v-model="fastingNotes" class="input" rows="2" placeholder="e.g., 10-12 hours fasting required" maxlength="200"></textarea>
      </div>

      <div class="card p-5">
        <div class="text-sm font-semibold text-surface-800 mb-3">3. Billing &amp; Checkout</div>
        <div class="flex items-center justify-between mb-3">
          <label class="text-sm">Discount %</label>
          <input v-model.number="discountPct" type="number" min="0" max="100" class="input w-20 text-right" />
        </div>
        <dl class="text-sm space-y-1">
          <div class="flex justify-between"><dt>Subtotal ({{ selectedTests.length }} items)</dt><dd>{{ subtotal.toLocaleString() }}</dd></div>
          <div class="flex justify-between"><dt>Tax (16%)</dt><dd>{{ tax.toLocaleString() }}</dd></div>
          <div class="flex justify-between border-t border-surface-200 pt-2 mt-2 font-semibold">
            <dt>Total Amount</dt><dd class="text-brand-teal-700">{{ total.toLocaleString() }}</dd>
          </div>
        </dl>
        <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg mt-3">{{ error }}</p>
        <button class="btn-primary w-full mt-4" :disabled="submitting" @click="submitOrder">
          {{ submitting ? 'Creating…' : 'Create Order' }}
        </button>
        <button class="btn-ghost w-full mt-2">Save Draft</button>
      </div>
    </div>
  </div>
</template>
