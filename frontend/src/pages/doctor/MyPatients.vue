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
const selected = ref<Patient | null>(null)

onMounted(() => patients.fetch())

let t: ReturnType<typeof setTimeout> | null = null
watch(search, (v) => {
  if (t) clearTimeout(t)
  t = setTimeout(() => patients.fetch(50, v || undefined), 250)
})
</script>

<template>
  <Topbar title="My Patients" />
  <SearchBar v-model="search" placeholder="Search patients by name, ID or MRN..." :show-kbd-hint="true" />
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="patients.list"
        :selectable="true"
        @select="(p) => (selected = p)"
        :columns="[
          { key: 'patient_name', label: 'Patient Name' },
          { key: 'uid', label: 'MRN' },
          { key: 'sex', label: 'Sex' },
          { key: 'mobile', label: 'Phone' },
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
      <button class="btn-ghost w-full mt-2">Open Results</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a patient</div>
  </div>
</template>
