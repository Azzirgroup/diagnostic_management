<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { getList, frappeError } from '@/api/client'
import { patientsApi } from '@/api/adms'

// Dual-mode page: create OR edit. `/patients/new` → create. `/patients/:name/edit`
// → load the patient, populate the form, then PATCH via patients.update_basic.
// The same template renders both flows (title + button text reflect the mode).

const router = useRouter()
const route = useRoute()
// editingName is the Patient doc name when route is /patients/:name/edit, else null.
const editingName = ref<string | null>(null)
const isEditMode = computed(() => !!editingName.value)
const loading = ref(false)

const form = ref({
  first_name: '',
  last_name: '',
  sex: '',
  // `dob` (ISO date) is what Healthcare's Patient doctype actually stores —
  // we still ship it to the backend. The form, however, asks for age + unit
  // and computes a representative dob (today − age in the chosen unit).
  // On edit, an existing dob is reverse-converted back to age + unit for
  // display via deriveAge().
  dob: '',
  age: '' as number | '',
  age_unit: 'Years' as 'Years' | 'Months' | 'Days',
  mobile: '',
  email: '',
  blood_group: '',
  uid: '',
  permanent_address: '',
  branch: '',
})

const genders = ref<string[]>([])
const branches = ref<{ name: string; branch?: string }[]>([])
const submitting = ref(false)
const error = ref('')

const bloodGroups = [
  'A Positive', 'A Negative', 'AB Positive', 'AB Negative',
  'B Positive', 'B Negative', 'O Positive', 'O Negative',
]

async function loadForEdit() {
  // Route is /patients/:name/edit when this fires; load the patient and seed
  // the form. We hit `patients.detail` (already used by PatientProfile) so the
  // edit page mirrors what the View page shows.
  const name = route.params.name as string | undefined
  if (!name) return
  editingName.value = name
  loading.value = true
  try {
    const p = await patientsApi.detail(name) as Record<string, any>
    const dob = p.dob || ''
    const derived = deriveAgeFromDob(dob)
    form.value = {
      first_name: p.first_name || '',
      last_name: p.last_name || '',
      sex: p.sex || '',
      dob,
      age: derived.age,
      age_unit: derived.unit,
      mobile: p.mobile || '',
      email: p.email || '',
      blood_group: p.blood_group || '',
      uid: p.uid || '',
      permanent_address: p.permanent_address || '',
      branch: p.branch || '',
    }
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to load patient')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const rows = await getList<{ name: string }>({
      doctype: 'Gender',
      fields: ['name'],
      limit_page_length: 20,
    })
    genders.value = rows.map((r) => r.name)
  } catch {
    genders.value = ['Male', 'Female', 'Other']
  }
  // Load branches + pre-fill from the user's branch when creating new.
  try {
    const { branchesApi } = await import('@/api/adms')
    branches.value = await branchesApi.list()
    if (!editingName.value) {
      const auth = (await import('@/stores/auth')).useAuthStore()
      if (auth.isBranchScoped && auth.activeBranch && auth.activeBranch !== 'All Branches') {
        form.value.branch = auth.activeBranch
      }
    }
  } catch { branches.value = [] }
  if (route.name === 'patient-edit') await loadForEdit()
})

// Convert (age, unit) → an ISO `YYYY-MM-DD` representative DOB. We
// approximate Months as 30 days and Years as 365 days — adequate for a
// clinical "age" entry (no patient distinguishes a few days on infant labs;
// adult labs only care about age in years). The result is stored on Healthcare's
// `Patient.dob` so existing reports/queries keep working.
function ageToDob(age: number, unit: 'Years' | 'Months' | 'Days'): string {
  if (!age || age < 0) return ''
  const days = unit === 'Years' ? Math.round(age * 365.25)
             : unit === 'Months' ? Math.round(age * 30)
             : Math.round(age)
  const d = new Date()
  d.setDate(d.getDate() - days)
  return d.toISOString().slice(0, 10)
}
// Reverse direction for the edit page: take an existing dob and pick the
// "nicest" of Years/Months/Days for display (Days under 60, Months under 24,
// otherwise Years).
function deriveAgeFromDob(dob: string): { age: number | ''; unit: 'Years'|'Months'|'Days' } {
  if (!dob) return { age: '', unit: 'Years' }
  const ms = Date.now() - new Date(dob).getTime()
  if (Number.isNaN(ms) || ms < 0) return { age: '', unit: 'Years' }
  const days = Math.floor(ms / (1000 * 60 * 60 * 24))
  if (days < 60) return { age: days, unit: 'Days' }
  const months = Math.floor(days / 30)
  if (months < 24) return { age: months, unit: 'Months' }
  return { age: Math.floor(days / 365.25), unit: 'Years' }
}

