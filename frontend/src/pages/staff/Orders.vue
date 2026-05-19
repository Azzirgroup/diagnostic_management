<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { ordersApi, type OrderRow } from '@/api/adms'

const orders = ref<OrderRow[]>([])
const loading = ref(false)
const router = useRouter()

async function load() {
  loading.value = true
  try {
    orders.value = await ordersApi.worklist(undefined, undefined, 200)
  } catch {
    orders.value = []
  } finally {
    loading.value = false
  }
}
onMounted(load)

// Marley v16 stores status / priority as Code Value document names like
// "draft-Request Status" or "Routine-Priority". Strip the suffix so the
// StatusPill shows a clean label.
function pretty(v?: string): string {
  if (!v) return ''
  return v.replace(/-Request Status$/i, '').replace(/-Priority$/i, '')
}

type OrderDisplay = OrderRow & {
  _pretty_status: string
  _pretty_priority: string
  _label: string
  _is_draft: boolean
}

const rows = computed<OrderDisplay[]>(() =>
  orders.value.map((o) => ({
    ...o,
    _pretty_status: pretty(o.status),
    _pretty_priority: pretty(o.priority),
    _label: o.title || o.subject || o.template_dn || o.name,
    // Service Request is submittable; docstatus 0 = draft, 1 = submitted.
    _is_draft: (o.docstatus ?? 0) === 0,
  })),
)
</script>

<template>
  <Topbar title="Orders" />
  <div class="card p-1 mb-4">
    <DataTable
      :rows="rows"
      row-key="name"
      :empty-text="loading ? 'Loading…' : 'No orders'"
      :columns="[
        { key: 'name', label: 'Order ID' },
        { key: 'patient_name', label: 'Patient' },
        { key: '_label', label: 'Subject' },
        { key: '_pretty_priority', label: 'Priority' },
        { key: 'occurrence_date', label: 'Date' },
        { key: '_pretty_status', label: 'Status' },
        { key: '_is_draft', label: 'Actions' },
      ]"
    >
      <template #cell-name="{ value }">
        <button class="text-brand-teal-600 hover:underline" @click="router.push(`/orders/${value}`)">{{ value }}</button>
      </template>
      <template #cell-_pretty_priority="{ value }">
        <StatusPill :status="(value as string) || 'Routine'" />
      </template>
      <template #cell-_pretty_status="{ value }">
        <StatusPill :status="(value as string) || '—'" />
      </template>
      <template #cell-_is_draft="{ row }">
        <div class="flex gap-2">
          <button class="text-xs text-brand-teal-600 hover:underline"
            @click="router.push(`/orders/${(row as OrderDisplay).name}`)">View</button>
          <button v-if="(row as OrderDisplay)._is_draft"
            class="text-xs text-brand-teal-600 hover:underline"
            @click="router.push(`/orders/${(row as OrderDisplay).name}/edit`)">Edit</button>
        </div>
      </template>
    </DataTable>
  </div>
  <div class="text-right">
    <button class="btn-primary" @click="router.push('/orders/new')">+ New Order</button>
  </div>
</template>
