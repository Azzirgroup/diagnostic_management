<script setup lang="ts">
// Generic detail-page renderer for simple ADMS doctypes (Reagent Lot, Lab
// Instrument, QC Run, Calibration Run, Peer Review Case, Radiology Pre-Auth,
// Doctor Statement, Lab Test). The route passes the target doctype as a
// meta tag; we fetch the doc, walk its fields via getMeta, and render them
// in a clean two-column layout with Print + Edit links pointing back to the
// Frappe desk form (no per-doctype Vue page to maintain).

import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { call, getDoc } from '@/api/client'

interface FieldMeta { fieldname: string; fieldtype: string; label?: string; options?: string }

const route = useRoute()
const router = useRouter()
const doctype = computed(() => (route.meta.doctype as string) || '')
const docName = computed(() => (route.params.name as string) || '')
const titleOverride = computed(() => (route.meta.title as string) || doctype.value)
const doc = ref<Record<string, any> | null>(null)
const fields = ref<FieldMeta[]>([])
const loading = ref(false)

async function load() {
  if (!doctype.value || !docName.value) return
  loading.value = true
  try {
    doc.value = await getDoc<Record<string, any>>(doctype.value, docName.value)
    fields.value = await loadMeta()
  } catch {
    doc.value = null
  } finally { loading.value = false }
}

async function loadMeta(): Promise<FieldMeta[]> {
  try {
    const meta = await call<any>('frappe.client.get_value', {
      doctype: 'DocType',
      filters: { name: doctype.value },
      fieldname: 'name',
    })
    if (!meta) return []
    // Pull the field definitions via a list call on tabDocField.
    const list = await call<any[]>('frappe.client.get_list', {
      doctype: 'DocField',
      fields: ['fieldname', 'fieldtype', 'label', 'options', 'idx'],
      filters: { parent: doctype.value, hidden: 0 },
      order_by: 'idx asc',
      limit_page_length: 200,
    })
    return (list || []).filter((f) => !['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Button'].includes(f.fieldtype))
  } catch {
    return []
  }
}

const displayFields = computed(() =>
  fields.value
    .filter((f) => !f.fieldname.startsWith('_'))
    .filter((f) => doc.value && doc.value[f.fieldname] !== null && doc.value[f.fieldname] !== '' && doc.value[f.fieldname] !== 0 || ['Check', 'Float', 'Int', 'Currency'].includes(f.fieldtype)),
)

const statusValue = computed(() => doc.value?.status || doc.value?.state)

function format(value: any, fieldtype: string): string {
  if (value === null || value === undefined || value === '') return '—'
  if (fieldtype === 'Check') return value ? 'Yes' : 'No'
  if (fieldtype === 'Currency' || fieldtype === 'Float') return Number(value).toLocaleString()
  if (fieldtype === 'Datetime') return String(value).split('.')[0]
  return String(value)
}

function openInDesk() {
  if (!doctype.value || !docName.value) return
  const slug = doctype.value.toLowerCase().replace(/\s+/g, '-')
  window.open(`/app/${slug}/${docName.value}`, '_blank')
}

onMounted(load)
</script>

<template>
  <Topbar :title="`${titleOverride} · ${docName}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>
  <div v-else-if="!doc" class="card p-12 text-center text-surface-400">Not found.</div>

  <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h3 class="font-semibold text-lg">{{ doc.title || doc.name }}</h3>
            <div class="text-xs text-surface-500 mt-1">{{ doctype }} · {{ docName }}</div>
          </div>
          <StatusPill v-if="statusValue" :status="statusValue" />
        </div>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-4">Details</h3>
        <dl class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <template v-for="f in displayFields" :key="f.fieldname">
            <div class="flex justify-between border-b border-surface-100 pb-2">
              <dt class="text-surface-500">{{ f.label || f.fieldname }}</dt>
              <dd class="text-right max-w-[60%] truncate">{{ format(doc[f.fieldname], f.fieldtype) }}</dd>
            </div>
          </template>
        </dl>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Actions</h3>
        <button class="btn-ghost w-full mb-2" @click="openInDesk">Open in Desk (Edit)</button>
        <button class="btn-ghost w-full" @click="router.back()">Back to List</button>
      </div>
    </div>
  </div>
</template>
