<script setup>
// Per-day variance bars: green for surplus (closing > expected), red for deficit.
import { computed } from 'vue'
const props = defineProps({
  dailyTotals: { type: Array, default: () => [] },
})
const W = 640, H = 180, padL = 44, padR = 8, padT = 12, padB = 32
const maxAbs = computed(() => Math.max(1, ...props.dailyTotals.map(d => Math.abs(Number(d.variance) || 0))))
const fmt = v => (Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })
const midY = computed(() => padT + (H - padT - padB) / 2)
const barWidth = computed(() => Math.max(4, (W - padL - padR) / Math.max(1, props.dailyTotals.length) - 2))
const tickEvery = computed(() => Math.max(1, Math.round(props.dailyTotals.length / 8)))
</script>

<template>
  <div class="rounded-lg border border-surface-200 bg-white p-3">
    <h4 class="text-sm font-semibold text-surface-700 mb-2">Daily Variance (Closing − Expected)</h4>
    <div v-if="!dailyTotals.length" class="text-xs text-surface-400 py-8 text-center">No variance data.</div>
    <svg v-else :viewBox="`0 0 ${W} ${H}`" class="w-full h-44">
      <line :x1="padL" :y1="midY" :x2="W - padR" :y2="midY" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,3" />
      <line :x1="padL" :y1="padT" :x2="padL" :y2="H - padB" stroke="#cbd5e1" stroke-width="1" />
      <g v-for="(d, i) in dailyTotals" :key="d.date">
        <rect
          :x="padL + i * ((W - padL - padR) / Math.max(1, dailyTotals.length))"
          :y="(Number(d.variance) || 0) >= 0 ? midY - ((Number(d.variance) || 0) / maxAbs) * (H - padT - padB) / 2 : midY"
          :width="barWidth"
          :height="Math.abs((Number(d.variance) || 0) / maxAbs) * (H - padT - padB) / 2"
          :fill="(Number(d.variance) || 0) >= 0 ? '#10b981' : '#ef4444'"
        />
        <text v-if="i % tickEvery === 0 || i === dailyTotals.length - 1"
          :x="padL + i * ((W - padL - padR) / Math.max(1, dailyTotals.length)) + barWidth / 2"
          :y="H - padB + 14" text-anchor="middle" font-size="9" fill="#64748b">{{ d.date.slice(5) }}</text>
      </g>
      <text :x="padL - 4" :y="padT + 10" font-size="9" text-anchor="end" fill="#64748b">+{{ fmt(maxAbs) }}</text>
      <text :x="padL - 4" :y="H - padB" font-size="9" text-anchor="end" fill="#64748b">−{{ fmt(maxAbs) }}</text>
    </svg>
  </div>
</template>
