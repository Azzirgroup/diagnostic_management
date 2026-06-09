<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { billingApi, ordersApi, stockAlertsApi, type InvoiceRow, type OrderRow, type StockAlertRow, type StockAlertSummary } from '@/api/adms'
import { call } from '@/api/client'

const router = useRouter()
const rows = ref<InvoiceRow[]>([])
const summary = ref<{ draft: { count: number; total: number }; unpaid: { count: number; total: number }; paid: { count: number; total: number } } | null>(null)
const unbilledOrders = ref<OrderRow[]>([])
const loading = ref(false)
const busyOrder = ref<string | null>(null)
const error = ref('')

// Stock Alerts surface — populated when a Sample → Tested can't fully consume
// the BOM raw materials from the source warehouse. Shown right at the top of
// the Billing screen so a billing officer can chase restock before issuing
// more invoices for the same item.
const stockAlerts = ref<StockAlertRow[]>([])
const stockAlertSummary = ref<StockAlertSummary | null>(null)
const busyAlert = ref<string | null>(null)

// Active shift banner — show the cashier their open shift inline so it's
// obvious every invoice they take will be reconciled at close.
const activeShift = ref<{ name: string; pos_profile?: string; company?: string; period_start_date?: string } | null>(null)
const shiftRequired = ref(false)
async function loadActiveShift() {
  try {
    const r = await call<{ required: boolean; has_shift: boolean; active: any }>(
      'diagnostic_management.api.shifts.shift_required_for_billing', {})
    activeShift.value = r.active || null
    shiftRequired.value = !!r.required
  } catch { activeShift.value = null; shiftRequired.value = false }
}
// Cashiers + receptionists can't post invoices without an open shift; admins
// and back-office roles bypass this.
const blockBilling = computed(() => shiftRequired.value && !activeShift.value)

async function loadStockAlerts() {
  try {
    const [a, s] = await Promise.all([stockAlertsApi.list({ limit: 20 }), stockAlertsApi.summary()])
    stockAlerts.value = a
    stockAlertSummary.value = s
  } catch { /* keep last good state */ }
}
async function ackAlert(name: string) {
  busyAlert.value = name
  try { await stockAlertsApi.acknowledge(name); await loadStockAlerts() }
  catch (e: any) { error.value = e?.response?.data?.message || 'Failed to acknowledge alert' }
  finally { busyAlert.value = null }
}
async function resolveAlert(name: string) {
  busyAlert.value = name
  try { await stockAlertsApi.resolve(name); await loadStockAlerts() }
  catch (e: any) { error.value = e?.response?.data?.message || 'Failed to resolve alert' }
  finally { busyAlert.value = null }
}
function severityClass(s: string) {
  return s === 'Critical' ? 'bg-red-200 text-red-900 font-bold'
    : s === 'High' ? 'bg-red-100 text-red-700'
    : s === 'Medium' ? 'bg-amber-100 text-amber-700'
    : 'bg-surface-100 text-surface-600'
}

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
onMounted(async () => { await Promise.all([load(), loadStockAlerts(), loadActiveShift()]) })

const totals = computed(() => ({
  draft: summary.value?.draft || { count: 0, total: 0 },
  unpaid: summary.value?.unpaid || { count: 0, total: 0 },
  paid: summary.value?.paid || { count: 0, total: 0 },
}))

