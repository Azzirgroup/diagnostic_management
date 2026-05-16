<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { collectionApi, sampleApi, type SampleRow } from '@/api/adms'

const router = useRouter()
const samples = ref<SampleRow[]>([])
const loading = ref(false)
const selected = ref<SampleRow | null>(null)
const tab = ref<'pending' | 'accepted' | 'rejected'>('pending')
const acceptNote = ref('')
const destination = ref('')
const busy = ref(false)

async function load() {
  loading.value = true
  try { samples.value = await collectionApi.accessionQueue(200) } catch { samples.value = [] }
  finally { loading.value = false }
}
onMounted(load)

const filtered = computed(() => {
  if (tab.value === 'rejected') return samples.value.filter((s) => s.status === 'Rejected')
  if (tab.value === 'accepted') return samples.value.filter((s) => s.status === 'Received')
  return samples.value.filter((s) => s.status === 'Draft' || s.status === 'Collected')
})

const counts = computed(() => ({
  pending: samples.value.filter((s) => s.status === 'Draft' || s.status === 'Collected').length,
  accepted: samples.value.filter((s) => s.status === 'Received').length,
  rejected: samples.value.filter((s) => s.status === 'Rejected').length,
}))

async function accept() {
  if (!selected.value) return
  busy.value = true
  try {
    await sampleApi.accept(selected.value.name, destination.value || undefined, acceptNote.value)
    acceptNote.value = ''
    destination.value = ''
    selected.value = null
    await load()
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Sample Accession Queue" />
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
    <KpiCard label="Awaiting Receipt" :value="counts.pending" sub="Samples in queue" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Rejected" :value="counts.rejected" sub="In current window" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Routed to Bench" :value="counts.accepted" sub="Received & in process" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-100">
        <button :class="['text-sm pb-2 border-b-2', tab === 'pending' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'pending'">Pending</button>
        <button :class="['text-sm pb-2 border-b-2', tab === 'accepted' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'accepted'">Accepted</button>
        <button :class="['text-sm pb-2 border-b-2', tab === 'rejected' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'rejected'">Rejected</button>
      </div>
      <DataTable
        :rows="filtered"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r as any)"
        :empty-text="loading ? 'Loading…' : 'No samples in this tab'"
        :columns="[
          { key: 'name', label: 'Sample ID' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'sample', label: 'Specimen Type' },
          { key: 'collection_date', label: 'Collected' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-status="{ value }">
          <StatusPill :status="(value as string) || 'Collected'" />
        </template>
      </DataTable>
    </div>

    <div>
      <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
        <dl class="text-sm space-y-3">
          <div class="flex justify-between"><dt class="text-surface-500">Sample Type</dt><dd>{{ selected.sample || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Volume</dt><dd>{{ selected.sample_qty ?? '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Collected</dt><dd>{{ selected.collection_date || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Barcode</dt><dd>{{ selected.barcode || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Condition</dt><dd>{{ selected.received_condition || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
        </dl>
        <div v-if="selected.status === 'Draft' || selected.status === 'Collected'" class="mt-6 space-y-2">
          <input v-model="destination" placeholder="Route to bench (optional)" class="w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <textarea v-model="acceptNote" rows="2" placeholder="Notes (optional)" class="w-full px-3 py-2 rounded border border-surface-200 text-sm"></textarea>
          <button class="btn-primary w-full" :disabled="busy" @click="accept">Accept &amp; Route</button>
          <button class="btn-danger-ghost w-full" @click="router.push(`/lab/sample/${selected.name}`)">Reject Sample</button>
        </div>
      </DetailPane>
      <div v-else class="card p-6 text-center text-surface-400">Select a sample</div>
    </div>
  </div>
</template>
