<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { getDoc } from '@/api/client'

const route = useRoute()
const order = ref<any>(null)

onMounted(async () => {
  order.value = await getDoc('Service Request', route.params.name as string)
})

const steps = ['Ordered', 'Collected', 'Accessioned', 'In Process', 'Completed']
</script>

<template>
  <Topbar :title="`Order ${order?.name || ''}`" />

  <div v-if="order" class="space-y-4">
    <div class="card p-5">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <div>
          <div class="text-xs text-surface-500">Created on {{ order.creation?.split('.')[0] }}</div>
          <div class="font-semibold text-lg">{{ order.subject || order.name }}</div>
        </div>
        <StatusPill :status="order.status || 'Active'" />
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="lg:col-span-2 card p-5">
        <div class="flex items-center justify-between mb-3">
          <h3 class="font-semibold">Ordered Tests</h3>
          <button class="text-sm text-brand-teal-600 hover:underline">+ Add Test</button>
        </div>
        <table class="w-full text-sm">
          <thead><tr class="text-left text-surface-500 border-b border-surface-200">
            <th class="py-2">Test / Study</th><th>Sample Type</th><th>Priority</th><th>Status</th>
          </tr></thead>
          <tbody>
            <tr class="border-b border-surface-100">
              <td class="py-3">{{ order.template_dn || order.subject || '—' }}</td>
              <td>Serum</td>
              <td><StatusPill :status="order.priority || 'Routine'" /></td>
              <td><StatusPill :status="order.status || 'In Analysis'" /></td>
            </tr>
          </tbody>
        </table>

        <div class="mt-6">
          <h3 class="font-semibold mb-3">Order Timeline</h3>
          <div class="flex items-center justify-between">
            <div v-for="(s, i) in steps" :key="s" class="flex-1 flex flex-col items-center">
              <div :class="['w-10 h-10 rounded-full flex items-center justify-center text-xs font-medium',
                i <= 3 ? 'bg-brand-teal-100 text-brand-teal-700 border-2 border-brand-teal-500'
                       : 'bg-surface-100 text-surface-400 border-2 border-dashed border-surface-300']">
                {{ i + 1 }}
              </div>
              <div class="text-xs mt-2 text-surface-600">{{ s }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="space-y-4">
        <div class="card p-5">
          <h3 class="font-semibold mb-3">Patient</h3>
          <div class="text-sm">{{ order.patient_name }}</div>
          <div class="text-xs text-surface-500 mt-1">{{ order.patient }}</div>
        </div>
        <div class="card p-5">
          <h3 class="font-semibold mb-3">Quick Actions</h3>
          <button class="btn-primary w-full mb-2">Amend Order</button>
          <button class="btn-ghost w-full mb-2">Print Requisition</button>
          <button class="btn-danger-ghost w-full">Cancel Order</button>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="card p-12 text-center text-surface-400">Loading order…</div>
</template>
