<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { getList } from '@/api/client'

const orders = ref<any[]>([])
const loading = ref(false)
const router = useRouter()

async function load() {
  loading.value = true
  try {
    orders.value = await getList({
      doctype: 'Service Request',
      fields: ['name', 'patient', 'patient_name', 'status', 'priority', 'order_date', 'subject'],
      limit_page_length: 100,
      order_by: 'modified desc',
    })
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <Topbar title="Orders" />
  <div class="card p-1 mb-4">
    <DataTable
      :rows="orders"
      row-key="name"
      :empty-text="loading ? 'Loading…' : 'No orders'"
      :columns="[
        { key: 'name', label: 'Order ID' },
        { key: 'patient_name', label: 'Patient' },
        { key: 'subject', label: 'Subject' },
        { key: 'priority', label: 'Priority' },
        { key: 'order_date', label: 'Date' },
        { key: 'status', label: 'Status' },
      ]"
    >
      <template #cell-name="{ value }">
        <button class="text-brand-teal-600 hover:underline" @click="router.push(`/orders/${value}`)">{{ value }}</button>
      </template>
      <template #cell-priority="{ value }">
        <StatusPill :status="(value as string) || 'Routine'" />
      </template>
      <template #cell-status="{ value }">
        <StatusPill :status="(value as string) || '—'" />
      </template>
    </DataTable>
  </div>
  <div class="text-right">
    <button class="btn-primary" @click="router.push('/orders/new')">+ New Order</button>
  </div>
</template>
