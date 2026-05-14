<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'

const selected = ref<any>(null)
const rows = ref<any[]>([])

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    rows.value = []
  } catch {
    rows.value = []
  }
})
</script>

<template>
  <Topbar title="Pre-Auth Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Awaiting Submission" :value="0" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Pending Approval" :value="0" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Approved Today" :value="0" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Expiring Soon" :value="0" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" :selectable="true" @select="(r) => (selected = r)" empty-text="No data"
        :columns="[
          { key: 'id', label: 'Request ID' },
          { key: 'patient', label: 'Patient' },
          { key: 'payor', label: 'Payor' },
          { key: 'test', label: 'Requested Test Package' },
          { key: 'urgency', label: 'Clinical Urgency' },
          { key: 'submitted', label: 'Submitted Date' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.id" :subtitle="selected.patient" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Payor</dt><dd>{{ selected.payor }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Service</dt><dd>{{ selected.test }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status"/></dd></div>
      </dl>
      <button class="btn-primary w-full mt-6">Submit</button>
      <button class="btn-secondary w-full mt-2">Follow Up</button>
      <button class="btn-ghost w-full mt-2">Mark Approved</button>
      <button class="btn-danger-ghost w-full mt-2">Mark Denied</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a pre-auth request</div>
  </div>
</template>
