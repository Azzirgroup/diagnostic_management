<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { radiologyApi, instrumentsApi, type RadDashboard, type OrderRow, type LabInstrumentRow } from '@/api/adms'

const dashboard = ref<RadDashboard>({ pending_studies: 0, pending_pre_auth: 0, approved_pre_auth: 0, reports_pending: 0, critical: 0 })
const studies = ref<OrderRow[]>([])
const modalityInstruments = ref<LabInstrumentRow[]>([])

onMounted(async () => {
  try { dashboard.value = await radiologyApi.dashboard() } catch { /* keep zeros */ }
  try { studies.value = await radiologyApi.readingWorklist({ limit: 20 }) } catch { studies.value = [] }
  try { modalityInstruments.value = await instrumentsApi.list('Radiology') } catch { modalityInstruments.value = [] }
})
</script>

<template>
  <Topbar title="Radiology Manager Dashboard" />
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <KpiCard label="Pending Studies" :value="dashboard.pending_studies" sub="Awaiting read" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Reports Pending" :value="dashboard.reports_pending" sub="Verification queue" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Critical Findings" :value="dashboard.critical" sub="Unacknowledged" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Pre-Auth Pending" :value="dashboard.pending_pre_auth" sub="Insurance review" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Today's Studies Worklist</h3>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Order ID</th><th>Patient</th><th>Modality</th><th>Priority</th><th>Status</th>
          </tr></thead>
          <tbody>
            <tr v-for="s in studies" :key="s.name" class="border-b border-surface-100">
              <td class="py-2">{{ s.name }}</td>
              <td>{{ s.patient_name }}</td>
              <td>{{ (s as any).imaging_modality || '—' }}</td>
              <td><StatusPill :status="s.priority || 'Routine'"/></td>
              <td><StatusPill :status="s.status" /></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!studies.length" class="text-sm text-surface-400 mt-3">No studies</p>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Modality Status</h3>
        <ul v-if="modalityInstruments.length" class="space-y-2 text-sm">
          <li v-for="m in modalityInstruments" :key="m.name" class="flex justify-between">
            <span>{{ m.instrument_name }}</span>
            <StatusPill :status="m.state" />
          </li>
        </ul>
        <p v-else class="text-sm text-surface-400">No instruments configured</p>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Pre-Auth Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Pending</dt><dd>{{ dashboard.pending_pre_auth }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Approved</dt><dd>{{ dashboard.approved_pre_auth }}</dd></div>
        </dl>
      </div>
    </div>
  </div>
</template>
