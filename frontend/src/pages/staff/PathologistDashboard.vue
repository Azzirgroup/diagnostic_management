<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'

const queue = ref<any[]>([])

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    queue.value = []
  } catch {
    queue.value = []
  }
})
</script>

<template>
  <Topbar title="Pathologist Dashboard" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Verification" :value="0" />
    <KpiCard label="Critical Cases" :value="0" />
    <KpiCard label="Peer Reviews" :value="0" />
    <KpiCard label="Avg Sign-off Time" :value="0" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Verification Queue</h3>
        <select class="input w-24"><option>All Tests</option></select>
      </div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">Order ID</th><th>Patient</th><th>Test(s)</th><th>Sample Type</th><th>Collected At</th><th>Priority</th><th>Status</th>
        </tr></thead>
        <tbody>
          <tr v-for="q in queue" :key="q.id" class="border-b border-surface-100">
            <td class="py-2">{{ q.id }}</td><td>{{ q.patient }}</td><td>{{ q.test }}</td>
            <td>{{ q.sample }}</td><td>{{ q.collected }}</td>
            <td><StatusPill :status="q.priority" /></td>
            <td><StatusPill :status="q.status" /></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">TAT Summary</h3>
        <div class="grid grid-cols-4 gap-2 text-center text-sm">
          <div><div class="text-surface-500 text-xs">Received</div><div class="font-semibold">0</div></div>
          <div><div class="text-surface-500 text-xs">Within TAT</div><div class="font-semibold text-status-success">0</div></div>
          <div><div class="text-surface-500 text-xs">At Risk</div><div class="font-semibold text-status-warning">0</div></div>
          <div><div class="text-surface-500 text-xs">Breached</div><div class="font-semibold text-status-danger">0</div></div>
        </div>
      </div>
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Urgent Findings</h3>
        <p class="text-sm text-surface-400">No urgent findings</p>
      </div>
    </div>
  </div>
</template>
