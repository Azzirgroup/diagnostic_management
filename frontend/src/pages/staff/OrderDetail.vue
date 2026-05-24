<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import WorkflowStepper from '@/components/ui/WorkflowStepper.vue'
import { ordersApi, type OrderDetail, type SampleRow } from '@/api/adms'

const route = useRoute()
const router = useRouter()
const order = ref<OrderDetail | null>(null)

async function load() {
  order.value = await ordersApi.detail(route.params.name as string)
}
onMounted(load)

// Timeline steps + how far this order has progressed come from the backend
// (orders.detail), so the highlighting reflects real state instead of a
// hard-coded position.
const steps = computed(() => order.value?.timeline_steps ?? ['Ordered', 'Collected', 'Accessioned', 'In Process', 'Completed'])
const stage = computed(() => order.value?.stage ?? 0)
const samples = computed<SampleRow[]>(() => order.value?.samples ?? [])
const firstSample = computed(() => samples.value[0]?.name)
const reports = computed<any[]>(() => order.value?.reports ?? [])
const labTests = computed<any[]>(() => order.value?.lab_tests ?? [])

// Edit is only allowed while the document is a draft (docstatus 0). Once a
// Service Request is submitted (docstatus 1) it's locked from the SPA — the
// user must cancel + recreate, or amend through the backend workflow.
const isDraft = computed(() => Number(order.value?.docstatus ?? 0) === 0)

function openCollect(row: SampleRow) {
  router.push(`/lab/sample/${row.name}/collect`)
}

function strip(v?: string) {
  return (v || '').replace(/-Request Status$/i, '').replace(/-Priority$/i, '')
}

