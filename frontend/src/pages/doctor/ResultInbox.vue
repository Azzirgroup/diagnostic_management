<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { getList } from '@/api/client'

const router = useRouter()
const all = ref<any[]>([])
const selected = ref<any | null>(null)
const tab = ref<'all' | 'unread' | 'flagged'>('all')

async function load() {
  all.value = await getList({
    doctype: 'Diagnostic Report',
    fields: ['name', 'docname', 'patient', 'patient_name', 'creation', 'status'],
    limit_page_length: 30,
    order_by: 'creation desc',
  })
}
onMounted(load)
</script>

<template>
  <Topbar title="Result Inbox" />
  <div class="flex items-center gap-2 mb-4">
    <button v-for="(label, key) in { all: 'All Results', unread: 'Unread', flagged: 'Flagged' }" :key="key"
      :class="['btn-ghost !py-1.5 !text-xs', tab === key && '!bg-brand-navy-700 !text-white !border-transparent']"
      @click="tab = key as any">
      {{ label }} <span class="ml-1 text-surface-400">{{ all.length }}</span>
    </button>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-3 px-3">Patient</th><th>Order / Result</th><th>Date</th><th>Status</th>
        </tr></thead>
        <tbody>
          <tr v-if="!all.length"><td colspan="4" class="py-12 text-center text-surface-400">No results in inbox.</td></tr>
          <tr v-for="r in all" :key="r.name"
            class="border-b border-surface-100 cursor-pointer hover:bg-surface-50"
            :class="{ 'row-selected': selected?.name === r.name }"
            @click="selected = r">
            <td class="py-3 px-3 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-brand-teal-500" />
              {{ r.patient_name }}
            </td>
            <td>{{ r.docname || r.name }}</td>
            <td>{{ r.creation?.split(' ')[0] }}</td>
            <td><StatusPill :status="r.status || 'New'" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <DetailPane v-if="selected" :title="selected.patient_name" :subtitle="selected.docname" @close="selected = null">
      <button class="btn-primary w-full" @click="router.push(`/doctor/results/${selected.name}`)">Open Full Report</button>
      <button class="btn-secondary w-full mt-2" @click="router.push(`/doctor/results/${selected.name}/acknowledge`)">Acknowledge Critical</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a result</div>
  </div>
</template>
