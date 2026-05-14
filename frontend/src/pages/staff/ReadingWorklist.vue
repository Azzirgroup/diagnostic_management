<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'

const router = useRouter()
const selected = ref<any>(null)
const rows = ref<any[]>([])

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    rows.value = []
  } catch {
    rows.value = []
  }
})
</script>

<template>
  <Topbar title="Reading Worklist" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Unread Studies" :value="0" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Urgent Studies" :value="0" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Peer Review Pending" :value="0" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="TAT Risk (Next 2 hrs)" :value="0" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable :rows="rows" :selectable="true" :initial-selected-index="0" @select="(r) => (selected = r)" empty-text="No data"
        :columns="[
          { key: 'study', label: 'Study ID' },
          { key: 'patient', label: 'Patient' },
          { key: 'modality', label: 'Modality' },
          { key: 'body', label: 'Body Part' },
          { key: 'referrer', label: 'Referring Doctor' },
          { key: 'received', label: 'Received' },
          { key: 'priority', label: 'Priority' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-priority="{ value }"><StatusPill :status="value as string"/></template>
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.patient" :subtitle="`${selected.modality} · ${selected.body}`" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Study ID</dt><dd>{{ selected.study }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Received</dt><dd>{{ selected.received }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Referring Doctor</dt><dd>{{ selected.referrer }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Priority</dt><dd><StatusPill :status="selected.priority"/></dd></div>
      </dl>
      <button class="btn-primary w-full mt-6" @click="router.push(`/radiology/viewer/${selected.study}`)">Open Viewer</button>
      <button class="btn-secondary w-full mt-2" @click="router.push(`/radiology/report/${selected.study}`)">Start Report</button>
      <button class="btn-ghost w-full mt-2">Assign Peer Review</button>
      <button class="btn-danger-ghost w-full mt-2">Escalate</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a study</div>
  </div>
</template>
