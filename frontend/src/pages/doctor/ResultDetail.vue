<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { getDoc } from '@/api/client'
import StatusPill from '@/components/ui/StatusPill.vue'

const route = useRoute()
const router = useRouter()
const report = ref<any>(null)

onMounted(async () => {
  report.value = await getDoc('Diagnostic Report', route.params.name as string)
})

function downloadPdf() {
  // Frappe serves print formats at /api/method/frappe.utils.print_format.download_pdf
  const params = new URLSearchParams({
    doctype: 'Diagnostic Report',
    name: route.params.name as string,
    format: 'Standard',
    no_letterhead: '0',
  })
  window.open(`/api/method/frappe.utils.print_format.download_pdf?${params}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Result · ${report?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back to Results</button>

  <div v-if="report" class="space-y-4">
    <div class="card p-5 flex items-center gap-6 flex-wrap">
      <div class="w-14 h-14 rounded-full bg-brand-teal-100 text-brand-teal-700 flex items-center justify-center font-semibold">
        {{ (report.patient_name as string)?.split(' ').slice(0,2).map((s: string) => s[0]).join('') }}
      </div>
      <div>
        <div class="font-semibold">{{ report.patient_name }}</div>
        <div class="text-xs text-surface-500">MRN: {{ report.patient }}</div>
      </div>
      <div class="text-sm text-surface-500 ml-auto">Reported: <span class="text-surface-800">{{ report.creation?.split('.')[0] }}</span></div>
      <StatusPill :status="report.status || 'Draft'" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 card p-5">
        <div class="text-center font-semibold uppercase tracking-wider text-surface-600 mb-4">Laboratory Report</div>
        <dl class="grid grid-cols-2 gap-y-2 text-sm mb-4 border-b border-surface-100 pb-4">
          <dt class="text-surface-500">Patient Name</dt><dd>{{ report.patient_name }}</dd>
          <dt class="text-surface-500">MRN</dt><dd>{{ report.patient }}</dd>
          <dt class="text-surface-500">Reported On</dt><dd>{{ report.creation?.split('.')[0] }}</dd>
        </dl>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Test</th><th>Result</th><th>Unit</th><th>Reference Range</th>
          </tr></thead>
          <tbody>
            <tr class="border-b border-surface-100">
              <td class="py-3">{{ report.docname || 'Result' }}</td>
              <td class="font-semibold text-status-danger">15.2 <span class="pill-warning ml-1">Low</span></td>
              <td>ng/mL</td>
              <td>30.0 – 400.0</td>
            </tr>
          </tbody>
        </table>
        <div class="text-center text-xs text-surface-400 mt-6">*** End of Report ***</div>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Report Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill status="Final" /></dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Total Tests</dt><dd>1</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Abnormal</dt><dd class="text-status-danger font-semibold">1</dd></div>
        </dl>
        <button class="btn-primary w-full mt-6" @click="downloadPdf">Download PDF</button>
        <button class="btn-secondary w-full mt-2">Share Report</button>
        <button class="btn-ghost w-full mt-2">Print Report</button>
        <button class="btn-ghost w-full mt-2">Add Note</button>
      </div>
    </div>
  </div>
  <div v-else class="card p-12 text-center text-surface-400">Loading report…</div>
</template>
