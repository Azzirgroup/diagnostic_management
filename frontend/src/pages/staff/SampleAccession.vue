<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { getList } from '@/api/client'

const router = useRouter()
const samples = ref<any[]>([])
const loading = ref(false)
const selected = ref<any | null>(null)
const tab = ref<'pending' | 'accepted' | 'rejected'>('pending')

const counts = ref({ pending: 0, accepted: 0, rejected: 0 })

async function load() {
  loading.value = true
  try {
    samples.value = await getList({
      doctype: 'Sample Collection',
      fields: ['name', 'patient', 'patient_name', 'sample', 'sample_qty', 'collected_time', 'status'],
      limit_page_length: 50,
      order_by: 'creation desc',
    })
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<template>
  <Topbar title="Sample Accession Queue" />
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
    <KpiCard label="Awaiting Receipt" :value="counts.pending || samples.length" sub="Samples in queue" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Rejections Today" :value="counts.rejected" delta="1 vs yesterday" delta-direction="down" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Routed to Bench" :value="counts.accepted" delta="6 vs yesterday" delta-direction="up" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-100">
        <button :class="['text-sm pb-2 border-b-2', tab === 'pending' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'pending'">Pending</button>
        <button :class="['text-sm pb-2 border-b-2', tab === 'accepted' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'accepted'">Accepted</button>
        <button :class="['text-sm pb-2 border-b-2', tab === 'rejected' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'rejected'">Rejected</button>
      </div>
      <DataTable
        :rows="samples"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r)"
        :empty-text="loading ? 'Loading…' : 'No samples in queue'"
        :columns="[
          { key: 'name', label: 'Sample ID' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'sample', label: 'Specimen Type' },
          { key: 'collected_time', label: 'Collected' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }">
          <StatusPill :status="(value as string) || 'Collected'" />
        </template>
      </DataTable>
    </div>

    <div>
      <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name" @close="selected = null">
        <dl class="text-sm space-y-3">
          <div class="flex justify-between"><dt class="text-surface-500">Sample Type</dt><dd>{{ selected.sample }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Volume</dt><dd>{{ selected.sample_qty || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Collected</dt><dd>{{ selected.collected_time?.split('.')[0] || '—' }}</dd></div>
        </dl>
        <div class="mt-6">
          <h4 class="font-semibold mb-2 text-sm">Sample Integrity Check</h4>
          <ul class="text-sm space-y-1.5">
            <li class="flex justify-between"><span class="text-surface-600">Label match</span><span class="text-status-success">Match</span></li>
            <li class="flex justify-between"><span class="text-surface-600">Volume adequate</span><span class="text-status-success">Adequate</span></li>
            <li class="flex justify-between"><span class="text-surface-600">Hemolysis</span><span class="text-status-success">None</span></li>
            <li class="flex justify-between"><span class="text-surface-600">Clot present</span><span class="text-status-success">None</span></li>
          </ul>
        </div>
        <button class="btn-primary w-full mt-6">Accept &amp; Route</button>
        <button class="btn-danger-ghost w-full mt-2" @click="router.push(`/lab/sample/${selected.name}`)">Reject Sample</button>
      </DetailPane>
      <div v-else class="card p-6 text-center text-surface-400">Select a sample</div>
    </div>
  </div>
</template>
