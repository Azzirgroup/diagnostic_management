<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import StatusPill from '@/components/ui/StatusPill.vue'

const router = useRouter()
const queue = ref<any[]>([])
const payments = ref<any>(null)

onMounted(async () => {
  try {
    // TODO: wire to Frappe doctype (getList<...>(...))
    queue.value = []
    payments.value = null
  } catch {
    queue.value = []
    payments.value = null
  }
})
</script>

<template>
  <Topbar title="Reception Dashboard" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Patients Waiting" :value="0" />
    <KpiCard label="Orders Today" :value="0" />
    <KpiCard label="Cash Collected" :value="0" />
    <KpiCard label="Pending Invoices" :value="0" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Quick Actions</h3>
        <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
          <button class="btn-ghost flex-col py-4">
            <span class="text-2xl">📝</span><span class="text-xs mt-1">Register Patient</span>
          </button>
          <button class="btn-ghost flex-col py-4" @click="router.push('/orders/new')">
            <span class="text-2xl">📋</span><span class="text-xs mt-1">New Order</span>
          </button>
          <button class="btn-ghost flex-col py-4" @click="router.push('/patients')">
            <span class="text-2xl">🔍</span><span class="text-xs mt-1">Search Patient</span>
          </button>
          <button class="btn-ghost flex-col py-4">
            <span class="text-2xl">💳</span><span class="text-xs mt-1">Collect Payment</span>
          </button>
          <button class="btn-ghost flex-col py-4">
            <span class="text-2xl">🖨️</span><span class="text-xs mt-1">Print Receipt</span>
          </button>
        </div>
      </div>
      <div class="card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold">Front Desk Queue <span class="text-surface-400 text-xs">({{ queue.length }} waiting)</span></h3>
          <a class="text-sm text-brand-teal-600 hover:underline" href="#">View all</a>
        </div>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">#</th><th>Patient</th><th>Visit Type</th><th>Wait Time</th><th>Status</th>
          </tr></thead>
          <tbody>
            <tr v-for="q in queue" :key="q.i" class="border-b border-surface-100">
              <td class="py-2">{{ q.i }}</td>
              <td>{{ q.name }}</td>
              <td>{{ q.visit }}</td>
              <td>{{ q.wait }}</td>
              <td><StatusPill :status="q.status" /></td>
            </tr>
          </tbody>
        </table>
        <p v-if="!queue.length" class="text-sm text-surface-400 mt-3">No data</p>
      </div>
    </div>
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Payment Summary</h3>
      <ul v-if="payments" class="text-sm space-y-3">
        <li class="flex justify-between"><span>Cash Collected</span><span class="text-brand-teal-700">{{ payments.cash }}</span></li>
        <li class="flex justify-between"><span>Card Payments</span><span class="text-brand-teal-700">{{ payments.card }}</span></li>
        <li class="flex justify-between"><span>Online Payments</span><span class="text-brand-teal-700">{{ payments.online }}</span></li>
        <li class="flex justify-between border-t border-surface-200 pt-3 font-semibold"><span>Total Collected</span><span>{{ payments.total }}</span></li>
      </ul>
      <p v-else class="text-sm text-surface-400">No data</p>
    </div>
  </div>
</template>
