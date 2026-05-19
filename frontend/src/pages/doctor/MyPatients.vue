<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import DataTable from '@/components/ui/DataTable.vue'
import SearchBar from '@/components/ui/SearchBar.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { doctorApi, type PatientLite } from '@/api/adms'

const all = ref<PatientLite[]>([])
const search = ref('')
const router = useRouter()
const selected = ref<PatientLite | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try { all.value = await doctorApi.myPatients(200) } catch { all.value = [] }
  finally { loading.value = false }
}
onMounted(load)

function filtered(): PatientLite[] {
  const q = search.value.trim().toLowerCase()
  if (!q) return all.value
  return all.value.filter((p) =>
    (p.patient_name || '').toLowerCase().includes(q) ||
    (p.mobile || '').toLowerCase().includes(q) ||
    (p.email || '').toLowerCase().includes(q) ||
    (p.name || '').toLowerCase().includes(q),
  )
}
</script>

<template>
  <Topbar title="My Patients" subtitle="Patients you've ordered for in the last 180 days" />
  <SearchBar v-model="search" placeholder="Filter your patient list..." />
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="filtered()"
        row-key="name"
        :selectable="true"
        :empty-text="loading ? 'Loading…' : 'No patients in your panel yet'"
        @select="(p) => (selected = p as any)"
        :columns="[
          { key: 'patient_name', label: 'Patient Name' },
          { key: 'name', label: 'MRN' },
          { key: 'sex', label: 'Sex' },
          { key: 'mobile', label: 'Phone' },
          { key: 'status', label: 'Status' },
        ]"
      />
    </div>
    <DetailPane v-if="selected" :title="selected.patient_name" :subtitle="selected.uid || selected.name" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Phone</dt><dd>{{ selected.mobile || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Email</dt><dd class="truncate max-w-[180px]">{{ selected.email || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Blood Group</dt><dd>{{ selected.blood_group || '—' }}</dd></div>
      </dl>
      <button class="btn-primary w-full mt-4" @click="router.push(`/patients/${selected.name}`)">View Patient</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a patient</div>
  </div>
</template>
