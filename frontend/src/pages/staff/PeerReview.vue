<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { labApi, type PeerReviewRow } from '@/api/adms'

const rows = ref<PeerReviewRow[]>([])
const selected = ref<PeerReviewRow | null>(null)
const reviewNotes = ref('')
const busy = ref(false)

async function load() {
  try { rows.value = await labApi.peerReviewList() } catch { rows.value = [] }
}
onMounted(load)

const kpis = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  const pending = rows.value.filter((r) => r.status === 'Open' || r.status === 'In Review').length
  const overdue = rows.value.filter((r) => r.due_date && r.due_date < today && r.status !== 'Closed').length
  const discussion = rows.value.filter((r) => r.status === 'Discussion').length
  const completed = rows.value.filter((r) => r.status === 'Closed').length
  return { pending, overdue, discussion, completed }
})

async function submit(outcome: string) {
  if (!selected.value) return
  busy.value = true
  try {
    await labApi.submitPeerReview({ name: selected.value.name, outcome, review_notes: reviewNotes.value })
    reviewNotes.value = ''
    selected.value = null
    await load()
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Peer Review Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Reviews" :value="kpis.pending" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Overdue" :value="kpis.overdue" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="In Discussion" :value="kpis.discussion" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Completed" :value="kpis.completed" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r as any)"
        empty-text="No peer review cases"
        :columns="[
          { key: 'name', label: 'Case ID' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'modality', label: 'Test / Modality' },
          { key: 'original_reporter', label: 'Reporter' },
          { key: 'assigned_reviewer', label: 'Reviewer' },
          { key: 'due_date', label: 'Due Date' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
      <dl class="text-sm space-y-3">
        <div class="flex justify-between"><dt class="text-surface-500">Modality / Test</dt><dd>{{ selected.modality || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reporter</dt><dd>{{ selected.original_reporter || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reviewer</dt><dd>{{ selected.assigned_reviewer || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Due</dt><dd>{{ selected.due_date || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
      </dl>
      <label class="block text-xs text-surface-500 mt-4 mb-1">Review Notes (Required)</label>
      <textarea v-model="reviewNotes" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="4" placeholder="Enter your comparison, comments, or additional findings..."></textarea>
      <button class="btn-primary w-full mt-4" :disabled="busy || !reviewNotes.trim()" @click="submit('Agree')">Submit · Agree</button>
      <button class="btn-secondary w-full mt-2" :disabled="busy || !reviewNotes.trim()" @click="submit('Minor Disagreement')">Submit · Minor Disagree</button>
      <button class="btn-danger-ghost w-full mt-2" :disabled="busy || !reviewNotes.trim()" @click="submit('Major Disagreement')">Submit · Major Disagree</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a case to review</div>
  </div>
</template>
