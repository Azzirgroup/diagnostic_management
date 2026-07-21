<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { call } from '@/api/client'

interface InvoiceLine { item_code: string; item_name: string; description?: string; qty: number; rate: number; amount: number; uom?: string }
interface InvoiceDetail {
  name: string
  customer: string
  customer_name?: string
  patient?: string
  patient_name?: string
  status: string
  docstatus: number
  grand_total: number
  outstanding_amount: number
  total_taxes_and_charges?: number
  posting_date: string
  due_date?: string
  currency: string
  custom_doctor?: string
  items_list: InvoiceLine[]
  payments?: Array<{ parent: string; allocated_amount: number; outstanding_amount: number }>
}

const route = useRoute()
const router = useRouter()
const invoice = ref<InvoiceDetail | null>(null)
const loading = ref(false)
const paymentAmount = ref<number | null>(null)
const paymentMode = ref('Cash')
// Dynamic Modes of Payment from ERPNext (Cash / Bank / M-Pesa / etc.) —
// mirrors what the workflow's BillingStep uses so both entry points
// stay in sync with the site's actual configured modes.
const modesOfPayment = ref<string[]>([])
const busy = ref(false)
const error = ref('')
const message = ref('')

async function load() {
  loading.value = true
  try {
    invoice.value = await call<InvoiceDetail>('diagnostic_management.api.billing.detail', { name: route.params.name as string })
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to load invoice'
  } finally { loading.value = false }
}

async function loadModesOfPayment() {
  try {
    const modes = await call<string[]>('diagnostic_management.api.billing_workflow.get_modes_of_payment')
    modesOfPayment.value = Array.isArray(modes) && modes.length ? modes : ['Cash']
    // Default to the first mode if the current selection isn't in the list
    // (e.g. site has no Cash mode configured, only M-Pesa + Bank).
    if (!modesOfPayment.value.includes(paymentMode.value)) {
      paymentMode.value = modesOfPayment.value[0]
    }
  } catch {
    modesOfPayment.value = ['Cash']  // safe fallback
  }
}

onMounted(() => {
  load()
  loadModesOfPayment()
})

const isDraft = computed(() => invoice.value?.docstatus === 0)
const isOutstanding = computed(() => invoice.value && invoice.value.docstatus === 1 && (invoice.value.outstanding_amount || 0) > 0)

// Referring Doctor — editable even after the invoice is submitted, thanks
// to the `allow_on_submit` Property Setter installed by
// setup._allow_doctor_after_submit. Saves via a dedicated endpoint that
// uses db.set_value so we don't have to cancel/amend the SI.
const doctorEditing = ref(false)
const doctorDraft = ref('')
const doctorSaving = ref(false)
const doctorMessage = ref('')

function startEditDoctor() {
  doctorDraft.value = invoice.value?.custom_doctor || ''
  doctorMessage.value = ''
  doctorEditing.value = true
}
async function saveDoctor() {
  if (!invoice.value) return
  doctorSaving.value = true; doctorMessage.value = ''; error.value = ''
  try {
    await call<{ ok: boolean; custom_doctor?: string }>(
      'diagnostic_management.api.billing.set_invoice_doctor',
      { invoice: invoice.value.name, doctor: doctorDraft.value.trim() || null },
    )
    doctorMessage.value = 'Doctor updated.'
    doctorEditing.value = false
    await load()
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to update doctor'
  } finally { doctorSaving.value = false }
}

async function recordPayment() {
  if (!invoice.value || !paymentAmount.value || paymentAmount.value <= 0) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const r = await call<{ ok: boolean; payment_entry: string; allocated: number }>(
      'diagnostic_management.api.billing.record_payment',
      { invoice: invoice.value.name, amount: paymentAmount.value, mode_of_payment: paymentMode.value },
    )
    message.value = `Payment ${r.payment_entry} recorded (${r.allocated.toLocaleString()})`
    paymentAmount.value = null
    await load()
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to record payment'
  } finally { busy.value = false }
}

// Print / PDF using the branded "Genetest Sales Invoice" format that the
// diag_mgmt app ships + pins as the doctype default (via Property Setter).
// Kept as an explicit constant here so if branding changes we swap it in
// one place.
const INVOICE_PRINT_FORMAT = 'Genetest Sales Invoice'

