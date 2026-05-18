<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { billingApi, ordersApi, type InvoiceRow, type OrderRow } from '@/api/adms'
import { call } from '@/api/client'

const router = useRouter()
const rows = ref<InvoiceRow[]>([])
const summary = ref<{ draft: { count: number; total: number }; unpaid: { count: number; total: number }; paid: { count: number; total: number } } | null>(null)
const unbilledOrders = ref<OrderRow[]>([])
const loading = ref(false)
const busyOrder = ref<string | null>(null)
const error = ref('')

async function load() {
  loading.value = true
  try {
    rows.value = await billingApi.queue()
    summary.value = await billingApi.summary()
    // Pull submitted orders so the user can spin invoices for them.
    const all = await ordersApi.worklist('active-Request Status', undefined, 200)
    unbilledOrders.value = all
  } catch { /* keep last good state */ }
  finally { loading.value = false }
}
onMounted(load)

const totals = computed(() => ({
  draft: summary.value?.draft || { count: 0, total: 0 },
  unpaid: summary.value?.unpaid || { count: 0, total: 0 },
  paid: summary.value?.paid || { count: 0, total: 0 },
}))

async function createInvoiceFor(orderName: string, submit: 0 | 1) {
  busyOrder.value = orderName
  error.value = ''
  try {
    const r = await call<{ ok: boolean; name: string; existing?: boolean }>(
      'diagnostic_management.api.billing.create_invoice_for_order',
      { service_request: orderName, submit },
    )
    if (r.existing) {
      // Jump straight to the existing invoice rather than creating a duplicate.
      router.push(`/billing/${r.name}`)
    } else {
      await load()
      router.push(`/billing/${r.name}`)
    }
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to create invoice'
  } finally { busyOrder.value = null }
}
</script>

<template>
  <Topbar title="Billing Queue" />

  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Draft Invoices" :value="totals.draft.count" :sub="totals.draft.total.toLocaleString() + ' total'" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Outstanding" :value="totals.unpaid.count" :sub="totals.unpaid.total.toLocaleString() + ' owed'" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Paid" :value="totals.paid.count" :sub="totals.paid.total.toLocaleString() + ' collected'" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Orders to Bill" :value="unbilledOrders.length" sub="Active service requests" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
  </div>

  <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg mb-3">{{ error }}</p>

  <div class="card p-1 mb-4 overflow-x-auto">
    <div class="px-4 py-3 border-b border-surface-100 text-sm font-semibold text-surface-800">Invoices</div>
    <table class="w-full text-sm">
      <thead><tr class="border-b border-surface-200 text-left text-surface-500">
        <th class="px-3 py-3">Invoice</th>
        <th class="px-3 py-3">Customer</th>
        <th class="px-3 py-3 text-right">Amount</th>
        <th class="px-3 py-3 text-right">Outstanding</th>
        <th class="px-3 py-3">Posted</th>
        <th class="px-3 py-3">Status</th>
        <th class="px-3 py-3 text-right">Actions</th>
      </tr></thead>
      <tbody>
        <tr v-if="!rows.length"><td colspan="7" class="text-center text-surface-400 py-8">{{ loading ? 'Loading…' : 'No invoices yet — create one from an order below.' }}</td></tr>
        <tr v-for="r in rows" :key="r.name" class="border-b border-surface-100 hover:bg-surface-50 cursor-pointer" @click="router.push(`/billing/${r.name}`)">
          <td class="px-3 py-3 text-brand-teal-600 font-medium">{{ r.name }}</td>
          <td class="px-3 py-3">{{ r.customer_name || r.customer }}</td>
          <td class="px-3 py-3 text-right">{{ r.grand_total?.toLocaleString() }}</td>
          <td class="px-3 py-3 text-right" :class="(r.outstanding_amount || 0) > 0 ? 'text-status-warning' : 'text-surface-400'">
            {{ r.outstanding_amount?.toLocaleString() || '—' }}
          </td>
          <td class="px-3 py-3">{{ r.posting_date }}</td>
          <td class="px-3 py-3"><StatusPill :status="r.status" /></td>
          <td class="px-3 py-3 text-right text-xs" @click.stop>
            <button class="text-brand-teal-600 hover:underline" @click="router.push(`/billing/${r.name}`)">View</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="card p-1 overflow-x-auto">
    <div class="px-4 py-3 border-b border-surface-100 text-sm font-semibold text-surface-800">Orders Awaiting Billing</div>
    <table class="w-full text-sm">
      <thead><tr class="border-b border-surface-200 text-left text-surface-500">
        <th class="px-3 py-3">Order</th>
        <th class="px-3 py-3">Patient</th>
        <th class="px-3 py-3">Subject</th>
        <th class="px-3 py-3">Status</th>
        <th class="px-3 py-3 text-right">Actions</th>
      </tr></thead>
      <tbody>
        <tr v-if="!unbilledOrders.length"><td colspan="5" class="text-center text-surface-400 py-8">No active orders.</td></tr>
        <tr v-for="o in unbilledOrders" :key="o.name" class="border-b border-surface-100 hover:bg-surface-50">
          <td class="px-3 py-3 text-brand-teal-600 font-medium cursor-pointer" @click="router.push(`/orders/${o.name}`)">{{ o.name }}</td>
          <td class="px-3 py-3">{{ o.patient_name }}</td>
          <td class="px-3 py-3">{{ o.title || o.template_dn || '—' }}</td>
          <td class="px-3 py-3"><StatusPill :status="(o.status || '').replace('-Request Status','')" /></td>
          <td class="px-3 py-3 text-right text-xs">
            <button class="text-brand-teal-600 hover:underline mr-3" :disabled="busyOrder === o.name" @click="createInvoiceFor(o.name, 0)">Create Draft Invoice</button>
            <button class="text-brand-teal-600 hover:underline" :disabled="busyOrder === o.name" @click="createInvoiceFor(o.name, 1)">Create &amp; Submit</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
