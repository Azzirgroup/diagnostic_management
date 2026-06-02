<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import SearchBar from '@/components/ui/SearchBar.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { usePatientsStore, type Patient } from '@/stores/patients'

const patients = usePatientsStore()
const search = ref('')
const router = useRouter()
const selectedPatient = ref<Patient | null>(null)

onMounted(() => patients.fetch())

let t: ReturnType<typeof setTimeout> | null = null
watch(search, (v) => {
  if (t) clearTimeout(t)
  t = setTimeout(() => patients.fetch(50, v || undefined), 250)
})

function onSelect(p: Patient) {
  selectedPatient.value = p
}

function openDetail() {
  if (selectedPatient.value) router.push(`/patients/${selectedPatient.value.name}`)
}
function openEdit() {
  if (selectedPatient.value) router.push(`/patients/${selectedPatient.value.name}/edit`)
}

function age(dob?: string): string {
  if (!dob) return '—'
  const d = new Date(dob)
  return `${Math.floor((Date.now() - d.getTime()) / (365.25 * 86400 * 1000))} Y`
}
</script>

<template>
  <Topbar title="Patients" />

  <div class="mb-4 flex items-center gap-3">
    <div class="flex-1">
      <SearchBar v-model="search" placeholder="Search patients by name, ID or MRN..." :show-kbd-hint="true" />
    </div>
    <RouterLink to="/patients/new" class="btn-primary whitespace-nowrap">+ Add Patient</RouterLink>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="patients.list"
        row-key="name"
        :selectable="true"
        :initial-selected-index="0"
        @select="onSelect"
        :empty-text="patients.loading ? 'Loading…' : 'No patients yet'"
        :columns="[
          { key: 'patient_name', label: 'Patient Name' },
          { key: 'uid', label: 'Patient ID / MRN' },
          { key: 'sex', label: 'Sex' },
          { key: 'mobile', label: 'Phone' },
          { key: 'blood_group', label: 'Actions' },
        ]"
      >
        <template #cell-patient_name="{ row }">
          <div class="flex items-center gap-3">
            <div class="w-9 h-9 rounded-full bg-brand-teal-100 text-brand-teal-700 flex items-center justify-center text-xs font-semibold">
              {{ (row.patient_name as string)?.split(' ').slice(0,2).map(s => s[0]).join('').toUpperCase() || '—' }}
            </div>
            <div>
              <div class="font-medium text-surface-800">{{ row.patient_name }}</div>
              <div class="text-xs text-surface-500">{{ age(row.dob as string) }}, {{ row.sex || '—' }}</div>
            </div>
          </div>
        </template>
        <template #cell-uid="{ row }">
          <span class="text-surface-700">{{ row.uid || row.name }}</span>
        </template>
        <template #cell-blood_group="{ row, value }">
          <div class="flex items-center gap-2 flex-wrap">
            <StatusPill v-if="value" :status="value as string" tone="info" />
            <span v-else class="text-surface-400 text-xs">—</span>
            <button class="text-xs text-brand-teal-600 hover:underline ml-2"
              @click.stop="router.push(`/patients/${(row as Patient).name}`)">View</button>
            <button class="text-xs text-brand-navy-700 hover:underline"
              @click.stop="router.push(`/patients/${(row as Patient).name}/edit`)">Edit</button>
          </div>
        </template>
      </DataTable>
    </div>

    <div>
      <DetailPane
        v-if="selectedPatient"
        :title="selectedPatient.patient_name"
        :subtitle="`${selectedPatient.uid || selectedPatient.name} · ${age(selectedPatient.dob)}, ${selectedPatient.sex || '—'}`"
        @close="selectedPatient = null"
      >
        <dl class="text-sm space-y-3">
          <div class="flex justify-between"><dt class="text-surface-500">Phone</dt><dd class="text-surface-800">{{ selectedPatient.mobile || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Email</dt><dd class="text-surface-800 truncate max-w-[180px]">{{ selectedPatient.email || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Blood Group</dt><dd class="text-surface-800">{{ selectedPatient.blood_group || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Registered</dt><dd class="text-surface-800">—</dd></div>
        </dl>
        <div class="grid grid-cols-2 gap-2 mt-6">
          <button class="btn-primary" @click="openDetail">View</button>
          <button class="btn-ghost" @click="openEdit">Edit</button>
        </div>
        <button class="btn-ghost w-full mt-2">Open Results</button>
      </DetailPane>
      <div v-else class="card p-6 text-center text-surface-400">Select a patient to see details.</div>
    </div>
  </div>
</template>
