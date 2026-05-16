<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { labApi, type LabHubSummary } from '@/api/adms'

const summary = ref<LabHubSummary>({
  pending_accession: 0,
  in_analysis: 0,
  pending_verification: 0,
  qc_open: 0,
  calibration_due: 0,
  peer_review_open: 0,
})

onMounted(async () => {
  try { summary.value = await labApi.hubSummary() } catch { /* keep zeros */ }
})

const tiles = computed(() => [
  { to: '/lab/accession', label: 'Sample Accession', icon: '📥', sub: `${summary.value.pending_accession} awaiting receipt` },
  { to: '/lab/verification', label: 'Verification Queue', icon: '✅', sub: `${summary.value.pending_verification} pending verification` },
  { to: '/lab/peer-review', label: 'Peer Review', icon: '👥', sub: `${summary.value.peer_review_open} cases open` },
  { to: '/lab/instruments', label: 'Lab Instruments', icon: '🧪', sub: 'Instrument fleet' },
  { to: '/lab/reagents', label: 'Reagents', icon: '🧫', sub: 'Lot inventory' },
  { to: '/lab/qc', label: 'QC Station', icon: '📊', sub: `${summary.value.qc_open} pending QC` },
  { to: '/lab/calibration', label: 'Calibration & Maintenance', icon: '🔧', sub: `${summary.value.calibration_due} due` },
  { to: '/lab/analyzer-monitor', label: 'Analyzer Monitor', icon: '📡', sub: 'Heartbeats & state' },
])
</script>

<template>
  <Topbar title="Laboratory" />
  <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
    <RouterLink v-for="t in tiles" :key="t.to" :to="t.to" class="card p-5 hover:shadow-card-hover transition-shadow">
      <div class="text-3xl">{{ t.icon }}</div>
      <div class="mt-3 font-semibold text-surface-800">{{ t.label }}</div>
      <div class="text-xs text-surface-500 mt-1">{{ t.sub }}</div>
    </RouterLink>
  </div>
</template>
