<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'

const modalities = ref<any[]>([])
const studies = ref<any[]>([])
const modalityStatus = ref<any[]>([])
const radiologistWorkload = ref<any[]>([])

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    modalities.value = []
    studies.value = []
    modalityStatus.value = []
    radiologistWorkload.value = []
  } catch {
    modalities.value = []
    studies.value = []
    modalityStatus.value = []
    radiologistWorkload.value = []
  }
})
</script>

<template>
  <Topbar title="Radiology Manager Dashboard" />
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <KpiCard label="Scheduled Studies" :value="0" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Report Backlog" :value="0" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Critical Findings" :value="0" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Modality Uptime" :value="0" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold">Modality Workload Overview</h3>
          <select class="input w-28"><option>Today</option></select>
        </div>
        <div v-if="modalities.length" class="grid grid-cols-6 gap-2">
          <div v-for="m in modalities" :key="m.code" class="text-center">
            <div class="bg-brand-teal-100 text-brand-teal-700 rounded-lg p-3">
              <div class="text-xs">{{ m.code }}</div>
              <div class="text-2xl font-semibold mt-1">{{ m.total }}</div>
              <div class="text-xs text-surface-500">{{ m.scheduled }} scheduled</div>
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-surface-400">No data</p>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-3">Today's Studies Worklist</h3>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Study ID</th><th>Patient</th><th>Modality</th><th>Time</th><th>Status</th>
          </tr></thead>
          <tbody>
            <tr v-for="s in studies" :key="s.id" class="border-b border-surface-100">
              <td class="py-2">{{ s.id }}</td>
              <td>{{ s.patient }}</td>
              <td>{{ s.modality }}</td>
              <td>{{ s.time }}</td>
              <td><StatusPill :status="s.status" /></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!studies.length" class="text-sm text-surface-400 mt-3">No data</p>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Modality Status</h3>
        <ul v-if="modalityStatus.length" class="space-y-2 text-sm">
          <li v-for="m in modalityStatus" :key="m.name" class="flex justify-between"><span>{{ m.name }}</span><span>{{ m.value }}</span></li>
        </ul>
        <p v-else class="text-sm text-surface-400">No data</p>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Radiologist Workload</h3>
        <ul v-if="radiologistWorkload.length" class="text-sm space-y-2">
          <li v-for="r in radiologistWorkload" :key="r.name" class="flex justify-between"><span>{{ r.name }}</span><span>{{ r.load }}</span></li>
        </ul>
        <p v-else class="text-sm text-surface-400">No data</p>
      </div>
    </div>
  </div>
</template>
