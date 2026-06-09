<script setup>
// Inline-SVG daily revenue chart used by the Shift Report. Expects an array
// of { date, revenue } from the shift_report endpoint.
import { computed } from 'vue'
const props = defineProps({
  dailyTotals: { type: Array, default: () => [] },
})
const W = 640, H = 200, padL = 44, padR = 8, padT = 12, padB = 32
const maxRev = computed(() => Math.max(1, ...props.dailyTotals.map(d => Number(d.revenue) || 0)))
const path = computed(() => {
  const n = props.dailyTotals.length
  if (n === 0) return ''
  const step = (W - padL - padR) / Math.max(1, n - 1)
  return props.dailyTotals.map((d, i) => {
    const x = padL + i * step
    const y = padT + (H - padT - padB) * (1 - (Number(d.revenue) || 0) / maxRev.value)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})
const areaPath = computed(() => {
  if (!path.value) return ''
  const n = props.dailyTotals.length
  const step = (W - padL - padR) / Math.max(1, n - 1)
  const lastX = padL + (n - 1) * step
  return `${path.value} L${lastX.toFixed(1)},${H - padB} L${padL},${H - padB} Z`
})
const fmt = v => 'Ksh ' + (Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })
const tickEvery = computed(() => Math.max(1, Math.round(props.dailyTotals.length / 8)))
</script>

<template>
  <div class="rounded-lg border border-surface-200 bg-white p-3">
    <h4 class="text-sm font-semibold text-surface-700 mb-2">Daily Revenue</h4>
    <div v-if="!dailyTotals.length" class="text-xs text-surface-400 py-8 text-center">No revenue in the selected window.</div>
    <svg v-else :viewBox="`0 0 ${W} ${H}`" class="w-full h-48">
      <line :x1="padL" :y1="H - padB" :x2="W - padR" :y2="H - padB" stroke="#cbd5e1" stroke-width="1" />
      <line :x1="padL" :y1="padT" :x2="padL" :y2="H - padB" stroke="#cbd5e1" stroke-width="1" />
      <path :d="areaPath" fill="#10b981" fill-opacity="0.12" />
      <path :d="path" fill="none" stroke="#10b981" stroke-width="2" />
      <g v-for="(d, i) in dailyTotals" :key="d.date">
        <circle v-if="i % tickEvery === 0 || i === dailyTotals.length - 1"
          :cx="padL + i * ((W - padL - padR) / Math.max(1, dailyTotals.length - 1))"
          :cy="padT + (H - padT - padB) * (1 - (Number(d.revenue) || 0) / maxRev)"
          r="2.5" fill="#10b981" />
        <text v-if="i % tickEvery === 0 || i === dailyTotals.length - 1"
          :x="padL + i * ((W - padL - padR) / Math.max(1, dailyTotals.length - 1))"
          :y="H - padB + 14" text-anchor="middle" font-size="9" fill="#64748b">{{ d.date.slice(5) }}</text>
      </g>
      <text :x="padL - 4" :y="padT + 10" font-size="9" text-anchor="end" fill="#64748b">{{ fmt(maxRev) }}</text>
      <text :x="padL - 4" :y="H - padB" font-size="9" text-anchor="end" fill="#64748b">0</text>
    </svg>
  </div>
</template>
