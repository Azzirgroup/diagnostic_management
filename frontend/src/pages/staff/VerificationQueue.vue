<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { getList } from '@/api/client'

const rows = ref<any[]>([])
const selected = ref<any>(null)
const comment = ref('')

onMounted(async () => {
  rows.value = await getList({
    doctype: 'Diagnostic Report',
    fields: ['name', 'docname', 'patient', 'patient_name', 'practitioner', 'status', 'creation'],
    filters: { status: ['in', ['Draft', 'Pending']] },
    limit_page_length: 25,
    order_by: 'creation desc',
  })
})
</script>

<template>
  <Topbar title="Verification Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Verification" :value="rows.length || 28" delta="6 from yesterday" delta-direction="down" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Urgent Cases" :value="7" delta="2 from yesterday" delta-direction="up" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Peer Reviews" :value="5" sub="No change" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Avg Sign-off Time" :value="'18m 42s'" delta="5m vs yesterday" delta-direction="down" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r)"
        empty-text="Verification queue is clear"
        :columns="[
          { key: 'name', label: 'Report' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'practitioner', label: 'Reporter' },
          { key: 'creation', label: 'Created' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string" /></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name" @close="selected = null">
      <dl class="text-sm space-y-3">
        <div class="flex justify-between"><dt class="text-surface-500">Created</dt><dd>{{ selected.creation?.split('.')[0] }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reporter</dt><dd>{{ selected.practitioner || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
      </dl>
      <label class="block text-xs text-surface-500 mt-4 mb-1">Add Comment (Optional)</label>
      <textarea v-model="comment" class="input" rows="3" placeholder="Add a comment or note for this case..."></textarea>
      <button class="btn-primary w-full mt-4">Verify &amp; Release</button>
      <button class="btn-ghost w-full mt-2">Request Amendment</button>
      <button class="btn-danger-ghost w-full mt-2">Escalate</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a report to verify</div>
  </div>
</template>
