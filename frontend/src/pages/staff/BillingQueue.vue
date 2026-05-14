<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { getList } from '@/api/client'

const rows = ref<any[]>([])
const selected = ref<any>(null)
onMounted(async () => {
  rows.value = await getList({
    doctype: 'Sales Invoice',
    fields: ['name', 'customer', 'customer_name', 'patient_name', 'grand_total', 'status', 'posting_date'],
    limit_page_length: 30,
    order_by: 'modified desc',
  })
})
</script>

<template>
  <Topbar title="Billing Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Ready to Bill" :value="34" delta="6 vs yesterday" delta-direction="up" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Pending Review" :value="18" delta="3 vs yesterday" delta-direction="up" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Insurance Split" :value="12" sub="No change" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Revenue Today" :value="'PKR 1,248,560'" delta="12% vs yesterday" delta-direction="up" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" row-key="name" :selectable="true" @select="(r) => (selected = r)"
        empty-text="No invoices yet"
        :columns="[
          { key: 'name', label: 'Invoice' },
          { key: 'customer_name', label: 'Customer' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'grand_total', label: 'Amount' },
          { key: 'posting_date', label: 'Posted' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.customer_name" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Patient</dt><dd>{{ selected.patient_name || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Amount</dt><dd>{{ selected.grand_total }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status"/></dd></div>
      </dl>
      <button class="btn-primary w-full mt-6">Create Invoice</button>
      <button class="btn-secondary w-full mt-2">Send to Insurance</button>
      <button class="btn-ghost w-full mt-2">Hold</button>
      <button class="btn-danger-ghost w-full mt-2">View Sales Invoice</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select an invoice</div>
  </div>
</template>
