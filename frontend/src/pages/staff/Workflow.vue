<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { collectionApi, labApi, workflowApi } from '@/api/adms'

// Lab Workflow launchpad: start a new guided workflow (single-page wizard),
// resume an in-progress Lab Workflow Session, and jump to any stage queue.
const router = useRouter()
const loading = ref(true)
const counts = ref({ collection: 0, store: 0, result: 0 })
const sessions = ref<Array<{ name: string; patient_name?: string; status?: string; current_step?: number; workflow_started?: string; modified?: string }>>([])

// "Date of client visit" = when the workflow session was started. Fall back to
// `modified` for legacy sessions saved before workflow_started was populated.
function visitDate(s: { workflow_started?: string; modified?: string }) {
  const raw = s.workflow_started || s.modified
  if (!raw) return '—'
  const d = new Date(raw.replace(' ', 'T'))
  return isNaN(d.getTime()) ? '—' : d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
const search = ref('')
const includeCompleted = ref(false)
let searchDebounce: ReturnType<typeof setTimeout> | null = null

const STEP_LABELS = ['', 'Patient', 'Order', 'Collection', 'Results']

async function loadSessions() {
  try {
    sessions.value = await workflowApi.listOpen(50, search.value, includeCompleted.value)
  } catch { sessions.value = [] }
}

async function load() {
  loading.value = true
  try {
    const [wl, aq, hub] = await Promise.all([
      collectionApi.worklist().catch(() => []),
      collectionApi.accessionQueue(200).catch(() => []),
      labApi.hubSummary().catch(() => ({}) as any),
    ])
    counts.value = {
      collection: wl.length,
      store: aq.filter((s) => s.collected_time && s.workflow_status !== 'Stored').length,
      result: hub.pending_verification || 0,
    }
    await loadSessions()
  } finally {
    loading.value = false
  }
}
onMounted(load)

function onSearchInput() {
  if (searchDebounce) clearTimeout(searchDebounce)
  searchDebounce = setTimeout(loadSessions, 250)
}

const steps = [
  { n: 1, key: 'order', label: 'Order', desc: 'Register the test order', to: '/orders' },
  { n: 2, key: 'collection', label: 'Collection', desc: 'Draw & label the specimen', to: '/collection' },
  { n: 3, key: 'store', label: 'Store', desc: 'Receive & store the sample', to: '/lab/accession' },
  { n: 4, key: 'result', label: 'Result', desc: 'Verify & release results', to: '/lab/verification' },
] as const

function countFor(key: string): number | null {
  if (key === 'collection') return counts.value.collection
  if (key === 'store') return counts.value.store
  if (key === 'result') return counts.value.result
  return null
}
</script>

<template>
  <Topbar title="Lab Workflow" subtitle="Order → Collection → Store → Result" />

  <div class="flex justify-end mb-4">
    <button class="btn-primary" @click="router.push('/workflow/new')">+ Start New Workflow</button>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <button
      v-for="(s, i) in steps"
      :key="s.key"
      class="card p-5 text-left hover:border-brand-teal-500 transition-colors relative"
      @click="router.push(s.to)"
    >
      <div class="flex items-center gap-3 mb-3">
        <span class="w-9 h-9 rounded-full flex items-center justify-center text-sm font-semibold bg-brand-navy-700 text-white">{{ s.n }}</span>
        <div class="font-semibold text-surface-800">{{ s.label }}</div>
      </div>
      <div class="text-sm text-surface-500">{{ s.desc }}</div>
      <div v-if="countFor(s.key) !== null" class="mt-4 flex items-baseline gap-2">
        <span class="text-2xl font-bold text-brand-teal-700">{{ loading ? '—' : countFor(s.key) }}</span>
        <span class="text-xs text-surface-500">waiting</span>
      </div>
      <div v-else class="mt-4 text-xs text-brand-teal-600">View orders →</div>
      <span v-if="i < steps.length - 1" class="hidden lg:block absolute -right-3 top-1/2 -translate-y-1/2 text-surface-300 text-xl z-10">→</span>
    </button>
  </div>

  <!-- Resume a workflow session already in flight -->
  <div class="card p-5 mt-6">
    <div class="flex items-start justify-between gap-4 flex-wrap mb-3">
      <div>
        <h3 class="font-semibold mb-1">Continue where you left off</h3>
        <p class="text-sm text-surface-500">Open workflow sessions. Resume at the step where you stopped.</p>
      </div>
      <div class="flex items-center gap-3 flex-wrap">
        <input
          v-model="search"
          @input="onSearchInput"
          type="text"
          placeholder="Search by session, patient, order…"
          class="input !py-1.5 !px-3 text-sm w-64"
        />
        <label class="flex items-center gap-1.5 text-xs text-surface-600 cursor-pointer select-none">
          <input v-model="includeCompleted" type="checkbox" class="accent-brand-teal-600" @change="loadSessions" />
          Include completed
        </label>
      </div>
    </div>
    <table v-if="sessions.length" class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">Session</th><th>Patient</th><th>Visit Date</th><th>Step</th><th>Status</th><th class="text-right">Action</th>
      </tr></thead>
      <tbody>
        <tr v-for="s in sessions" :key="s.name" class="border-b border-surface-100">
          <td class="py-3 text-brand-teal-600 font-medium">{{ s.name }}</td>
          <td>{{ s.patient_name || '—' }}</td>
          <td class="whitespace-nowrap">{{ visitDate(s) }}</td>
          <td>{{ STEP_LABELS[s.current_step || 1] || s.current_step }}</td>
          <td><StatusPill :status="s.status || 'Draft'" /></td>
          <td class="text-right">
            <button class="btn-secondary !py-1.5 !px-4 !text-xs" @click="router.push(`/workflow/${s.name}`)">Resume →</button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="text-sm text-surface-400 py-3">
      {{ loading ? 'Loading…' : (search || includeCompleted ? 'No sessions match your search.' : 'No open sessions. Start a new workflow above.') }}
    </div>
  </div>

  <p class="text-xs text-surface-400 mt-6">
    Tip: press <span class="border border-surface-200 rounded px-1.5 py-0.5">⌘ K</span> to scan or look up a sample, order, or patient barcode.
  </p>
</template>
