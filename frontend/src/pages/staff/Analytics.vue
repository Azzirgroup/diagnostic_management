<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import { analyticsApi, type AnalyticsKpis } from '@/api/adms'

const days = ref(7)
const kpis = ref<AnalyticsKpis>({ orders: 0, samples: 0, reports_completed: 0, critical_results: 0, pre_auth_approved: 0, qc_failed: 0 })
const trend = ref<Array<{ date: string; orders: number; samples: number; reports: number }>>([])
const mix = ref<Array<{ section: string; count: number }>>([])

async function load() {
  try { kpis.value = await analyticsApi.kpis(days.value) } catch { /* keep */ }
  try { trend.value = await analyticsApi.volumeTrend(14) } catch { trend.value = [] }
  try { mix.value = await analyticsApi.sectionMix(30) } catch { mix.value = [] }
}
onMounted(load)

const totalMix = computed(() => mix.value.reduce((s, m) => s + m.count, 0))

// Compute a simple line-chart path from `trend.value.orders`.
const trendPath = computed(() => {
  if (!trend.value.length) return ''
  const max = Math.max(1, ...trend.value.map((t) => t.orders))
  const w = 700, h = 160, padL = 40, padR = 20, padT = 20, padB = 20
  const innerW = w - padL - padR
  const innerH = h - padT - padB
  const step = innerW / Math.max(1, trend.value.length - 1)
  return trend.value
    .map((t, i) => `${i === 0 ? 'M' : 'L'}${padL + step * i},${padT + innerH - (t.orders / max) * innerH}`)
    .join(' ')
})
</script>

<template>
  <Topbar title="Analytics — Operations" />
  <div class="card p-4 mb-4 flex flex-wrap items-center gap-3">
    <label class="text-sm text-surface-500">Window</label>
    <select v-model.number="days" class="input px-3 py-2 rounded border border-surface-200" @change="load">
      <option :value="7">Last 7 days</option>
      <option :value="14">Last 14 days</option>
      <option :value="30">Last 30 days</option>
      <option :value="90">Last 90 days</option>
    </select>
    <button class="btn-ghost ml-auto" @click="load">Refresh</button>
  </div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <KpiCard label="Orders" :value="kpis.orders" sub="In window" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Samples" :value="kpis.samples" sub="Collected" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Reports Completed" :value="kpis.reports_completed" sub="Verified" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Critical Results" :value="kpis.critical_results" sub="Flagged" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-4">
    <KpiCard label="Pre-Auth Approved" :value="kpis.pre_auth_approved" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="QC Failures" :value="kpis.qc_failed" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="card p-5 lg:col-span-2">
      <h3 class="font-semibold mb-3">Order Volume (last 14 days)</h3>
      <svg v-if="trend.length" viewBox="0 0 720 200" class="w-full h-56">
        <g stroke="#E4E9F1">
          <line x1="40" y1="40" x2="720" y2="40" />
          <line x1="40" y1="80" x2="720" y2="80" />
          <line x1="40" y1="120" x2="720" y2="120" />
          <line x1="40" y1="160" x2="720" y2="160" />
        </g>
        <path :d="trendPath" fill="none" stroke="#1A8B96" stroke-width="3"/>
      </svg>
      <p v-else class="text-sm text-surface-400">No trend data</p>
    </div>
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Workload by Section <span class="text-surface-400 text-xs">(last 30d)</span></h3>
      <ul v-if="mix.length" class="text-sm space-y-2">
        <li v-for="m in mix" :key="m.section" class="flex justify-between">
          <span>{{ m.section }}</span>
          <span>{{ m.count }} ({{ totalMix ? Math.round((m.count / totalMix) * 1000) / 10 : 0 }}%)</span>
        </li>
      </ul>
      <p v-else class="text-sm text-surface-400">No section data</p>
    </div>
  </div>
</template>
