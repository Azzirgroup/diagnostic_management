<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { customersApi, type CustomerDetail } from '@/api/adms'
import { frappeError } from '@/api/client'

const route = useRoute()
const router = useRouter()
const detail = ref<CustomerDetail | null>(null)
const form = ref<Partial<CustomerDetail>>({})
const customerGroups = ref<string[]>([])
const territories = ref<string[]>([])
const loading = ref(true)
const saving = ref(false)
const editing = ref(false)
const error = ref('')
const success = ref('')

async function load() {
  loading.value = true; error.value = ''
  const name = decodeURIComponent(route.params.name as string)
  try {
    detail.value = await customersApi.get(name)
    form.value = { ...detail.value }
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to load customer')
    detail.value = null
  } finally { loading.value = false }
}

onMounted(async () => {
  // Load dropdown options in parallel; non-fatal if either fails.
  Promise.all([
    customersApi.customerGroups().then((g) => (customerGroups.value = g)).catch(() => {}),
    customersApi.territories().then((t) => (territories.value = t)).catch(() => {}),
  ])
  load()
})

const hasChanges = computed(() => {
  if (!detail.value) return false
  for (const k of Object.keys(form.value) as (keyof CustomerDetail)[]) {
    if (form.value[k] !== detail.value[k]) return true
  }
  return false
})

async function save() {
  if (!detail.value) return
  saving.value = true; error.value = ''; success.value = ''
  try {
    // Send only changed fields — keeps the audit trail tight + lets the
    // server's allowlist check stay strict.
    const updates: Record<string, unknown> = {}
    for (const k of Object.keys(form.value)) {
      if (form.value[k as keyof CustomerDetail] !== detail.value[k as keyof CustomerDetail]) {
        updates[k] = form.value[k as keyof CustomerDetail]
      }
    }
    const res = await customersApi.update(detail.value.name, updates)
    success.value = `Saved (${res.changed.length} field${res.changed.length === 1 ? '' : 's'} updated)`
    editing.value = false
    await load()  // re-fetch to reflect any server-side normalisation
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to save customer')
  } finally { saving.value = false }
}

function cancel() {
  if (detail.value) form.value = { ...detail.value }
  editing.value = false
  error.value = ''; success.value = ''
}
</script>

<template>
  <Topbar :title="detail?.customer_name ? `Customer: ${detail.customer_name}` : 'Customer'" />

  <div class="mb-4">
    <button class="text-sm text-brand-teal-600 hover:underline" @click="router.push('/customers')">
      ← Back to all customers
    </button>
  </div>

  <div v-if="loading" class="card p-6 text-surface-400">Loading…</div>
  <div v-else-if="!detail" class="card p-6 text-status-danger">
    {{ error || 'Customer not found.' }}
  </div>

  <template v-else>
    <!-- Header card -->
    <div class="card p-5 mb-4 flex items-center justify-between flex-wrap gap-3">
      <div>
        <h2 class="text-xl font-semibold text-surface-800">{{ detail.customer_name }}</h2>
        <div class="text-sm text-surface-500 mt-1">ID: <span class="font-mono">{{ detail.name }}</span></div>
        <div v-if="detail.linked_patient" class="text-sm mt-1">
          Linked Patient:
          <RouterLink :to="`/patients/${encodeURIComponent(detail.linked_patient)}`"
            class="text-brand-teal-600 hover:underline">{{ detail.linked_patient }}</RouterLink>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button v-if="!editing" class="btn-primary px-3 py-1.5 rounded text-sm" @click="editing = true">Edit</button>
        <template v-else>
          <button class="btn-outline px-3 py-1.5 rounded text-sm" @click="cancel" :disabled="saving">Cancel</button>
          <button class="btn-primary px-3 py-1.5 rounded text-sm" @click="save"
                  :disabled="saving || !hasChanges">{{ saving ? 'Saving…' : 'Save' }}</button>
        </template>
      </div>
    </div>

    <div v-if="error" class="card p-3 bg-red-50 border-red-200 text-sm text-red-700 mb-3">{{ error }}</div>
    <div v-if="success" class="card p-3 bg-green-50 border-green-200 text-sm text-green-700 mb-3">{{ success }}</div>

    <!-- Editable form / read view -->
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Customer Details</h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Customer Name</label>
          <input v-if="editing" v-model="form.customer_name" type="text" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <span v-else class="text-sm">{{ detail.customer_name || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Customer Type</label>
          <select v-if="editing" v-model="form.customer_type" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm">
            <option value="Individual">Individual</option>
            <option value="Company">Company</option>
            <option value="Partnership">Partnership</option>
          </select>
          <span v-else class="text-sm">{{ detail.customer_type || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Customer Group</label>
          <select v-if="editing" v-model="form.customer_group" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm">
            <option value="">— pick —</option>
            <option v-for="g in customerGroups" :key="g" :value="g">{{ g }}</option>
          </select>
          <span v-else class="text-sm">{{ detail.customer_group || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Territory</label>
          <select v-if="editing" v-model="form.territory" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm">
            <option value="">— pick —</option>
            <option v-for="t in territories" :key="t" :value="t">{{ t }}</option>
          </select>
          <span v-else class="text-sm">{{ detail.territory || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Mobile</label>
          <input v-if="editing" v-model="form.mobile_no" type="text" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <span v-else class="text-sm">{{ detail.mobile_no || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Email</label>
          <input v-if="editing" v-model="form.email_id" type="email" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <span v-else class="text-sm">{{ detail.email_id || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Tax ID</label>
          <input v-if="editing" v-model="form.tax_id" type="text" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <span v-else class="text-sm">{{ detail.tax_id || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1">
          <label class="text-xs font-medium text-surface-500">Default Currency</label>
          <input v-if="editing" v-model="form.default_currency" type="text" placeholder="e.g. KES" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <span v-else class="text-sm">{{ detail.default_currency || '—' }}</span>
        </div>

        <div class="flex flex-col gap-1 md:col-span-2">
          <label class="text-xs font-medium text-surface-500">Status</label>
          <label v-if="editing" class="inline-flex items-center gap-2 text-sm">
            <input v-model="form.disabled" type="checkbox" :true-value="1" :false-value="0" />
            <span>Disabled — hide from new invoices</span>
          </label>
          <span v-else class="text-sm">{{ detail.disabled ? 'Disabled' : 'Active' }}</span>
        </div>
      </div>
    </div>
  </template>
</template>