function printInvoice() {
  if (!invoice.value) return
  const params = new URLSearchParams({
    doctype: 'Sales Invoice',
    name: invoice.value.name,
    format: INVOICE_PRINT_FORMAT,
    no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}
function downloadPdf() {
  if (!invoice.value) return
  const params = new URLSearchParams({
    doctype: 'Sales Invoice',
    name: invoice.value.name,
    format: INVOICE_PRINT_FORMAT,
    no_letterhead: '0',
  })
  window.open(`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Invoice · ${invoice?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>
  <div v-else-if="!invoice" class="card p-12 text-center text-surface-400">
    Invoice not found.
    <button class="btn-ghost block mx-auto mt-3" @click="router.push('/billing')">Back to Billing</button>
  </div>

  <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h3 class="font-semibold text-lg">{{ invoice.name }}</h3>
            <div class="text-sm text-surface-500 mt-1">{{ invoice.customer_name || invoice.customer }}</div>
          </div>
          <div class="flex items-center gap-2">
            <StatusPill :status="invoice.status" />
            <span v-if="isDraft" class="pill-warning">Draft</span>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-3">Line Items</h3>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Item</th><th>Description</th><th class="text-right">Qty</th>
            <th class="text-right">Rate</th><th class="text-right">Amount</th>
          </tr></thead>
          <tbody>
            <tr v-for="(it, i) in invoice.items_list" :key="i" class="border-b border-surface-100">
              <td class="py-2"><span class="font-medium">{{ it.item_code }}</span><span v-if="it.item_name && it.item_name !== it.item_code" class="text-xs text-surface-500 block">{{ it.item_name }}</span></td>
              <td>{{ it.description || '—' }}</td>
              <td class="text-right">{{ it.qty }} {{ it.uom || '' }}</td>
              <td class="text-right">{{ it.rate.toLocaleString() }}</td>
              <td class="text-right font-medium">{{ it.amount.toLocaleString() }}</td>
            </tr>
            <tr v-if="!invoice.items_list.length"><td colspan="5" class="py-8 text-center text-surface-400">No items</td></tr>
          </tbody>
        </table>
        <dl class="mt-4 pt-4 border-t border-surface-100 text-sm space-y-1 max-w-xs ml-auto">
          <div v-if="invoice.total_taxes_and_charges" class="flex justify-between"><dt>Taxes</dt><dd>{{ invoice.total_taxes_and_charges?.toLocaleString() }}</dd></div>
          <div class="flex justify-between font-semibold pt-2 border-t border-surface-200"><dt>Total</dt><dd>{{ invoice.grand_total?.toLocaleString() }} {{ invoice.currency }}</dd></div>
          <div class="flex justify-between text-status-warning"><dt>Outstanding</dt><dd>{{ invoice.outstanding_amount?.toLocaleString() }}</dd></div>
        </dl>
      </div>

      <div v-if="invoice.payments && invoice.payments.length" class="card p-5">
        <h3 class="font-semibold mb-3">Payments</h3>
        <ul class="text-sm space-y-2">
          <li v-for="p in invoice.payments" :key="p.parent" class="flex justify-between border-b border-surface-100 pb-2">
            <span class="text-brand-teal-600">{{ p.parent }}</span>
            <span>{{ p.allocated_amount.toLocaleString() }}</span>
          </li>
        </ul>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Patient</dt><dd>{{ invoice.patient_name || invoice.patient || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Posted</dt><dd>{{ invoice.posting_date }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Due</dt><dd>{{ invoice.due_date || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="invoice.status" /></dd></div>
          <!-- Referring Doctor — inline editable even after submit. -->
          <div>
            <div class="flex justify-between items-start">
              <dt class="text-surface-500">Doctor</dt>
              <dd class="text-right max-w-[65%]">
                <template v-if="!doctorEditing">
                  <span>{{ invoice.custom_doctor || '—' }}</span>
                  <button class="ml-2 text-xs text-brand-teal-600 hover:underline"
                          @click="startEditDoctor">Edit</button>
                </template>
                <template v-else>
                  <input v-model="doctorDraft" type="text"
                         class="w-full px-2 py-1 border border-surface-200 rounded text-sm"
                         placeholder="Referring doctor name" />
                  <div class="flex gap-2 justify-end mt-1">
                    <button class="text-xs text-surface-500 hover:underline"
                            :disabled="doctorSaving" @click="doctorEditing = false">Cancel</button>
                    <button class="text-xs text-brand-teal-600 hover:underline font-medium"
                            :disabled="doctorSaving" @click="saveDoctor">
                      {{ doctorSaving ? 'Saving…' : 'Save' }}
                    </button>
                  </div>
                </template>
              </dd>
            </div>
            <p v-if="doctorMessage" class="text-xs text-status-success text-right mt-1">{{ doctorMessage }}</p>
          </div>
        </dl>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-3">Actions</h3>
        <button class="btn-secondary w-full mb-2" @click="printInvoice">Print Invoice</button>
        <button class="btn-ghost w-full" @click="downloadPdf">Download PDF</button>
      </div>

      <div v-if="isOutstanding" class="card p-5">
        <h3 class="font-semibold mb-3">Record Payment</h3>
        <label class="block text-xs text-surface-500 mb-1">Amount ({{ invoice.currency }})</label>
        <input v-model.number="paymentAmount" type="number" min="0" :max="invoice.outstanding_amount"
          class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-3"
          :placeholder="`Outstanding: ${invoice.outstanding_amount.toLocaleString()}`" />
        <label class="block text-xs text-surface-500 mb-1">Mode of Payment</label>
        <select v-model="paymentMode" class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-3">
          <option v-for="m in modesOfPayment" :key="m" :value="m">{{ m }}</option>
        </select>
        <p v-if="error" class="text-sm text-status-danger mb-2">{{ error }}</p>
        <p v-if="message" class="text-sm text-status-success mb-2">{{ message }}</p>
        <button class="btn-primary w-full" :disabled="busy || !paymentAmount" @click="recordPayment">
          {{ busy ? 'Recording…' : 'Record Payment' }}
        </button>
      </div>
    </div>
  </div>
</template>