async function createInvoiceFor(orderName: string, submit: 0 | 1) {
  if (blockBilling.value) {
    error.value = 'No active shift. Open a shift first from the Shifts screen.'
    return
  }
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

  <!-- Active shift banner: tells the cashier their open POS Opening Entry,
       so every invoice posted from here automatically rolls into close. -->
  <div v-if="activeShift" class="card mb-4 px-4 py-3 flex items-center justify-between gap-3 flex-wrap border-l-4 border-emerald-500">
    <div class="text-sm">
      <span class="font-semibold text-emerald-700">Shift open</span>
      <span class="text-surface-500 ml-2">{{ activeShift.pos_profile }}</span>
      <span class="text-xs text-surface-400 ml-2">since {{ activeShift.period_start_date }}</span>
    </div>
    <button class="text-xs text-brand-teal-600 hover:underline" @click="router.push('/shift')">Open shift desk</button>
  </div>
  <div v-else :class="['card mb-4 px-4 py-3 flex items-center justify-between gap-3 flex-wrap border-l-4', blockBilling ? 'border-red-500' : 'border-amber-400']">
    <div class="text-sm">
      <span :class="['font-semibold', blockBilling ? 'text-red-700' : 'text-amber-700']">
        {{ blockBilling ? 'No active shift — invoices are blocked' : 'No active shift' }}
      </span>
      <span class="text-surface-500 ml-2">
        {{ blockBilling
          ? 'Open a shift before raising invoices, so end-of-shift reconciliation can pick them up.'
          : "Invoices won't be tied to a shift reconciliation until you open one." }}
      </span>
    </div>
    <button class="text-xs text-brand-teal-600 hover:underline" @click="router.push('/shift')">Open a shift →</button>
  </div>

  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Draft Invoices" :value="totals.draft.count" :sub="totals.draft.total.toLocaleString() + ' total'" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Outstanding" :value="totals.unpaid.count" :sub="totals.unpaid.total.toLocaleString() + ' owed'" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Paid" :value="totals.paid.count" :sub="totals.paid.total.toLocaleString() + ' collected'" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Orders to Bill" :value="unbilledOrders.length" sub="Active service requests" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
  </div>

  <!-- Stock alerts: surfaced when the Sample → Tested transition consumed
       material from a warehouse that didn't have enough on hand. The Material
       Issue is still submitted (consumption is recorded), but the bench needs
       to know about the shortfall and chase a restock. -->
  <div v-if="stockAlerts.length" class="card mb-4 border-l-4 border-red-500">
    <div class="px-4 py-3 border-b border-surface-100 flex items-center justify-between flex-wrap gap-2">
      <div>
        <span class="text-sm font-semibold text-surface-800">Stock Alerts</span>
        <span class="text-xs text-surface-500 ml-2">
          {{ stockAlertSummary?.open ?? 0 }} open
          <span v-if="stockAlertSummary?.critical">· {{ stockAlertSummary.critical }} critical</span>
          <span v-if="stockAlertSummary?.acknowledged">· {{ stockAlertSummary.acknowledged }} acknowledged</span>
        </span>
      </div>
      <button class="text-xs text-brand-teal-600 hover:underline" @click="loadStockAlerts">Refresh</button>
    </div>
    <div class="overflow-x-auto">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-surface-200 text-left text-surface-500">
            <th class="px-3 py-2">Severity</th>
            <th class="px-3 py-2">Item</th>
            <th class="px-3 py-2">Warehouse</th>
            <th class="px-3 py-2 text-right">Required</th>
            <th class="px-3 py-2 text-right">Available</th>
            <th class="px-3 py-2 text-right">Shortage</th>
            <th class="px-3 py-2">SI</th>
            <th class="px-3 py-2">Sample</th>
            <th class="px-3 py-2">When</th>
            <th class="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in stockAlerts" :key="a.name" class="border-b border-surface-100 hover:bg-surface-50">
            <td class="px-3 py-2">
              <span :class="['text-xs px-1.5 py-0.5 rounded', severityClass(a.severity)]">{{ a.severity }}</span>
              <span v-if="a.status === 'Acknowledged'" class="ml-1 text-xs text-amber-700">ack</span>
            </td>
            <td class="px-3 py-2">
              <div class="font-medium">{{ a.item_name || a.item_code }}</div>
              <div class="text-xs text-surface-400">{{ a.item_code }}</div>
            </td>
            <td class="px-3 py-2 text-xs">{{ a.warehouse || '—' }}</td>
            <td class="px-3 py-2 text-right">{{ a.required_qty }}</td>
            <td class="px-3 py-2 text-right" :class="a.available_qty <= 0 ? 'text-red-700' : ''">{{ a.available_qty }}</td>
            <td class="px-3 py-2 text-right font-semibold text-red-700">{{ a.shortage_qty }}</td>
            <td class="px-3 py-2 text-xs">
              <button v-if="a.sales_invoice" class="text-brand-teal-600 hover:underline" @click="router.push(`/billing/${a.sales_invoice}`)">{{ a.sales_invoice }}</button>
              <span v-else>—</span>
            </td>
            <td class="px-3 py-2 text-xs">{{ a.sample_collection || '—' }}</td>
            <td class="px-3 py-2 text-xs text-surface-500">{{ a.alert_date }}</td>
            <td class="px-3 py-2 text-right text-xs whitespace-nowrap">
              <button v-if="a.status === 'Open'" class="text-amber-700 hover:underline mr-2" :disabled="busyAlert === a.name" @click="ackAlert(a.name)">Acknowledge</button>
              <button class="text-emerald-700 hover:underline" :disabled="busyAlert === a.name" @click="resolveAlert(a.name)">Resolve</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
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
            <button class="text-brand-teal-600 hover:underline mr-3 disabled:text-surface-400 disabled:no-underline disabled:cursor-not-allowed"
              :disabled="busyOrder === o.name || blockBilling"
              :title="blockBilling ? 'Open a shift first' : 'Create Draft Invoice'"
              @click="createInvoiceFor(o.name, 0)">Create Draft Invoice</button>
            <button class="text-brand-teal-600 hover:underline disabled:text-surface-400 disabled:no-underline disabled:cursor-not-allowed"
              :disabled="busyOrder === o.name || blockBilling"
              :title="blockBilling ? 'Open a shift first' : 'Create & Submit'"
              @click="createInvoiceFor(o.name, 1)">Create &amp; Submit</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
