<script setup lang="ts">
import { RouterLink } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'

const tiles = [
  { to: '/lab/accession', label: 'Sample Accession', icon: '📥', sub: '24 awaiting receipt' },
  { to: '/lab/verification', label: 'Verification Queue', icon: '✅', sub: '28 pending verification' },
  { to: '/lab/peer-review', label: 'Peer Review', icon: '👥', sub: '5 cases pending' },
  { to: '/lab/instruments', label: 'Lab Instruments', icon: '🧪', sub: '24 online' },
  { to: '/lab/reagents', label: 'Reagents', icon: '🧫', sub: '12 low stock' },
  { to: '/lab/qc', label: 'QC Station', icon: '📊', sub: '18 pending QC' },
  { to: '/lab/calibration', label: 'Calibration & Maintenance', icon: '🔧', sub: '6 due today' },
  { to: '/lab/analyzer-monitor', label: 'Analyzer Interface', icon: '📡', sub: '64 pending HL7' },
]
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
