<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { customersApi, type CustomerRow } from '@/api/adms'
import { frappeError } from '@/api/client'

const router = useRouter()
const rows = ref<CustomerRow[]>([])
const total = ref(0)
const query = ref('')
const groupFilter = ref('')
const customerGroups = ref<string[]>([])
const loading = ref(false)
const error = ref('')

const PAGE = 50
const offset = ref(0)
const pageFrom = computed(() => (rows.value.length ? offset.value + 1 : 0))
const pageTo = computed(() => offset.value + rows.value.length)

async function load() {
  loading.value = true; error.value = ''
  try {
    const res = await customersApi.list(query.value, PAGE, offset.value, groupFilter.value || undefined)
    rows.value = res.rows
    total.value = res.total
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to load customers')
    rows.value = []; total.value = 0
  } finally { loading.value = false }
}

// Debounced search — typing in the search box re-queries 300ms after the
// last keystroke so we don't hammer the API on every char.
let searchTimer: number | null = null
watch(query, () => {
  if (searchTimer) window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(() => { offset.value = 0; load() }, 300)
})
watch(groupFilter, () => { offset.value = 0; load() })

onMounted(async () => {
  try { customerGroups.value = await customersApi.customerGroups() } catch { /* non-fatal */ }
  load()
})

function openDetail(c: CustomerRow) {
  router.push(`/customers/${encodeURIComponent(c.name)}`)
}
function prev() { if (offset.value > 0) { offset.value = Math.max(0, offset.value - PAGE); load() } }
function next() { if (offset.value + PAGE < total.value) { offset.value += PAGE; load() } }
</script>

<template>
  <Topbar title="Customers" />

  <!-- Search + filters -->
  <div class="card p-4 mb-4 flex flex-wrap items-center gap-3">
    <input
      v-model="query"
      type="text"
      placeholder="Search by name, ID, mobile, email, tax ID…"
      class="input flex-1 min-w-[260px] px-3 py-2 rounded border border-surface-200 text-sm"
    />
    <select v-model="groupFilter" class="input px-3 py-2 rounded border border-surface-200 text-sm">
      <option value="">All Customer Groups</option>
      <option v-for="g in customerGroups" :key="g" :value="g">{{ g }}</option>
    </select>
  </div>

  <div v-if="error" class="card p-3 bg-red-50 border-red-200 text-sm text-red-700 mb-3">{{ error }}</div>

  <!-- Results -->
  <div class="card p-0 overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-surface-50 text-surface-500 text-xs uppercase">
        <tr>
          <th class="text-left py-2 px-3">Name</th>
          <th class="text-left py-2 px-3">Group</th>
          <th class="text-left py-2 px-3">Territory</th>
          <th class="text-left py-2 px-3">Mobile</th>
          <th class="text-left py-2 px-3">Email</th>
          <th class="text-left py-2 px-3">Tax ID</th>
          <th class="text-left py-2 px-3">Linked Patient</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="loading"><td colspan="7" class="py-6 text-center text-surface-400">Loading…</td></tr>
        <tr v-else-if="!rows.length"><td colspan="7" class="py-6 text-center text-surface-400">No customers found.</td></tr>
        <tr v-for="c in rows" :key="c.name"
            class="border-t border-surface-100 hover:bg-surface-50 cursor-pointer"
            @click="openDetail(c)">
          <td class="py-2 px-3">
            <div class="font-medium text-surface-800">{{ c.customer_name || c.name }}</div>
            <div class="text-xs text-surface-500">{{ c.name }}</div>
          </td>
          <td class="py-2 px-3">{{ c.customer_group || '—' }}</td>
          <td class="py-2 px-3">{{ c.territory || '—' }}</td>
          <td class="py-2 px-3">{{ c.mobile_no || '—' }}</td>
          <td class="py-2 px-3 truncate max-w-[200px]">{{ c.email_id || '—' }}</td>
          <td class="py-2 px-3">{{ c.tax_id || '—' }}</td>
          <td class="py-2 px-3">
            <RouterLink v-if="c.linked_patient" :to="`/patients/${encodeURIComponent(c.linked_patient)}`"
              class="text-brand-teal-600 hover:underline"
              @click.stop>{{ c.linked_patient }}</RouterLink>
            <span v-else class="text-surface-400">—</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Pagination -->
  <div class="mt-3 flex items-center justify-between text-sm text-surface-500">
    <div>Showing {{ pageFrom }}–{{ pageTo }} of {{ total }}</div>
    <div class="flex gap-2">
      <button :disabled="offset === 0" @click="prev"
        class="px-3 py-1 rounded border border-surface-200 disabled:opacity-40">Previous</button>
      <button :disabled="offset + rows.length >= total" @click="next"
        class="px-3 py-1 rounded border border-surface-200 disabled:opacity-40">Next</button>
    </div>
  </div>
</template>
