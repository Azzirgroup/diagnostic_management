<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import SearchBar from '@/components/ui/SearchBar.vue'
import { labReportsApi, type LabReportRow, type LabReportSummary } from '@/api/adms'

// Lab Reports browser. Lists every released Lab Report; lets the user search,
// filter by status / date, and open either the printable HTML (verbatim
// genetest format) or the form view for editing/inspection.

const router = useRouter()
const rows = ref<LabReportRow[]>([])
const summary = ref<LabReportSummary | null>(null)
const loading = ref(false)
const search = ref('')
const statusFilter = ref<'' | 'Approved' | 'Open' | 'Pending Review' | 'Rejected'>('')
const dateFrom = ref('')
const dateTo = ref('')

async function load() {
  loading.value = true
  try {
    const payload: Record<string, string | number | undefined> = { limit: 200 }
    if (search.value.trim()) payload.query = search.value.trim()
    if (statusFilter.value) payload.status = statusFilter.value
    if (dateFrom.value) payload.date_from = dateFrom.value
    if (dateTo.value) payload.date_to = dateTo.value
    rows.value = await labReportsApi.list(payload as any)
  } catch { rows.value = [] }
  finally { loading.value = false }
}
async function loadSummary() {
  try { summary.value = await labReportsApi.summary() } catch { summary.value = null }
}

onMounted(async () => { await Promise.all([load(), loadSummary()]) })

// Debounce search (avoid hammering the API on every keystroke).
let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(search, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 250)
})
watch([statusFilter, dateFrom, dateTo], load)

// Quick date-range helpers
function setToday() {
  const t = new Date().toISOString().slice(0, 10)
  dateFrom.value = t; dateTo.value = t
}
function setLast7() {
  const today = new Date()
  const week = new Date(today.getTime() - 7 * 86400000)
  dateFrom.value = week.toISOString().slice(0, 10)
  dateTo.value = today.toISOString().slice(0, 10)
}
function setLast30() {
  const today = new Date()
  const month = new Date(today.getTime() - 30 * 86400000)
  dateFrom.value = month.toISOString().slice(0, 10)
  dateTo.value = today.toISOString().slice(0, 10)
}
function clearDates() { dateFrom.value = ''; dateTo.value = '' }
function clearAll() {
  search.value = ''; statusFilter.value = ''; dateFrom.value = ''; dateTo.value = ''
}

const activeFilters = computed(() => {
  const f: string[] = []
  if (statusFilter.value) f.push(`Status: ${statusFilter.value}`)
  if (dateFrom.value && dateTo.value) f.push(`Dates: ${dateFrom.value} → ${dateTo.value}`)
  else if (dateFrom.value) f.push(`From: ${dateFrom.value}`)
  else if (dateTo.value) f.push(`To: ${dateTo.value}`)
  return f
})

function openPrint(name: string) {
  const params = new URLSearchParams({
    doctype: 'Lab Report', name, format: 'Lab Report', no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}
function openForm(name: string) {
  window.open(`/app/lab-report/${name}`, '_blank')
}
</script>

<template>
  <Topbar title="Lab Reports" subtitle="Browse, search and reprint every Lab Report" />

  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Total" :value="summary?.total ?? 0" sub="All reports"
      icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Approved" :value="summary?.approved ?? 0" sub="Released"
      icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Pending" :value="summary?.pending ?? 0" sub="Not yet released"
      icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Today" :value="summary?.today ?? 0" sub="Reports dated today"
      icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
  </div>

  <div class="card p-4 mb-4">
    <div class="grid grid-cols-1 lg:grid-cols-12 gap-3 items-end">
      <div class="lg:col-span-5">
        <label class="block text-xs text-surface-500 mb-1">Search</label>
        <SearchBar v-model="search" placeholder="Patient name, MRN or Lab Report ID…" />
      </div>
      <div class="lg:col-span-2">
        <label class="block text-xs text-surface-500 mb-1">Status</label>
        <select v-model="statusFilter" class="input">
          <option value="">All</option>
          <option>Approved</option>
          <option>Open</option>
          <option>Pending Review</option>
          <option>Rejected</option>
        </select>
      </div>
      <div class="lg:col-span-2">
        <label class="block text-xs text-surface-500 mb-1">From</label>
        <input v-model="dateFrom" type="date" class="input" />
      </div>
      <div class="lg:col-span-2">
        <label class="block text-xs text-surface-500 mb-1">To</label>
        <input v-model="dateTo" type="date" class="input" />
      </div>
      <div class="lg:col-span-1 flex items-end">
        <button class="btn-ghost !py-1.5 !text-xs w-full" @click="clearAll" title="Clear all filters">Clear</button>
      </div>
    </div>
    <div class="flex items-center gap-2 mt-3 flex-wrap">
      <span class="text-xs text-surface-500">Quick:</span>
      <button class="text-xs text-brand-teal-600 hover:underline" @click="setToday">Today</button>
      <button class="text-xs text-brand-teal-600 hover:underline" @click="setLast7">Last 7 days</button>
      <button class="text-xs text-brand-teal-600 hover:underline" @click="setLast30">Last 30 days</button>
      <button v-if="dateFrom || dateTo" class="text-xs text-surface-500 hover:underline ml-2" @click="clearDates">clear dates</button>
      <span v-for="f in activeFilters" :key="f" class="text-xs px-2 py-0.5 rounded bg-brand-teal-50 text-brand-teal-700 ml-2">
        {{ f }}
      </span>
    </div>
  </div>

  <div class="card p-1">
    <DataTable :rows="rows" row-key="name"
      :empty-text="loading ? 'Loading…' : 'No reports match these filters'"
      :columns="[
        { key: 'name', label: 'Report ID' },
        { key: 'patient_name', label: 'Patient' },
        { key: 'patient_sex', label: 'Sex' },
        { key: 'report_date', label: 'Date' },
        { key: 'pathologist_name', label: 'Reported by' },
        { key: 'status', label: 'Status' },
        { key: 'creation', label: 'Actions' },
      ]"
    >
      <template #cell-name="{ row, value }">
        <div class="flex flex-col">
          <button class="text-brand-teal-600 hover:underline text-left font-medium" @click.stop="openPrint(value as string)">{{ value }}</button>
          <span v-if="(row as LabReportRow).samples?.length" class="text-xs text-surface-400">
            sample: {{ (row as LabReportRow).samples?.join(', ') }}
          </span>
        </div>
      </template>
      <template #cell-patient_name="{ row, value }">
        <div class="flex flex-col">
          <span class="font-medium text-surface-800">{{ value || (row as LabReportRow).patient || '—' }}</span>
          <span class="text-xs text-surface-400">{{ (row as LabReportRow).patient || '' }}</span>
        </div>
      </template>
      <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      <template #cell-creation="{ row }">
        <div class="flex gap-2 justify-end">
          <button class="text-xs text-brand-teal-600 hover:underline" @click.stop="openPrint((row as LabReportRow).name)" title="Open printable Lab Report">Print</button>
          <button class="text-xs text-brand-navy-700 hover:underline" @click.stop="openForm((row as LabReportRow).name)" title="Open form view in Desk">View</button>
        </div>
      </template>
    </DataTable>
  </div>
</template>
