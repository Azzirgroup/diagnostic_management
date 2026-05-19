<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { call, getList } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

interface PendingOrder {
  name: string
  patient_name: string
  status: string
  priority?: string
}

interface Alert { key: string; title: string; sub: string; count: number; tone: string }
interface Analyzer { name: string; status: string }
interface Workflow {
  collected: number
  in_processing: number
  in_analysis: number
  result_ready: number
  completed: number
}
interface BranchPerf {
  samples_processed: number
  reports_released: number
  avg_tat_minutes: number
  rejection_rate_pct: number
}

const auth = useAuthStore()

const kpis = ref({
  pending_samples: 0,
  pending_delta: 0,
  avg_tat_minutes: 0,
  critical_results: 0,
  reagent_alerts: 0,
})
const alerts = ref<Alert[]>([])
const analyzers = ref<Analyzer[]>([])
const pending = ref<PendingOrder[]>([])
const workflow = ref<Workflow>({ collected: 0, in_processing: 0, in_analysis: 0, result_ready: 0, completed: 0 })
const branch = ref<BranchPerf>({ samples_processed: 0, reports_released: 0, avg_tat_minutes: 0, rejection_rate_pct: 0 })

const stages: Array<{ key: keyof Workflow; label: string; color: string }> = [
  { key: 'collected', label: 'Collected', color: '#0B2440' },
  { key: 'in_processing', label: 'In Processing', color: '#1A8B96' },
  { key: 'in_analysis', label: 'In Analysis', color: '#274D7E' },
  { key: 'result_ready', label: 'Result Ready', color: '#7B96B8' },
  { key: 'completed', label: 'Completed', color: '#15803D' },
]

async function load() {
  // Each backend call is wrapped — endpoints may not be installed yet, page still renders.
  try {
    const data = await call<typeof kpis.value>('diagnostic_management.api.dashboard.lab_manager')
    if (data) kpis.value = data
  } catch { /* keep defaults */ }

  try {
    // Service Request status is a Code Value link in v16 — use the document
    // names directly. The display layer strips the suffix for the pill.
    pending.value = await getList<PendingOrder>({
      doctype: 'Service Request',
      fields: ['name', 'patient_name', 'status', 'priority'],
      filters: { status: ['in', ['active-Request Status', 'draft-Request Status', 'on-hold-Request Status']] },
      limit_page_length: 5,
      order_by: 'modified desc',
    })
    pending.value = pending.value.map((p) => ({
      ...p,
      status: (p.status || '').replace(/-Request Status$/i, ''),
      priority: (p.priority || '').replace(/-Priority$/i, ''),
    }))
  } catch { pending.value = [] }

  try {
    const a = await call<Alert[]>('diagnostic_management.api.dashboard.alerts')
    alerts.value = a || []
  } catch { alerts.value = [] }

  try {
    const an = await call<Analyzer[]>('diagnostic_management.api.dashboard.analyzers')
    analyzers.value = an || []
  } catch { analyzers.value = [] }

  try {
    const w = await call<Workflow>('diagnostic_management.api.dashboard.workflow_overview')
    if (w) workflow.value = w
  } catch { /* keep zeros */ }

  try {
    const b = await call<BranchPerf>('diagnostic_management.api.dashboard.branch_performance')
    if (b) branch.value = b
  } catch { /* keep zeros */ }
}

onMounted(load)

function formatTat(m: number) {
  if (!m) return '—'
  const h = Math.floor(m / 60), mm = m % 60
  return `${h}h ${String(mm).padStart(2, '0')}m`
}
</script>

