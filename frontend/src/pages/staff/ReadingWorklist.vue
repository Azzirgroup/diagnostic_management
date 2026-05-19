<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { radiologyApi, type OrderRow, type RadDashboard } from '@/api/adms'

const router = useRouter()
const rows = ref<OrderRow[]>([])
const dashboard = ref<RadDashboard>({ pending_studies: 0, pending_pre_auth: 0, approved_pre_auth: 0, reports_pending: 0, critical: 0 })
const selected = ref<OrderRow | null>(null)

async function load() {
  try { rows.value = await radiologyApi.readingWorklist({ limit: 200 }) } catch { rows.value = [] }
  try { dashboard.value = await radiologyApi.dashboard() } catch { /* keep zeros */ }
}
onMounted(load)

const urgent = computed(() => rows.value.filter((r) => r.priority === 'Stat' || r.priority === 'Urgent').length)
</script>

<template>
  <Topbar title="Reading Worklist" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Unread Studies" :value="dashboard.pending_studies" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Urgent / Stat" :value="urgent" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Reports Pending" :value="dashboard.reports_pending" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Critical Findings" :value="dashboard.critical" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" row-key="name" :selectable="true" @select="(r) => (selected = r as any)"
        empty-text="No imaging orders pending"
        :columns="[
          { key: 'name', label: 'Order ID' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'imaging_modality', label: 'Modality' },
          { key: 'imaging_body_part', label: 'Body Part' },
          { key: 'practitioner', label: 'Referring Doctor' },
          { key: 'creation', label: 'Received' },
          { key: 'priority', label: 'Priority' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-priority="{ value }"><StatusPill :status="(value as string) || 'Routine'"/></template>
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.patient_name || selected.name" :subtitle="`${(selected as any).imaging_modality || ''} · ${(selected as any).imaging_body_part || ''}`" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Order ID</dt><dd>{{ selected.name }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Received</dt><dd>{{ selected.creation?.split('.')[0] || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Referring Doctor</dt><dd>{{ selected.practitioner || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Priority</dt><dd><StatusPill :status="(selected.priority || 'Routine')"/></dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status"/></dd></div>
      </dl>
      <button class="btn-primary w-full mt-6" @click="router.push(`/radiology/viewer/${selected.name}`)">Open Viewer</button>
      <button class="btn-secondary w-full mt-2" @click="router.push(`/radiology/report/${selected.name}`)">Start Report</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a study</div>
  </div>
</template>
