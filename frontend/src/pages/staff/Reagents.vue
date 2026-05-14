<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { getList } from '@/api/client'

interface Reagent {
  name: string
  item_name: string
  item_code: string
  description?: string
  stock_uom: string
  on_hand?: number
  status?: string
  expiry?: string
}

const reagents = ref<Reagent[]>([])
const selected = ref<Reagent | null>(null)
const tab = ref<'all' | 'low' | 'expiring' | 'archived'>('all')

onMounted(async () => {
  // Reagents are modelled as Item with `is_stock_item = 1` and a Healthcare-related item group.
  reagents.value = await getList<Reagent>({
    doctype: 'Item',
    fields: ['name', 'item_name', 'item_code', 'description', 'stock_uom'],
    filters: { is_stock_item: 1, disabled: 0 },
    limit_page_length: 40,
    order_by: 'modified desc',
  })
})
</script>

<template>
  <Topbar title="Reagents" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Low Stock" :value="12" delta="3 vs yesterday" delta-direction="down" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Expiring Soon" :value="8" delta="2 vs yesterday" delta-direction="up" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Out of Stock" :value="3" sub="No change" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Active Lots" :value="156" delta="10 vs yesterday" delta-direction="up" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-2 border-b border-surface-100">
        <button v-for="(label, key) in { all: 'All', low: 'Low Stock', expiring: 'Expiring', archived: 'Archived' }" :key="key"
          :class="['btn-ghost !py-1.5 !text-xs', tab === key && '!bg-brand-navy-700 !text-white !border-transparent']"
          @click="tab = key as any">
          {{ label }}
        </button>
      </div>
      <DataTable
        :rows="reagents"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r as any)"
        :columns="[
          { key: 'item_name', label: 'Reagent' },
          { key: 'item_code', label: 'Lot / Batch' },
          { key: 'description', label: 'Analyzer / Section' },
          { key: 'stock_uom', label: 'On Hand' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }">
          <StatusPill :status="(value as string) || 'In Stock'" />
        </template>
      </DataTable>
    </div>

    <div>
      <DetailPane v-if="selected" :title="selected.item_name" :subtitle="selected.item_code" @close="selected = null">
        <dl class="text-sm space-y-3">
          <div class="flex justify-between"><dt class="text-surface-500">Unit</dt><dd>{{ selected.stock_uom }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">On Hand</dt><dd>12 L</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill status="Low Stock" /></dd></div>
        </dl>
        <button class="btn-primary w-full mt-6">Receive Stock</button>
        <button class="btn-ghost w-full mt-2">Create Purchase Request</button>
      </DetailPane>
      <div v-else class="card p-6 text-center text-surface-400">Select a reagent</div>
    </div>
  </div>
</template>
