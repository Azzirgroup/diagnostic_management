<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { call } from '@/api/client'
import { doctorApi, type DiagnosticReportRow, type PatientLite } from '@/api/adms'
import StatusPill from '@/components/ui/StatusPill.vue'

const router = useRouter()
const kpis = ref({ pending_results: 0, recent_patients: 0, new_orders: 0, unpaid_amount: 0 })
const recentResults = ref<DiagnosticReportRow[]>([])
const recentPatients = ref<PatientLite[]>([])

async function load() {
  try {
    const d = await call<typeof kpis.value>('diagnostic_management.api.dashboard.doctor')
    if (d) kpis.value = d
  } catch { /* keep zeros */ }

  try { recentResults.value = (await doctorApi.resultsInbox(undefined, 5)) || [] } catch { recentResults.value = [] }
  try { recentPatients.value = (await doctorApi.myPatients(5)) || [] } catch { recentPatients.value = [] }
}
onMounted(load)
</script>

<template>
  <Topbar title="Doctor Dashboard" />
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <div class="card p-5">
      <div class="w-10 h-10 rounded-lg bg-brand-teal-50 text-brand-teal-700 flex items-center justify-center mb-3">📄</div>
      <div class="text-sm text-surface-500">Pending Results</div>
      <div class="text-2xl font-semibold text-surface-800">{{ kpis.pending_results }}</div>
      <RouterLink to="/results" class="text-sm text-brand-teal-600 hover:underline mt-2 inline-block">View inbox →</RouterLink>
    </div>
    <div class="card p-5">
      <div class="w-10 h-10 rounded-lg bg-brand-teal-50 text-brand-teal-700 flex items-center justify-center mb-3">👥</div>
      <div class="text-sm text-surface-500">Recent Patients</div>
      <div class="text-2xl font-semibold text-surface-800">{{ kpis.recent_patients }}</div>
      <RouterLink to="/patients" class="text-sm text-brand-teal-600 hover:underline mt-2 inline-block">View patients →</RouterLink>
    </div>
    <div class="card p-5">
      <div class="w-10 h-10 rounded-lg bg-brand-teal-50 text-brand-teal-700 flex items-center justify-center mb-3">📋</div>
      <div class="text-sm text-surface-500">New Orders</div>
      <div class="text-2xl font-semibold text-surface-800">{{ kpis.new_orders }}</div>
      <RouterLink to="/orders" class="text-sm text-brand-teal-600 hover:underline mt-2 inline-block">View orders →</RouterLink>
    </div>
    <div class="card p-5">
      <div class="w-10 h-10 rounded-lg bg-status-danger-bg text-status-danger flex items-center justify-center mb-3">💳</div>
      <div class="text-sm text-surface-500">Unpaid Statements</div>
      <div class="text-2xl font-semibold text-surface-800">PKR {{ kpis.unpaid_amount.toLocaleString() }}</div>
      <RouterLink to="/statements" class="text-sm text-brand-teal-600 hover:underline mt-2 inline-block">View statements →</RouterLink>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4">
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Recent Results</h3>
        <RouterLink class="text-sm text-brand-teal-600 hover:underline" to="/results">View all</RouterLink>
      </div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200"><th class="py-2">Test</th><th>Patient</th><th>Date</th><th>Status</th></tr></thead>
        <tbody>
          <tr v-if="!recentResults.length"><td colspan="4" class="py-6 text-center text-surface-400">No results yet</td></tr>
          <tr v-for="r in recentResults" :key="r.name" class="border-b border-surface-100 cursor-pointer hover:bg-surface-50" @click="router.push(`/results/${r.name}`)">
            <td class="py-2">{{ r.docname || r.name }}</td>
            <td>{{ r.patient_name }}</td>
            <td>{{ r.creation?.split(' ')[0] }}</td>
            <td><StatusPill :status="r.status || 'Draft'" /></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Recent Patients</h3>
        <RouterLink class="text-sm text-brand-teal-600 hover:underline" to="/patients">View all</RouterLink>
      </div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200"><th class="py-2">Patient</th><th>Age / Gender</th><th>Last Visit</th></tr></thead>
        <tbody>
          <tr v-if="!recentPatients.length"><td colspan="3" class="py-6 text-center text-surface-400">No patients yet</td></tr>
          <tr v-for="p in recentPatients" :key="p.name" class="border-b border-surface-100 cursor-pointer hover:bg-surface-50" @click="router.push(`/patients/${p.name}`)">
            <td class="py-2">{{ p.patient_name }}</td>
            <td>{{ p.sex || '—' }}</td>
            <td>—</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