// Open Frappe's print preview in a new tab. The user can review the layout
// and hit Ctrl+P / the browser's Print button — same UX as ERPNext invoices.
function printRequisition() {
  if (!order.value?.name) return
  const params = new URLSearchParams({
    doctype: 'Service Request',
    name: order.value.name as string,
    format: 'Diagnostic Order Requisition',
    no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}

// Direct PDF download — same format, but bypasses the preview tab.
function downloadRequisitionPdf() {
  if (!order.value?.name) return
  const params = new URLSearchParams({
    doctype: 'Service Request',
    name: order.value.name as string,
    format: 'Diagnostic Order Requisition',
    no_letterhead: '0',
  })
  window.open(`/api/method/frappe.utils.print_format.download_pdf?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Order ${order?.name || ''}`" />

  <div v-if="order" class="space-y-4">
    <WorkflowStepper :order="order.name" :sample="firstSample" current="order" />
    <div class="card p-5">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-xs text-surface-500">Created on {{ order.creation?.split('.')[0] }}</div>
          <div class="font-semibold text-lg">{{ order.title || order.subject || order.name }}</div>
        </div>
        <div class="flex items-center gap-2">
          <StatusPill :status="strip(order.status) || 'Active'" />
          <button v-if="isDraft" class="btn-primary !py-1.5 !text-xs"
            @click="router.push(`/orders/${order.name}/edit`)">Edit</button>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold">Ordered Tests</h3>
        </div>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Test / Study</th><th>Priority</th><th>Status</th>
          </tr></thead>
          <tbody>
            <tr class="border-b border-surface-100">
              <td class="py-3">{{ order.template_dn || order.title || order.subject || '—' }}</td>
              <td><StatusPill :status="strip(order.priority) || 'Routine'" /></td>
              <td><StatusPill :status="strip(order.status) || '—'" /></td>
            </tr>
          </tbody>
        </table>

        <div class="mt-6">
          <h3 class="font-semibold mb-3">Order Timeline</h3>
          <div class="flex items-center justify-between">
            <div v-for="(s, i) in steps" :key="s" class="flex-1 flex flex-col items-center">
              <div :class="['w-10 h-10 rounded-full flex items-center justify-center text-xs font-medium',
                i <= stage ? 'bg-brand-teal-100 text-brand-teal-700 border-2 border-brand-teal-500'
                           : 'bg-surface-100 text-surface-400 border-2 border-dashed border-surface-300']">
                <span v-if="i < stage">✓</span>
                <span v-else>{{ i + 1 }}</span>
              </div>
              <div :class="['text-xs mt-2', i <= stage ? 'text-surface-700 font-medium' : 'text-surface-400']">{{ s }}</div>
            </div>
          </div>
        </div>

        <div class="mt-6">
          <h3 class="font-semibold mb-3">Samples</h3>
          <table v-if="samples.length" class="w-full text-sm">
            <thead><tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-2">Sample ID</th><th>Specimen</th><th>Container</th><th>Status</th><th class="text-right">Action</th>
            </tr></thead>
            <tbody>
              <tr v-for="sc in samples" :key="sc.name" class="border-b border-surface-100">
                <td class="py-3">
                  <button class="text-brand-teal-600 font-medium hover:underline" @click="router.push(`/lab/sample/${sc.name}`)">{{ sc.name }}</button>
                </td>
                <td>{{ sc.sample || '—' }}</td>
                <td>{{ sc.container || '—' }}</td>
                <td><StatusPill :status="sc.collected_time ? 'Collected' : 'Pending'" /></td>
                <td class="text-right whitespace-nowrap">
                  <button v-if="!sc.collected_time" class="btn-secondary !py-1.5 !px-4 !text-xs" @click="openCollect(sc)">Collect Sample</button>
                  <span v-else class="text-xs text-surface-400">{{ (sc.collected_time as string)?.split('.')[0] }}</span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-sm text-surface-400 py-3">
            No samples yet. Samples appear here once the order is submitted and a Lab Test is created.
          </div>
        </div>

        <div v-if="labTests.length" class="mt-6">
          <h3 class="font-semibold mb-3">Tests</h3>
          <table class="w-full text-sm">
            <thead><tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-2">Test</th><th>Status</th><th class="text-right">Action</th>
            </tr></thead>
            <tbody>
              <tr v-for="t in labTests" :key="t.name" class="border-b border-surface-100">
                <td class="py-3">{{ t.name }}</td>
                <td><StatusPill :status="t.status || 'Draft'" /></td>
                <td class="text-right">
                  <button class="btn-secondary !py-1.5 !px-4 !text-xs" :disabled="t.docstatus === 1"
                    @click="router.push(`/lab/result/${t.name}?order=${order.name}`)">
                    {{ t.docstatus === 1 ? 'Completed' : 'Enter Results' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="mt-6">
          <h3 class="font-semibold mb-3">Results</h3>
          <table v-if="reports.length" class="w-full text-sm">
            <thead><tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-2">Report</th><th>Status</th><th>Critical</th><th class="text-right">Action</th>
            </tr></thead>
            <tbody>
              <tr v-for="r in reports" :key="r.name" class="border-b border-surface-100">
                <td class="py-3">{{ r.name }}</td>
                <td><StatusPill :status="r.status || '—'" /></td>
                <td>
                  <span v-if="r.is_critical" class="pill-danger">Critical</span>
                  <span v-else class="text-surface-400">—</span>
                </td>
                <td class="text-right">
                  <button class="text-brand-teal-600 text-xs hover:underline" @click="router.push('/lab/verification')">Verify →</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="text-sm text-surface-400 py-3 flex items-center justify-between gap-3 flex-wrap">
            <span>No results yet — the sample is being analysed. Results show here once entered, then go to verification.</span>
            <button class="btn-ghost !py-1.5 !text-xs shrink-0" @click="router.push('/lab/verification')">Open Verification Queue →</button>
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div class="card p-5">
          <h3 class="font-semibold mb-3">Patient</h3>
          <div class="text-sm">{{ order.patient_name }}</div>
          <div class="text-xs text-surface-500 mt-1">{{ order.patient }}</div>
        </div>
        <div class="card p-5">
          <h3 class="font-semibold mb-3">Quick Actions</h3>
          <button v-if="isDraft" class="btn-primary w-full mb-2"
            @click="router.push(`/orders/${order.name}/edit`)">Edit Order</button>
          <button class="btn-secondary w-full mb-2" @click="printRequisition">Print Requisition</button>
          <button class="btn-ghost w-full mb-2" @click="downloadRequisitionPdf">Download PDF</button>
          <button class="btn-danger-ghost w-full">Cancel Order</button>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="card p-12 text-center text-surface-400">Loading order…</div>
</template>
