<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { collectionApi, type SampleRow } from '@/api/adms'

const list = ref<SampleRow[]>([])
const loading = ref(false)
const busyId = ref<string | null>(null)

async function load() {
  loading.value = true
  try { list.value = await collectionApi.worklist() } catch { list.value = [] }
  finally { loading.value = false }
}
onMounted(load)

async function markCollected(row: SampleRow) {
  busyId.value = row.name
  try { await collectionApi.markCollected(row.name); await load() } finally { busyId.value = null }
}
</script>

<template>
  <Topbar title="Collection Worklist" subtitle="Open queue for phlebotomists across all branches" />
  <div class="card p-1 overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-surface-200 text-left text-surface-500">
          <th class="px-3 py-3">Sample ID</th>
          <th class="px-3 py-3">Patient</th>
          <th class="px-3 py-3">Specimen</th>
          <th class="px-3 py-3">Collected Date</th>
          <th class="px-3 py-3">Time</th>
          <th class="px-3 py-3">Status</th>
          <th class="px-3 py-3"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!list.length">
          <td colspan="7" class="text-center text-surface-400 py-12">{{ loading ? 'Loading…' : 'No collection tasks' }}</td>
        </tr>
        <tr v-for="row in list" :key="row.name" class="border-b border-surface-100 hover:bg-surface-50">
          <td class="px-3 py-3">{{ row.name }}</td>
          <td class="px-3 py-3">{{ row.patient_name }}</td>
          <td class="px-3 py-3">{{ row.sample || '—' }}</td>
          <td class="px-3 py-3">{{ row.collection_date || '—' }}</td>
          <td class="px-3 py-3">{{ row.collection_time || '—' }}</td>
          <td class="px-3 py-3"><StatusPill :status="row.status || 'Draft'" /></td>
          <td class="px-3 py-3 text-right">
            <button v-if="row.status === 'Draft'"
              class="btn-ghost !py-1 !px-2 text-xs"
              :disabled="busyId === row.name"
              @click.stop="markCollected(row)">
              Mark Collected
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
