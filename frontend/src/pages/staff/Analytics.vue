<script setup lang="ts">
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
</script>

<template>
  <Topbar title="Analytics — Operations" />
  <div class="card p-4 mb-4 flex flex-wrap items-center gap-3">
    <select class="input w-40"><option>May 16 – May 22, 2025</option></select>
    <select class="input w-40"><option>Main Branch</option></select>
    <select class="input w-44"><option>All Departments</option></select>
    <select class="input w-52"><option>All Modalities / Sections</option></select>
    <button class="btn-ghost ml-auto">Reset Filters</button>
  </div>
  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
    <KpiCard label="Orders Today" :value="248" delta="12% vs yesterday" delta-direction="up" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Average TAT (Overall)" :value="'01h 42m'" delta="8m vs last week" delta-direction="down" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
    <KpiCard label="Samples Pending" :value="86" delta="9 vs yesterday" delta-direction="up" icon-bg="rgb(254 243 199)" icon-color="rgb(180 83 9)" />
    <KpiCard label="Studies Completed" :value="312" delta="15% vs last week" delta-direction="up" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-4">
    <div class="card p-5 lg:col-span-2">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Average TAT Trend <span class="text-surface-400 text-xs">(Overall)</span></h3>
        <a class="text-sm text-brand-teal-600 hover:underline" href="#">View full report</a>
      </div>
      <svg viewBox="0 0 700 220" class="w-full h-56">
        <g stroke="#E4E9F1">
          <line x1="40" y1="40" x2="700" y2="40" />
          <line x1="40" y1="80" x2="700" y2="80" />
          <line x1="40" y1="120" x2="700" y2="120" />
          <line x1="40" y1="160" x2="700" y2="160" />
        </g>
        <path d="M40,140 L140,80 L240,120 L340,150 L440,140 L540,150 L640,170" fill="none" stroke="#1A8B96" stroke-width="3"/>
        <g fill="#1A8B96">
          <circle cx="40" cy="140" r="4"/><circle cx="140" cy="80" r="4"/><circle cx="240" cy="120" r="4"/>
          <circle cx="340" cy="150" r="4"/><circle cx="440" cy="140" r="4"/><circle cx="540" cy="150" r="4"/><circle cx="640" cy="170" r="4"/>
        </g>
      </svg>
    </div>
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Workload by Department</h3>
      <ul class="text-sm space-y-2">
        <li class="flex justify-between"><span>Radiology</span><span>142 (45.5%)</span></li>
        <li class="flex justify-between"><span>Pathology</span><span>98 (31.4%)</span></li>
        <li class="flex justify-between"><span>Laboratory</span><span>52 (16.7%)</span></li>
        <li class="flex justify-between"><span>Cardiology</span><span>12 (3.8%)</span></li>
        <li class="flex justify-between"><span>Other</span><span>8 (2.6%)</span></li>
      </ul>
    </div>
  </div>
</template>
