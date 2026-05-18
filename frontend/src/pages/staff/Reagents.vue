<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { reagentsApi, type ReagentLot } from '@/api/adms'

const allLots = ref<ReagentLot[]>([])
const lowStock = ref<ReagentLot[]>([])
const expiring = ref<ReagentLot[]>([])
const selected = ref<ReagentLot | null>(null)
const tab = ref<'all' | 'low' | 'expiring' | 'archived'>('all')
const usageAmount = ref<number | null>(null)
const busy = ref(false)

async function load() {
  try { allLots.value = await reagentsApi.listLots() } catch { allLots.value = [] }
  try { lowStock.value = await reagentsApi.lowStock(20) } catch { lowStock.value = [] }
  try { expiring.value = await reagentsApi.expiringSoon(30) } catch { expiring.value = [] }
}

onMounted(load)

const archivedLots = computed(() => allLots.value.filter((l) => l.status === 'Depleted' || l.status === 'Expired'))
const activeLots = computed(() => allLots.value.filter((l) => l.status !== 'Depleted' && l.status !== 'Expired'))

const visible = computed<ReagentLot[]>(() => {
  switch (tab.value) {
    case 'low': return lowStock.value
    case 'expiring': return expiring.value
    case 'archived': return archivedLots.value
    default: return activeLots.value
  }
})

const kpis = computed(() => ({
  low: lowStock.value.length,
  expiring: expiring.value.length,
  out: allLots.value.filter((l) => l.status === 'Depleted').length,
  active: activeLots.value.length,
}))

async function logUsage() {
  if (!selected.value || !usageAmount.value || usageAmount.value <= 0) return
  busy.value = true
  try {
    await reagentsApi.logUsage(selected.value.name, Number(usageAmount.value))
    usageAmount.value = null
    await load()
    selected.value = allLots.value.find((l) => l.name === selected.value?.name) || null
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Reagents" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Low Stock" :value="kpis.low" sub="Below 20% on hand" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Expiring Soon" :value="kpis.expiring" sub="Within 30 days" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Out of Stock" :value="kpis.out" sub="Depleted lots" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Active Lots" :value="kpis.active" sub="Across all sections" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-2 border-b border-surface-100">
        <button v-for="(label, key) in { all: 'Active', low: 'Low Stock', expiring: 'Expiring', archived: 'Archived' }" :key="key"
          :class="['btn-ghost !py-1.5 !text-xs', tab === key && '!bg-brand-navy-700 !text-white !border-transparent']"
          @click="tab = key as any">
          {{ label }}
        </button>
      </div>
      <DataTable
        :rows="visible"
        row-key="name"
        :selectable="true"
        empty-text="No reagent lots"
        @select="(r) => (selected = r as any)"
        :columns="[
          { key: 'name', label: 'Lot ID' },
          { key: 'reagent_item', label: 'Reagent' },
          { key: 'section', label: 'Section' },
          { key: 'quantity_on_hand', label: 'On Hand' },
          { key: 'expiry_date', label: 'Expiry' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-name="{ value }">
          <button class="text-brand-teal-600 hover:underline" @click.stop="$router.push(`/lab/reagent/${value}`)">{{ value }}</button>
        </template>
        <template #cell-quantity_on_hand="{ row }">
          {{ row.quantity_on_hand ?? 0 }} {{ row.unit || '' }}
        </template>
        <template #cell-status="{ value }">
          <StatusPill :status="(value as string) || 'Active'" />
        </template>
      </DataTable>
    </div>

    <div>
      <DetailPane v-if="selected" :title="selected.lot_number" :subtitle="selected.reagent_item" @close="selected = null">
        <dl class="text-sm space-y-3">
          <div class="flex justify-between"><dt class="text-surface-500">Section</dt><dd>{{ selected.section || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Manufacturer</dt><dd>{{ selected.manufacturer || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Received</dt><dd>{{ selected.received_date || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Expiry</dt><dd>{{ selected.expiry_date || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">On Hand</dt><dd>{{ selected.quantity_on_hand ?? 0 }} {{ selected.unit || '' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Storage</dt><dd>{{ selected.storage_location || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
        </dl>
        <div class="mt-6 space-y-2">
          <label class="text-xs text-surface-500">Log Usage (decrement on-hand)</label>
          <div class="flex gap-2">
            <input v-model.number="usageAmount" type="number" min="0" step="0.1" placeholder="0.0"
              class="flex-1 px-3 py-2 rounded border border-surface-200 text-sm" />
            <button class="btn-primary !py-2 !px-3 text-sm" :disabled="busy || !usageAmount" @click="logUsage">Log</button>
          </div>
        </div>
      </DetailPane>
      <div v-else class="card p-6 text-center text-surface-400">Select a lot to view details and log usage</div>
    </div>
  </div>
</template>
