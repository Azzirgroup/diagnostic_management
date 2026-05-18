<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { collectionApi, type SampleRow } from '@/api/adms'

const list = ref<SampleRow[]>([])
const loading = ref(false)
const busyId = ref<string | null>(null)
const router = useRouter()

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

function viewSample(name: string) {
  router.push(`/lab/sample/${name}`)
}

function printLabel(name: string) {
  const params = new URLSearchParams({
    doctype: 'Sample Collection',
    name,
    format: 'Specimen Label',
    no_letterhead: '0',
  })
  window.open(`/printview?${params.toString()}`, '_blank')
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
          <th class="px-3 py-3">Collected</th>
          <th class="px-3 py-3">Status</th>
          <th class="px-3 py-3 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!list.length">
          <td colspan="6" class="text-center text-surface-400 py-12">{{ loading ? 'Loading…' : 'No samples in worklist' }}</td>
        </tr>
        <tr v-for="row in list" :key="row.name" class="border-b border-surface-100 hover:bg-surface-50 cursor-pointer" @click="viewSample(row.name)">
          <td class="px-3 py-3 text-brand-teal-600 font-medium">{{ row.name }}</td>
          <td class="px-3 py-3">{{ row.patient_name }}</td>
          <td class="px-3 py-3">{{ row.sample || '—' }}{{ row.sample_qty ? ` · ${row.sample_qty} ${row.sample_uom || ''}`.trim() : '' }}</td>
          <td class="px-3 py-3">{{ (row.collected_time as string)?.split('.')[0] || '—' }}</td>
          <td class="px-3 py-3"><StatusPill :status="row.status || 'Pending'" /></td>
          <td class="px-3 py-3 text-right" @click.stop>
            <div class="flex justify-end gap-3 text-xs">
              <button class="text-brand-teal-600 hover:underline" @click="viewSample(row.name)">View</button>
              <button class="text-brand-teal-600 hover:underline" @click="printLabel(row.name)">Print</button>
              <button v-if="row.status === 'Pending'"
                class="text-brand-teal-600 hover:underline"
                :disabled="busyId === row.name"
                @click="markCollected(row)">
                Mark Collected
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
