<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import {
  reportsApi,
  type ReportsOverview, type ActivityRow, type TopTestRow,
  type SampleMixRow, type BillingSummaryData, type PLData,
} from '@/api/adms'

// "Reports" — operational analytics across lab activity, billing, and P&L.
// Charts are inline SVG so we don't need to pull a chart lib for the SPA.
const days = ref(30)
const overview = ref<ReportsOverview | null>(null)
const activity = ref<ActivityRow[]>([])
const topTests = ref<TopTestRow[]>([])
const sampleMix = ref<SampleMixRow[]>([])
const billing = ref<BillingSummaryData | null>(null)
const pl = ref<PLData | null>(null)
const loading = ref(false)

async function loadAll() {
  loading.value = true
  try {
    const [o, a, t, s, b, p] = await Promise.all([
      reportsApi.overview(days.value),
      reportsApi.activityTrend(days.value),
      reportsApi.topTests(days.value, 10),
      reportsApi.sampleMix(days.value),
      reportsApi.billingSummary(days.value),
      reportsApi.profitAndLoss(days.value),
    ])
    overview.value = o; activity.value = a; topTests.value = t
    sampleMix.value = s; billing.value = b; pl.value = p
  } catch (e: any) {
    // surface error in console; KPI cards just show 0
    console.error(e)
  } finally { loading.value = false }
}
onMounted(loadAll)
watch(days, loadAll)

function fmtCurrency(n?: number) {
  return 'Ksh ' + (n || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })
}
function pct(n?: number) { return ((n || 0).toFixed(1)) + '%' }

// ── Activity multi-line chart (inline SVG) ───────────────────────────────
const chartW = 720, chartH = 200, padL = 40, padR = 12, padT = 12, padB = 24

