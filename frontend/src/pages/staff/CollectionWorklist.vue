<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { getList } from '@/api/client'

const list = ref<any[]>([])
const loading = ref(false)
onMounted(async () => {
  loading.value = true
  try {
    list.value = await getList({
      doctype: 'Sample Collection',
      fields: ['name', 'patient', 'patient_name', 'sample', 'collected_time', 'status'],
      filters: { status: ['in', ['Draft', 'Collected']] },
      limit_page_length: 100,
      order_by: 'creation desc',
    })
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <Topbar title="Collection Worklist" subtitle="Open queue for phlebotomists across all branches" />
  <div class="card p-1">
    <DataTable
      :rows="list"
      row-key="name"
      :empty-text="loading ? 'Loading…' : 'No collection tasks'"
      :columns="[
        { key: 'name', label: 'Sample ID' },
        { key: 'patient_name', label: 'Patient' },
        { key: 'sample', label: 'Specimen' },
        { key: 'collected_time', label: 'Collected At' },
        { key: 'status', label: 'Status' },
      ]"
    >
      <template #cell-status="{ value }">
        <StatusPill :status="(value as string) || 'Draft'" />
      </template>
    </DataTable>
  </div>
</template>