async function submit() {
  if (!form.value.first_name.trim()) { error.value = 'First name is required.'; return }
  if (!form.value.sex) { error.value = 'Gender is required.'; return }
  submitting.value = true
  error.value = ''
  // Recompute dob from age + unit (only if user actually entered an age),
  // so the backend always gets a valid ISO date in `dob`.
  const ageNum = typeof form.value.age === 'number' ? form.value.age : parseInt(String(form.value.age || ''), 10)
  if (!Number.isNaN(ageNum) && ageNum > 0) {
    form.value.dob = ageToDob(ageNum, form.value.age_unit)
  }
  try {
    // Send empty strings for explicit clears (the backend treats null=skip,
    // ""=clear so the user can blank out an optional field on edit).
    const payload = {
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim(),
      sex: form.value.sex,
      dob: form.value.dob || '',
      mobile: form.value.mobile.trim(),
      email: form.value.email.trim(),
      blood_group: form.value.blood_group || '',
      uid: form.value.uid.trim(),
      permanent_address: form.value.permanent_address.trim(),
      branch: form.value.branch || '',
    }
    if (isEditMode.value && editingName.value) {
      await patientsApi.updateBasic({ name: editingName.value, ...payload })
      router.push(`/patients/${editingName.value}`)
    } else {
      // Create: omit empty optional fields so we don't carry "" into doc inserts.
      const create: Record<string, string | undefined> = { first_name: payload.first_name, sex: payload.sex }
      for (const k of ['last_name','dob','mobile','email','blood_group','uid','permanent_address','branch'] as const) {
        const v = (payload as any)[k]
        if (v) create[k] = v
      }
      const r = await patientsApi.createBasic(create as any)
      router.push(`/patients/${r.name}`)
    }
  } catch (e: any) {
    error.value = frappeError(e, isEditMode.value ? 'Failed to update patient' : 'Failed to create patient')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Topbar :title="isEditMode ? 'Edit Patient' : 'Register Patient'"
          :subtitle="isEditMode ? `Update ${editingName}` : 'Create a new patient record'" />

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>
  <form v-else class="card p-6 max-w-4xl" @submit.prevent="submit">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">First Name <span class="text-status-danger">*</span></label>
        <input v-model="form.first_name" class="input" type="text" autocomplete="given-name" required />
      </div>
      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Last Name</label>
        <input v-model="form.last_name" class="input" type="text" autocomplete="family-name" />
      </div>

      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Gender <span class="text-status-danger">*</span></label>
        <select v-model="form.sex" class="input" required>
          <option value="" disabled>Select…</option>
          <option v-for="g in genders" :key="g" :value="g">{{ g }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Age</label>
        <div class="flex gap-2">
          <input v-model.number="form.age" class="input flex-1" type="number" min="0" placeholder="e.g. 32" />
          <select v-model="form.age_unit" class="input w-32">
            <option value="Years">Years</option>
            <option value="Months">Months</option>
            <option value="Days">Days</option>
          </select>
        </div>
        <p class="text-[11px] text-surface-400 mt-1">DOB is computed from age (today − age in the unit chosen).</p>
      </div>

      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Mobile</label>
        <input v-model="form.mobile" class="input" type="tel" autocomplete="tel" placeholder="+92…" />
      </div>
      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Email</label>
        <input v-model="form.email" class="input" type="email" autocomplete="email" placeholder="patient@example.com" />
      </div>

      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Blood Group</label>
        <select v-model="form.blood_group" class="input">
          <option value="">—</option>
          <option v-for="bg in bloodGroups" :key="bg" :value="bg">{{ bg }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Patient ID / UID</label>
        <input v-model="form.uid" class="input" type="text" placeholder="National ID, MRN, etc." />
      </div>

      <div>
        <label class="block text-sm font-medium text-surface-700 mb-1">Branch</label>
        <select v-model="form.branch" class="input">
          <option value="">— No branch (visible to all branches) —</option>
          <option v-for="b in branches" :key="b.name" :value="b.name">{{ b.branch || b.name }}</option>
        </select>
        <p class="text-xs text-surface-500 mt-1">Defaults to your branch when scoped. Leave empty to register globally.</p>
      </div>

      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-surface-700 mb-1">Address</label>
        <textarea v-model="form.permanent_address" class="input" rows="2" />
      </div>
    </div>

    <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg mt-4">{{ error }}</p>

    <div class="flex gap-2 mt-6">
      <button type="submit" class="btn-primary" :disabled="submitting">
        {{ submitting ? 'Saving…' : isEditMode ? 'Save Changes' : 'Create Patient' }}
      </button>
      <button type="button" class="btn-ghost" @click="router.back()">Cancel</button>
    </div>
  </form>
</template>