function buildLine(series: number[], maxVal: number) {
  if (!series.length || !maxVal) return ''
  const stepX = (chartW - padL - padR) / Math.max(1, series.length - 1)
  return series.map((v, i) => {
    const x = padL + i * stepX
    const y = padT + (chartH - padT - padB) * (1 - v / maxVal)
    return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
}
const activitySvg = computed(() => {
  const a = activity.value
  if (!a.length) return { reports: '', tests: '', samples: '', revenue: '', maxCount: 0, maxRevenue: 0 }
  const maxCount = Math.max(1, ...a.map(r => Math.max(r.reports, r.tests, r.samples)))
  const maxRevenue = Math.max(1, ...a.map(r => r.revenue))
  return {
    reports: buildLine(a.map(r => r.reports), maxCount),
    tests:   buildLine(a.map(r => r.tests),   maxCount),
    samples: buildLine(a.map(r => r.samples), maxCount),
    revenue: buildLine(a.map(r => r.revenue), maxRevenue),
    maxCount, maxRevenue,
  }
})

// ── Sample-mix bar chart ────────────────────────────────────────────────
const sampleMixMax = computed(() => Math.max(1, ...sampleMix.value.map(r => r.count)))

// ── P&L bars ────────────────────────────────────────────────────────────
const plMax = computed(() => Math.max(1, ...(pl.value?.series ?? []).map(s => Math.max(s.revenue, s.cogs))))
</script>

<template>
  <Topbar title="Reports" subtitle="Operational analytics — activity, billing, profit & loss" />

  <!-- Window selector + refresh -->
  <div class="card p-3 mb-4 flex items-center gap-4 flex-wrap">
    <span class="text-sm text-surface-500">Window:</span>
    <div class="flex gap-1">
      <button v-for="d in [7, 14, 30, 60, 90]" :key="d"
        :class="['btn-ghost !py-1.5 !text-xs', days === d && '!bg-brand-navy-700 !text-white !border-transparent']"
        @click="days = d">{{ d }} days</button>
    </div>
    <span class="text-xs text-surface-500 ml-auto">
      {{ overview ? `${overview.window.from} → ${overview.window.to}` : '' }}
    </span>
    <button class="btn-ghost !py-1.5 !text-xs" :disabled="loading" @click="loadAll">
      {{ loading ? 'Loading…' : 'Refresh' }}
    </button>
  </div>

  <!-- KPIs -->
  <div class="grid grid-cols-2 lg:grid-cols-6 gap-3 mb-4">
    <KpiCard label="Reports" :value="overview?.reports ?? 0"
      icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Tests" :value="overview?.tests ?? 0"
      icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Samples" :value="overview?.samples ?? 0"
      icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="Revenue" :value="fmtCurrency(overview?.revenue_billed)" sub="Billed"
      icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Outstanding" :value="fmtCurrency(overview?.outstanding)" sub="Awaiting payment"
      icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Margin" :value="pct(overview?.margin_pct)" sub="Gross"
      icon-bg="rgb(254 226 226)" icon-color="rgb(220 38 38)" />
  </div>

  <!-- Activity trend (multi-line) -->
  <div class="card p-4 mb-4">
    <div class="flex items-center justify-between mb-2">
      <h3 class="font-semibold text-sm">Activity Trend</h3>
      <div class="flex items-center gap-3 text-xs">
        <span class="flex items-center gap-1"><span class="w-3 h-1 inline-block bg-blue-500"></span>Reports</span>
        <span class="flex items-center gap-1"><span class="w-3 h-1 inline-block bg-emerald-500"></span>Tests</span>
        <span class="flex items-center gap-1"><span class="w-3 h-1 inline-block bg-red-500"></span>Samples</span>
        <span class="flex items-center gap-1"><span class="w-3 h-1 inline-block bg-purple-500"></span>Revenue (scaled)</span>
      </div>
    </div>
    <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="w-full h-48">
      <!-- baseline -->
      <line :x1="padL" :y1="chartH - padB" :x2="chartW - padR" :y2="chartH - padB" stroke="#cbd5e1" stroke-width="1"/>
      <line :x1="padL" :y1="padT" :x2="padL" :y2="chartH - padB" stroke="#cbd5e1" stroke-width="1"/>
      <path :d="activitySvg.reports" fill="none" stroke="#3b82f6" stroke-width="2"/>
      <path :d="activitySvg.tests"   fill="none" stroke="#10b981" stroke-width="2"/>
      <path :d="activitySvg.samples" fill="none" stroke="#ef4444" stroke-width="2"/>
      <path :d="activitySvg.revenue" fill="none" stroke="#a855f7" stroke-width="2" stroke-dasharray="4,3"/>
      <text :x="padL - 4" :y="padT + 10" font-size="9" text-anchor="end" fill="#64748b">{{ activitySvg.maxCount }}</text>
      <text :x="padL - 4" :y="chartH - padB" font-size="9" text-anchor="end" fill="#64748b">0</text>
    </svg>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
    <!-- Top tests -->
    <div class="card p-1">
      <h3 class="font-semibold text-sm px-4 pt-3 pb-2">Top Tests</h3>
      <DataTable :rows="topTests" row-key="template"
        :empty-text="loading ? 'Loading…' : 'No tests in this window'"
        :columns="[
          { key: 'template', label: 'Template' },
          { key: 'department', label: 'Dept.' },
          { key: 'count', label: 'Count' },
          { key: 'rate', label: 'Unit Rate' },
          { key: 'revenue', label: 'Revenue' },
        ]"
      >
        <template #cell-rate="{ value }">{{ fmtCurrency(value as number) }}</template>
        <template #cell-revenue="{ value }">{{ fmtCurrency(value as number) }}</template>
      </DataTable>
    </div>

    <!-- Sample mix (horizontal bars) -->
    <div class="card p-4">
      <h3 class="font-semibold text-sm mb-2">Sample Type Mix</h3>
      <div v-if="!sampleMix.length" class="text-sm text-surface-400 py-4">No samples in this window</div>
      <div v-else class="space-y-2">
        <div v-for="row in sampleMix" :key="row.sample_type" class="flex items-center gap-2 text-xs">
          <span class="w-24 truncate" :title="row.sample_type">{{ row.sample_type }}</span>
          <div class="flex-1 h-4 bg-surface-100 rounded overflow-hidden">
            <div class="h-full bg-brand-teal-500" :style="{ width: (row.count / sampleMixMax * 100) + '%' }"></div>
          </div>
          <span class="w-10 text-right font-semibold">{{ row.count }}</span>
        </div>
      </div>
    </div>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
    <!-- Billing summary -->
    <div class="card p-4 lg:col-span-2">
      <h3 class="font-semibold text-sm mb-3">Billing</h3>
      <dl class="grid grid-cols-3 gap-3 mb-3 text-sm">
        <div><dt class="text-xs text-surface-500">Billed</dt><dd class="text-lg font-semibold">{{ fmtCurrency(billing?.billed) }}</dd></div>
        <div><dt class="text-xs text-surface-500">Collected</dt><dd class="text-lg font-semibold text-emerald-700">{{ fmtCurrency(billing?.collected) }}</dd></div>
        <div><dt class="text-xs text-surface-500">Outstanding</dt><dd class="text-lg font-semibold text-amber-700">{{ fmtCurrency(billing?.outstanding) }}</dd></div>
      </dl>
      <h4 class="text-xs text-surface-500 mb-2">Payment Mode Mix</h4>
      <div v-if="!billing?.mode_mix?.length" class="text-xs text-surface-400">No payment entries in this window</div>
      <div v-else class="space-y-1.5">
        <div v-for="m in billing.mode_mix" :key="m.mode" class="flex items-center gap-2 text-xs">
          <span class="w-24 truncate">{{ m.mode }}</span>
          <div class="flex-1 h-3 bg-surface-100 rounded overflow-hidden">
            <div class="h-full bg-brand-navy-700"
              :style="{ width: (m.amount / Math.max(1, billing.billed) * 100) + '%' }"></div>
          </div>
          <span class="w-24 text-right font-medium">{{ fmtCurrency(m.amount) }}</span>
        </div>
      </div>
    </div>

    <!-- P&L card -->
    <div class="card p-4">
      <h3 class="font-semibold text-sm mb-3">Profit &amp; Loss</h3>
      <dl class="space-y-2 text-sm">
        <div class="flex justify-between"><dt class="text-surface-500">Revenue</dt><dd class="font-semibold">{{ fmtCurrency(pl?.revenue) }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">COGS (consumables)</dt><dd class="font-semibold text-red-600">{{ fmtCurrency(pl?.cogs) }}</dd></div>
        <div class="flex justify-between border-t border-surface-100 pt-2"><dt class="text-surface-500">Gross Profit</dt><dd class="font-bold text-emerald-700">{{ fmtCurrency(pl?.profit) }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Margin</dt><dd class="font-semibold">{{ pct(pl?.margin_pct) }}</dd></div>
      </dl>
      <p class="text-xs text-surface-400 mt-3">COGS = Manufacture stock entries auto-created when samples reach <em>Tested</em>.</p>
    </div>
  </div>

  <!-- P&L daily series -->
  <div class="card p-4 mb-4">
    <h3 class="font-semibold text-sm mb-2">Revenue vs COGS (daily)</h3>
    <div v-if="!pl?.series?.length" class="text-sm text-surface-400 py-4">No financial activity in this window</div>
    <svg v-else :viewBox="`0 0 ${chartW} ${chartH}`" class="w-full h-48">
      <line :x1="padL" :y1="chartH - padB" :x2="chartW - padR" :y2="chartH - padB" stroke="#cbd5e1" stroke-width="1"/>
      <g v-for="(s, i) in pl.series" :key="s.day">
        <rect
          :x="padL + i * ((chartW - padL - padR) / pl.series.length) + 1"
          :y="chartH - padB - ((s.revenue / plMax) * (chartH - padT - padB))"
          :width="(chartW - padL - padR) / pl.series.length / 2 - 1"
          :height="(s.revenue / plMax) * (chartH - padT - padB)"
          fill="#10b981"
        />
        <rect
          :x="padL + i * ((chartW - padL - padR) / pl.series.length) + (chartW - padL - padR) / pl.series.length / 2"
          :y="chartH - padB - ((s.cogs / plMax) * (chartH - padT - padB))"
          :width="(chartW - padL - padR) / pl.series.length / 2 - 1"
          :height="(s.cogs / plMax) * (chartH - padT - padB)"
          fill="#ef4444"
        />
      </g>
      <text :x="padL - 4" :y="padT + 10" font-size="9" text-anchor="end" fill="#64748b">{{ fmtCurrency(plMax) }}</text>
    </svg>
    <div class="flex items-center gap-3 text-xs mt-1">
      <span class="flex items-center gap-1"><span class="w-3 h-3 inline-block bg-emerald-500"></span>Revenue</span>
      <span class="flex items-center gap-1"><span class="w-3 h-3 inline-block bg-red-500"></span>COGS</span>
    </div>
  </div>
</template>
