<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { auditApi, type SampleRow, type DiagnosticReportRow } from '@/api/adms'

const tab = ref<'critical' | 'rejections'>('critical')
const criticalAudit = ref<DiagnosticReportRow[]>([])
const rejections = ref<SampleRow[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const [c, r] = await Promise.all([
      auditApi.criticalAudit(30, 100).catch(() => []),
      auditApi.rejectionLog(30, 100).catch(() => []),
    ])
    criticalAudit.value = c
    rejections.value = r
  } finally { loading.value = false }
}
onMounted(load)

const kpis = computed(() => ({
  critical: criticalAudit.value.length,
  unacked: criticalAudit.value.filter((r) => !r.critical_acknowledged).length,
  rejections: rejections.value.length,
}))
</script>

<template>
  <Topbar title="Audit &amp; Compliance" />
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
    <KpiCard label="Critical Reports (Peer Review)" :value="kpis.critical" sub="Last 30 days" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Awaiting Review" :value="kpis.unacked" sub="Pending peer review" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Sample Rejections" :value="kpis.rejections" sub="Last 30 days" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
  </div>

  <div class="card p-1">
    <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-100">
      <button :class="['text-sm pb-2 border-b-2', tab === 'critical' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'critical'">Critical Results · Peer Review</button>
      <button :class="['text-sm pb-2 border-b-2', tab === 'rejections' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'rejections'">Sample Rejections</button>
      <button class="ml-auto btn-ghost !py-1 !px-2 text-xs" @click="load">Refresh</button>
    </div>

    <DataTable v-if="tab === 'critical'" :rows="criticalAudit" row-key="name"
      :empty-text="loading ? 'Loading…' : 'No critical reports awaiting peer review'"
      :columns="[
        { key: 'name', label: 'Report' },
        { key: 'patient_name', label: 'Patient' },
        { key: 'critical_acknowledged', label: 'Peer Review' },
        { key: 'critical_acknowledged_at', label: 'Reviewed At' },
        { key: 'modified', label: 'Updated' },
      ]"
    >
      <template #cell-critical_acknowledged="{ value }">
        <StatusPill :status="value ? 'Reviewed' : 'Pending Review'" />
      </template>
    </DataTable>

    <DataTable v-else :rows="rejections" row-key="name"
      :empty-text="loading ? 'Loading…' : 'No rejections in window'"
      :columns="[
        { key: 'name', label: 'Sample' },
        { key: 'patient_name', label: 'Patient' },
        { key: 'sample', label: 'Specimen' },
        { key: 'received_condition', label: 'Condition' },
        { key: 'rejection_reason_text', label: 'Reason' },
        { key: 'modified', label: 'When' },
      ]"
    />
  </div>
</template>
