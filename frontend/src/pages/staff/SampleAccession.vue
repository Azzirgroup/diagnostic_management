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

// Tabs derive from received_condition, NOT status (status has only Pending/
// Partly Collected/Collected — no slot for "accepted" or "rejected").
const REJECT_CONDITIONS = ['Haemolysed', 'Clotted', 'Insufficient', 'Wrong Tube', 'Other']
const isAccepted = (s: SampleRow) => s.received_condition === 'Acceptable'
const isRejected = (s: SampleRow) => !!s.received_condition && REJECT_CONDITIONS.includes(s.received_condition)
const isPending = (s: SampleRow) => !s.received_condition && (s.status === 'Pending' || s.status === 'Partly Collected' || s.status === 'Collected')

async function load() {
  loading.value = true
  try { samples.value = await collectionApi.accessionQueue(200) } catch { samples.value = [] }
  finally { loading.value = false }
}
onMounted(load)

const filtered = computed(() => {
  if (tab.value === 'rejected') return samples.value.filter(isRejected)
  if (tab.value === 'accepted') return samples.value.filter(isAccepted)
  return samples.value.filter(isPending)
})

const counts = computed(() => ({
  pending: samples.value.filter(isPending).length,
  accepted: samples.value.filter(isAccepted).length,
  rejected: samples.value.filter(isRejected).length,
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

function printLabel(name: string) {
  const params = new URLSearchParams({
    doctype: 'Sample Collection',
    name,
    format: 'Specimen Label',
    no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar title="Sample Accession Queue" />
  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
    <KpiCard label="Awaiting Receipt" :value="counts.pending" sub="No condition recorded yet" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Accepted" :value="counts.accepted" sub="Condition = Acceptable" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Rejected" :value="counts.rejected" sub="Haemolysed / Clotted / etc." icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <div class="px-4 py-3 flex items-center gap-3 border-b border-surface-100">
        <button :class="['text-sm pb-2 border-b-2', tab === 'pending' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'pending'">
          Pending ({{ counts.pending }})
        </button>
        <button :class="['text-sm pb-2 border-b-2', tab === 'accepted' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'accepted'">
          Accepted ({{ counts.accepted }})
        </button>
        <button :class="['text-sm pb-2 border-b-2', tab === 'rejected' ? 'border-brand-navy-700 text-brand-navy-700 font-medium' : 'border-transparent text-surface-500']" @click="tab = 'rejected'">
          Rejected ({{ counts.rejected }})
        </button>
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
          { key: 'sample', label: 'Specimen' },
          { key: 'collected_time', label: 'Collected' },
          { key: 'received_condition', label: 'Condition' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-collected_time="{ value }">{{ (value as string)?.split('.')[0] || '—' }}</template>
        <template #cell-received_condition="{ value }">
          <span v-if="value === 'Acceptable'" class="text-status-success font-medium">Acceptable</span>
          <span v-else-if="value" class="text-status-danger font-medium">{{ value }}</span>
          <span v-else class="text-surface-400">—</span>
        </template>
        <template #cell-status="{ value }">
          <StatusPill :status="(value as string) || 'Pending'" />
        </template>
      </DataTable>
    </div>

    <div>
      <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
        <dl class="text-sm space-y-3">
          <div class="flex justify-between"><dt class="text-surface-500">Specimen</dt><dd>{{ selected.sample || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Volume</dt><dd>{{ selected.sample_qty ?? '—' }} {{ selected.sample_uom || '' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Collected</dt><dd>{{ (selected.collected_time as string)?.split('.')[0] || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Order</dt><dd>{{ selected.service_request || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Barcode</dt><dd>{{ selected.barcode || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Condition</dt><dd>{{ selected.received_condition || 'Not recorded' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
        </dl>
        <div class="mt-4 space-y-2">
          <button class="btn-ghost w-full" @click="router.push(`/lab/sample/${selected.name}`)">View Details</button>
          <button class="btn-ghost w-full" @click="printLabel(selected.name)">Print Label</button>
        </div>
        <div v-if="tab === 'pending'" class="mt-4 pt-4 border-t border-surface-100 space-y-2">
          <input v-model="destination" placeholder="Route to bench (optional)" class="w-full px-3 py-2 rounded border border-surface-200 text-sm" />
          <textarea v-model="acceptNote" rows="2" placeholder="Acceptance notes (optional)" class="w-full px-3 py-2 rounded border border-surface-200 text-sm"></textarea>
          <button class="btn-primary w-full" :disabled="busy" @click="accept">Accept &amp; Route</button>
          <button class="btn-danger-ghost w-full" @click="router.push(`/lab/sample/${selected.name}`)">Reject Sample…</button>
        </div>
      </DetailPane>
      <div v-else class="card p-6 text-center text-surface-400">Select a sample</div>
    </div>
  </div>
</template>