<template>
  <Topbar :title="auth.primaryRole === 'Lab Manager' ? 'Lab Manager Dashboard' : 'Diagnostic Dashboard'" />

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <KpiCard
      label="Pending Samples"
      :value="kpis.pending_samples"
      :delta="kpis.pending_delta ? `${kpis.pending_delta > 0 ? '+' : ''}${kpis.pending_delta} from yesterday` : ''"
      :delta-direction="kpis.pending_delta >= 0 ? 'up' : 'down'"
      icon-bg="rgb(239 246 255)"
      icon-color="rgb(29 78 216)"
    />
    <KpiCard
      label="Avg TAT Today"
      :value="formatTat(kpis.avg_tat_minutes)"
      sub="Goal: ≤ 4h"
      icon-bg="rgb(220 252 231)"
      icon-color="rgb(21 128 61)"
    />
    <KpiCard
      label="Critical Results"
      :value="kpis.critical_results"
      sub="Requires immediate review"
      icon-bg="rgb(254 226 226)"
      icon-color="rgb(185 28 28)"
    />
    <KpiCard
      label="Reagent Alerts"
      :value="kpis.reagent_alerts"
      sub="Low stock / Expiring"
      icon-bg="rgb(254 243 199)"
      icon-color="rgb(180 83 9)"
    />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-surface-800">Sample Workflow Overview</h2>
        </div>
        <div class="grid grid-cols-5 gap-2">
          <div v-for="s in stages" :key="s.key" class="text-center">
            <div class="w-12 h-12 mx-auto rounded-full flex items-center justify-center" :style="{ background: `${s.color}1A`, color: s.color }">
              <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <rect x="6" y="3" width="12" height="18" rx="2" fill="currentColor"/>
              </svg>
            </div>
            <div class="text-xs text-surface-500 mt-2">{{ s.label }}</div>
            <div class="text-lg font-semibold text-surface-800">{{ workflow[s.key] }}</div>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <div class="flex items-center justify-between mb-4">
          <h2 class="font-semibold text-surface-800">Pending Worklist</h2>
          <RouterLink class="text-sm text-brand-teal-600 hover:underline" to="/orders">View all orders</RouterLink>
        </div>
        <DataTable
          :rows="pending"
          row-key="name"
          empty-text="No pending orders"
          :columns="[
            { key: 'name', label: 'Order ID' },
            { key: 'patient_name', label: 'Patient' },
            { key: 'priority', label: 'Priority' },
            { key: 'status', label: 'Status' },
          ]"
        >
          <template #cell-priority="{ value }">
            <StatusPill :status="(value as string) || 'Routine'" />
          </template>
          <template #cell-status="{ value }">
            <StatusPill :status="(value as string) || '—'" />
          </template>
        </DataTable>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-surface-800">Alerts &amp; Notifications</h3>
        </div>
        <ul v-if="alerts.length" class="space-y-3">
          <li v-for="a in alerts" :key="a.key" class="flex items-start justify-between gap-3">
            <div class="flex items-start gap-3">
              <div :class="`pill-${a.tone}`" class="!rounded-lg !p-2 shrink-0">
                <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="6"/></svg>
              </div>
              <div>
                <div class="text-sm font-medium text-surface-800">{{ a.title }}</div>
                <div class="text-xs text-surface-500">{{ a.sub }}</div>
              </div>
            </div>
            <span :class="`pill-${a.tone}`">{{ a.count }}</span>
          </li>
        </ul>
        <div v-else class="text-sm text-surface-400 py-4 text-center">No alerts</div>
      </div>

      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-surface-800">Analyzer Status</h3>
        </div>
        <ul v-if="analyzers.length" class="space-y-3">
          <li v-for="a in analyzers" :key="a.name" class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <span class="w-2 h-2 rounded-full" :class="a.status === 'Online' || a.status === 'In Use' ? 'bg-status-success' : 'bg-status-warning'" />
              <span class="text-sm text-surface-700">{{ a.name }}</span>
            </div>
            <StatusPill :status="a.status" />
          </li>
        </ul>
        <div v-else class="text-sm text-surface-400 py-4 text-center">No analyzers configured</div>
      </div>

      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold text-surface-800">Branch Performance <span class="text-surface-400 text-xs">(Today)</span></h3>
        </div>
        <div class="grid grid-cols-2 gap-3 text-center">
          <div>
            <div class="text-xs text-surface-500">Samples Processed</div>
            <div class="text-xl font-semibold text-surface-800">{{ branch.samples_processed }}</div>
          </div>
          <div>
            <div class="text-xs text-surface-500">Avg TAT</div>
            <div class="text-xl font-semibold text-surface-800">{{ formatTat(branch.avg_tat_minutes) }}</div>
          </div>
          <div>
            <div class="text-xs text-surface-500">Reports Released</div>
            <div class="text-xl font-semibold text-surface-800">{{ branch.reports_released }}</div>
          </div>
          <div>
            <div class="text-xs text-surface-500">Rejection Rate</div>
            <div class="text-xl font-semibold text-surface-800">{{ branch.rejection_rate_pct }}%</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
