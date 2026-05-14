<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { createDoc, getList } from '@/api/client'

const router = useRouter()

const form = ref({
  first_name: '',
  last_name: '',
  sex: '',
  dob: '',
  mobile: '',
  email: '',
  blood_group: '',
  uid: '',
  permanent_address: '',
})

const genders = ref<string[]>([])
const submitting = ref(false)
const error = ref('')

const bloodGroups = [
  'A Positive', 'A Negative', 'AB Positive', 'AB Negative',
  'B Positive', 'B Negative', 'O Positive', 'O Negative',
]

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
})

async function submit() {
  if (!form.value.first_name.trim()) { error.value = 'First name is required.'; return }
  if (!form.value.sex) { error.value = 'Gender is required.'; return }
  submitting.value = true
  error.value = ''
  try {
    const payload: Record<string, unknown> = {
      first_name: form.value.first_name.trim(),
      last_name: form.value.last_name.trim() || undefined,
      sex: form.value.sex,
      dob: form.value.dob || undefined,
      mobile: form.value.mobile.trim() || undefined,
      email: form.value.email.trim() || undefined,
      blood_group: form.value.blood_group || undefined,
      uid: form.value.uid.trim() || undefined,
      permanent_address: form.value.permanent_address.trim() || undefined,
      status: 'Active',
    }
    Object.keys(payload).forEach((k) => payload[k] === undefined && delete payload[k])

    const doc = await createDoc<{ name: string }>('Patient', payload)
    router.push(`/patients/${doc.name}`)
  } catch (e: unknown) {
    const err = e as { response?: { data?: { _server_messages?: string; exception?: string; message?: string } }; message?: string }
    const sm = err?.response?.data?._server_messages
    if (sm) {
      try {
        const parsed = JSON.parse(sm)
        const first = Array.isArray(parsed) ? JSON.parse(parsed[0]) : parsed
        error.value = first?.message || 'Failed to create patient'
      } catch {
        error.value = 'Failed to create patient'
      }
    } else {
      error.value = err?.response?.data?.message || err?.message || 'Failed to create patient'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Topbar title="Register Patient" subtitle="Create a new patient record" />

  <form class="card p-6 max-w-4xl" @submit.prevent="submit">
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
        <label class="block text-sm font-medium text-surface-700 mb-1">Date of Birth</label>
        <input v-model="form.dob" class="input" type="date" />
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

      <div class="md:col-span-2">
        <label class="block text-sm font-medium text-surface-700 mb-1">Address</label>
        <textarea v-model="form.permanent_address" class="input" rows="2" />
      </div>
    </div>

    <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg mt-4">{{ error }}</p>

    <div class="flex gap-2 mt-6">
      <button type="submit" class="btn-primary" :disabled="submitting">
        {{ submitting ? 'Saving…' : 'Create Patient' }}
      </button>
      <button type="button" class="btn-ghost" @click="router.back()">Cancel</button>
    </div>
  </form>
</template>
