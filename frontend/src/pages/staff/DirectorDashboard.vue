<script setup lang="ts">
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'

const branches = [
  { name: 'Main Branch', samples: 612, tat: '2h 05m', ontime: '96.4%', rev: '₹6.12L', delta: '+9.3%' },
  { name: 'North Branch', samples: 318, tat: '2h 28m', ontime: '92.1%', rev: '₹2.87L', delta: '+7.8%' },
  { name: 'East Branch', samples: 220, tat: '2h 42m', ontime: '90.2%', rev: '₹1.95L', delta: '+6.1%' },
  { name: 'West Branch', samples: 134, tat: '2h 15m', ontime: '95.0%', rev: '₹1.54L', delta: '+8.4%' },
]
</script>

<template>
  <Topbar title="Director Executive Dashboard" subtitle="Performance overview across all branches and departments." />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Revenue Today" :value="'₹12.48L'" delta="8.7% vs yesterday" delta-direction="up" />
    <KpiCard label="Samples Processed" :value="1284" delta="10.2% vs yesterday" delta-direction="up" />
    <KpiCard label="Avg TAT Today" :value="'2h 18m'" delta="0.4h vs yesterday · On Track" delta-direction="down" />
    <KpiCard label="Critical Escalations" :value="5" delta="28.6% vs yesterday" delta-direction="down" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-5">
      <h3 class="font-semibold mb-3">Cross-Department Performance Overview</h3>
      <svg viewBox="0 0 700 240" class="w-full h-60">
        <g stroke="#E4E9F1">
          <line v-for="y in [40, 80, 120, 160, 200]" :key="y" :x1="40" :y1="y" :x2="700" :y2="y" />
        </g>
        <path d="M40,200 C140,150 240,80 340,60 S540,30 700,20" fill="none" stroke="#0B2440" stroke-width="2.5"/>
        <path d="M40,210 C140,170 240,120 340,100 S540,80 700,70" fill="none" stroke="#1A8B96" stroke-width="2.5"/>
        <path d="M40,215 C140,190 240,160 340,140 S540,120 700,110" fill="none" stroke="#7B96B8" stroke-width="2.5"/>
        <path d="M40,220 C140,205 240,180 340,165 S540,150 700,140" fill="none" stroke="#B45309" stroke-width="2.5"/>
      </svg>
      <div class="grid grid-cols-4 gap-3 text-center mt-4">
        <div><div class="text-xs text-surface-500">Hematology</div><div class="text-lg font-semibold">1,642</div><div class="text-xs text-status-success">↑ 12.3%</div></div>
        <div><div class="text-xs text-surface-500">Biochemistry</div><div class="text-lg font-semibold">1,286</div><div class="text-xs text-status-success">↑ 9.1%</div></div>
        <div><div class="text-xs text-surface-500">Radiology</div><div class="text-lg font-semibold">948</div><div class="text-xs text-status-success">↑ 7.4%</div></div>
        <div><div class="text-xs text-surface-500">Microbiology</div><div class="text-lg font-semibold">612</div><div class="text-xs text-status-success">↑ 5.6%</div></div>
      </div>
    </div>
    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Financial Snapshot</h3>
        <ul class="text-sm space-y-2">
          <li class="flex justify-between"><span class="text-surface-500">Total Revenue</span><span class="font-semibold">₹12.48L</span></li>
          <li class="flex justify-between"><span class="text-surface-500">Collections</span><span class="font-semibold">₹11.23L</span></li>
          <li class="flex justify-between"><span class="text-surface-500">Outstanding</span><span class="font-semibold">₹3.21L</span></li>
          <li class="flex justify-between"><span class="text-surface-500">Today's Refunds</span><span class="font-semibold">₹45.2K</span></li>
        </ul>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Quality / Compliance Alerts</h3>
        <ul class="text-sm space-y-2">
          <li class="flex justify-between"><span>Results pending verification &gt; 24h</span><span class="pill-danger">7</span></li>
          <li class="flex justify-between"><span>QC failures</span><span class="pill-warning">3</span></li>
          <li class="flex justify-between"><span>Equipment calibration due</span><span class="pill-warning">4</span></li>
          <li class="flex justify-between"><span>License renewals due (30 days)</span><span class="pill-info">2</span></li>
        </ul>
      </div>
    </div>
  </div>

  <div class="card p-5 mt-4">
    <h3 class="font-semibold mb-3">Branch Performance Summary</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">Branch</th><th>Samples Processed</th><th>Avg TAT</th><th>On-Time %</th><th>Revenue Today</th>
      </tr></thead>
      <tbody>
        <tr v-for="b in branches" :key="b.name" class="border-b border-surface-100">
          <td class="py-2">{{ b.name }}</td><td>{{ b.samples }}</td><td>{{ b.tat }}</td>
          <td>{{ b.ontime }}</td><td>{{ b.rev }} <span class="text-status-success text-xs">{{ b.delta }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
