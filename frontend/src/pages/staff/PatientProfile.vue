<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { getDoc, getList } from '@/api/client'

const route = useRoute()
const router = useRouter()
const patient = ref<any>(null)
const orders = ref<any[]>([])
const results = ref<any[]>([])

async function load() {
  const name = route.params.name as string
  patient.value = await getDoc('Patient', name)
  orders.value = await getList({
    doctype: 'Service Request',
    fields: ['name', 'order_date', 'status'],
    filters: { patient: name },
    limit_page_length: 5,
    order_by: 'creation desc',
  })
  results.value = await getList({
    doctype: 'Diagnostic Report',
    fields: ['name', 'docname', 'creation', 'status'],
    filters: { patient: name },
    limit_page_length: 5,
    order_by: 'creation desc',
  })
}
onMounted(load)
</script>

<template>
  <Topbar title="Patient Profile 360" />

  <div v-if="patient" class="card p-5 mb-4 flex items-center gap-6 flex-wrap">
    <div class="w-20 h-20 rounded-full bg-brand-teal-100 text-brand-teal-700 flex items-center justify-center text-xl font-semibold">
      {{ (patient.patient_name as string)?.split(' ').slice(0,2).map((s: string) => s[0]).join('').toUpperCase() }}
    </div>
    <div class="flex-1 min-w-[200px]">
      <div class="flex items-center gap-3">
        <h2 class="text-xl font-semibold text-surface-800">{{ patient.patient_name }}</h2>
        <span v-if="patient.allergies" class="pill-danger">Allergic: {{ patient.allergies }}</span>
      </div>
      <div class="text-sm text-surface-500 mt-1 flex flex-wrap gap-x-4 gap-y-1">
        <span>MRN: {{ patient.uid || patient.name }}</span>
        <span>{{ patient.sex || '—' }}</span>
        <span v-if="patient.blood_group">Blood Group: {{ patient.blood_group }}</span>
        <span v-if="patient.mobile">+{{ patient.mobile }}</span>
      </div>
    </div>
    <button class="btn-ghost">Edit Profile</button>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Demographics</h3>
      <dl class="grid grid-cols-2 gap-y-3 text-sm">
        <dt class="text-surface-500">Date of Birth</dt><dd>{{ patient?.dob || '—' }}</dd>
        <dt class="text-surface-500">Gender</dt><dd>{{ patient?.sex || '—' }}</dd>
        <dt class="text-surface-500">Marital Status</dt><dd>{{ patient?.marital_status || '—' }}</dd>
        <dt class="text-surface-500">Nationality</dt><dd>{{ patient?.nationality || '—' }}</dd>
        <dt class="text-surface-500">Language</dt><dd>{{ patient?.language || '—' }}</dd>
        <dt class="text-surface-500">Occupation</dt><dd>{{ patient?.occupation || '—' }}</dd>
      </dl>
    </div>
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Contact Details</h3>
      <dl class="space-y-3 text-sm">
        <div class="flex justify-between"><dt class="text-surface-500">Primary Phone</dt><dd>{{ patient?.mobile || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Email</dt><dd class="truncate max-w-[260px]">{{ patient?.email || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Address</dt><dd class="text-right max-w-[260px]">{{ patient?.permanent_address || '—' }}</dd></div>
      </dl>
    </div>

    <div class="card p-5 lg:col-span-2">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Recent Orders</h3>
        <RouterLink class="text-sm text-brand-teal-600 hover:underline" to="/orders">View all orders</RouterLink>
      </div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">Order ID</th><th>Test(s)</th><th>Date</th><th>Status</th>
        </tr></thead>
        <tbody>
          <tr v-if="!orders.length"><td colspan="4" class="py-6 text-center text-surface-400">No orders yet.</td></tr>
          <tr v-for="o in orders" :key="o.name" class="border-b border-surface-100 cursor-pointer hover:bg-surface-50" @click="router.push(`/orders/${o.name}`)">
            <td class="py-2">{{ o.name }}</td>
            <td>—</td>
            <td>{{ o.order_date || '—' }}</td>
            <td><StatusPill :status="o.status || 'Active'" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card p-5 lg:col-span-2">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Recent Results</h3>
        <a href="#" class="text-sm text-brand-teal-600 hover:underline">View all results</a>
      </div>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">Report</th><th>Date</th><th>Status</th>
        </tr></thead>
        <tbody>
          <tr v-if="!results.length"><td colspan="3" class="py-6 text-center text-surface-400">No results yet.</td></tr>
          <tr v-for="r in results" :key="r.name" class="border-b border-surface-100">
            <td class="py-2">{{ r.docname || r.name }}</td>
            <td>{{ r.creation?.split(' ')[0] }}</td>
            <td><StatusPill :status="r.status || 'Draft'" /></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
