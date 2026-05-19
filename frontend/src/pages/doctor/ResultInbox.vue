<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { doctorApi, type DiagnosticReportRow } from '@/api/adms'

const router = useRouter()
const all = ref<DiagnosticReportRow[]>([])
const selected = ref<DiagnosticReportRow | null>(null)
const tab = ref<'all' | 'unread' | 'flagged'>('all')

async function load() {
  try { all.value = await doctorApi.resultsInbox(undefined, 200) } catch { all.value = [] }
}
onMounted(load)

const filtered = computed(() => {
  if (tab.value === 'unread') return all.value.filter((r) => r.status === 'Draft' || r.status === 'Pending')
  if (tab.value === 'flagged') return all.value.filter((r) => r.is_critical)
  return all.value
})
const flaggedCount = computed(() => all.value.filter((r) => r.is_critical).length)
const unreadCount = computed(() => all.value.filter((r) => r.status === 'Draft' || r.status === 'Pending').length)
</script>

<template>
  <Topbar title="Result Inbox" />
  <div class="flex items-center gap-2 mb-4">
    <button :class="['btn-ghost !py-1.5 !text-xs', tab === 'all' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'all'">All Results <span class="ml-1 text-surface-400">{{ all.length }}</span></button>
    <button :class="['btn-ghost !py-1.5 !text-xs', tab === 'unread' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'unread'">Pending <span class="ml-1 text-surface-400">{{ unreadCount }}</span></button>
    <button :class="['btn-ghost !py-1.5 !text-xs', tab === 'flagged' && '!bg-brand-navy-700 !text-white !border-transparent']" @click="tab = 'flagged'">Critical <span class="ml-1 text-surface-400">{{ flaggedCount }}</span></button>
  </div>

  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-3 px-3">Patient</th><th>Report</th><th>Date</th><th>Critical</th><th>Status</th>
        </tr></thead>
        <tbody>
          <tr v-if="!filtered.length"><td colspan="5" class="py-12 text-center text-surface-400">No results in inbox.</td></tr>
          <tr v-for="r in filtered" :key="r.name"
            class="border-b border-surface-100 cursor-pointer hover:bg-surface-50"
            :class="{ 'row-selected': selected?.name === r.name }"
            @click="selected = r">
            <td class="py-3 px-3 flex items-center gap-2">
              <span class="w-1.5 h-1.5 rounded-full bg-brand-teal-500" />
              {{ r.patient_name }}
            </td>
            <td>{{ r.docname || r.name }}</td>
            <td>{{ r.creation?.split(' ')[0] }}</td>
            <td>
              <span v-if="r.is_critical && !r.critical_acknowledged" class="text-status-danger font-semibold">Unack.</span>
              <span v-else-if="r.is_critical" class="text-status-success">Acked</span>
              <span v-else class="text-surface-400">—</span>
            </td>
            <td><StatusPill :status="r.status || 'New'" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <DetailPane v-if="selected" :title="selected.patient_name || ''" :subtitle="selected.docname || selected.name" @close="selected = null">
      <dl class="text-sm space-y-2">
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Critical</dt><dd>{{ selected.is_critical ? 'Yes' : 'No' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Acknowledged</dt><dd>{{ selected.critical_acknowledged ? 'Yes' : 'No' }}</dd></div>
      </dl>
      <button class="btn-primary w-full mt-4" @click="router.push(`/results/${selected.name}`)">Open Full Report</button>
      <button v-if="selected.is_critical && !selected.critical_acknowledged" class="btn-secondary w-full mt-2" @click="router.push(`/results/${selected.name}/acknowledge`)">Acknowledge Critical</button>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a result</div>
  </div>
</template>
