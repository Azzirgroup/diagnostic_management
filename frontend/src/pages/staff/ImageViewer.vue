<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'

const route = useRoute()
const router = useRouter()
const tools = ['WW/WL', 'Zoom', 'Pan', 'Rotate', 'Flip H', 'Flip V', 'Measure', 'Annotate', 'Arrow', 'Text', 'Circle', 'Angle', 'Reset']
const patient = ref<any>(null)
const study = ref<any>(null)
const series = ref<any[]>([])

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    patient.value = null
    study.value = null
    series.value = []
  } catch {
    patient.value = null
    study.value = null
    series.value = []
  }
})
</script>

<template>
  <Topbar title="Image Viewer" />
  <div class="card p-5 mb-4 flex items-center gap-6 flex-wrap">
    <div class="w-14 h-14 rounded-full bg-brand-teal-100 text-brand-teal-700 flex items-center justify-center font-semibold">{{ patient?.initials || '—' }}</div>
    <div>
      <div class="font-semibold">{{ patient?.name || '—' }} <span v-if="patient?.gender" class="pill-info">{{ patient.gender }}</span></div>
      <div class="text-xs text-surface-500">{{ patient?.meta || '' }}</div>
    </div>
    <div class="text-sm text-surface-500">Study: <span class="text-surface-800">{{ study?.name || '—' }}</span></div>
    <div class="text-sm text-surface-500">ID: <span class="text-surface-800">{{ route.params.name || '—' }}</span></div>
    <div v-if="study?.priority" class="ml-auto"><span class="pill-danger">{{ study.priority }}</span></div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
    <div class="lg:col-span-3 card p-3 bg-surface-900 text-white">
      <div class="flex flex-wrap gap-2 mb-3">
        <button v-for="t in tools" :key="t" class="text-xs px-2 py-1 rounded bg-surface-800 hover:bg-surface-700">{{ t }}</button>
      </div>
      <div class="relative aspect-square bg-black flex items-center justify-center text-surface-500 rounded">
        <span>DICOM viewer canvas (Cornerstone.js mount point)</span>
        <span class="absolute top-2 left-2 text-xs text-surface-400">Im: 12/25  Se: 3</span>
        <span class="absolute top-2 right-2 text-xs text-surface-400">Zoom: 1.25x  WW: 900  WL: 450</span>
        <span class="absolute bottom-2 left-2 text-xs text-surface-400">512 × 512</span>
      </div>
      <div class="mt-3 grid grid-cols-7 gap-2">
        <div v-for="(s, i) in series" :key="i" class="aspect-square bg-surface-800 rounded text-xs flex items-center justify-center text-surface-400">
          {{ s.label }}
        </div>
      </div>
    </div>
    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Study Details</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Body Part</dt><dd>{{ study?.body || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Protocol</dt><dd>{{ study?.protocol || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Slice</dt><dd>{{ study?.slice || '—' }}</dd></div>
        </dl>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Series ({{ series.length }})</h3>
        <ul v-if="series.length" class="text-sm space-y-2">
          <li v-for="s in series" :key="s.label" class="flex justify-between">
            <span>{{ s.label }}</span><span class="text-surface-500">{{ s.count }}</span>
          </li>
        </ul>
        <p v-else class="text-sm text-surface-400">No data</p>
      </div>
      <div class="card p-5 space-y-2">
        <button class="btn-primary w-full" @click="router.push('/radiology/report')">Open Report</button>
        <button class="btn-ghost w-full">Mark Reviewed</button>
        <button class="btn-danger-ghost w-full">Flag Finding</button>
      </div>
    </div>
  </div>
</template>
