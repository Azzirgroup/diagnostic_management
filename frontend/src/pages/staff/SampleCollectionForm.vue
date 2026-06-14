<script setup lang="ts">
import { onMounted, reactive, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import WorkflowStepper from '@/components/ui/WorkflowStepper.vue'
import Combobox from '@/components/ui/Combobox.vue'
import { getDoc } from '@/api/client'
import { collectionApi } from '@/api/adms'

// One row in any of this form's searchable dropdowns. `value` is what gets
// stored on the doc field; `label` is what's shown to the user. An empty-value
// row labelled "—" is prepended so the user can clear a selection.
type Opt = { value: string; label: string }
const optKey = (o: Opt) => o.value
const optLabel = (o: Opt) => o.label
// Filter an in-memory list by case-insensitive substring match on the label.
// Always prepends the "—" clear row so it's reachable in every search.
function filterOpts(items: Opt[], q: string): Opt[] {
  const head: Opt = { value: '', label: '—' }
  if (!q) return [head, ...items]
  const lq = q.toLowerCase()
  return [head, ...items.filter((o) => o.label.toLowerCase().includes(lq))]
}

// Full-page editor for a Healthcare Sample Collection record, mirroring the
// desk form (Patient Details, Sample Details, Samples child table, Collection
// Details). Saves the whole document — scalar fields + child rows — via
// collection.save_collection so Marley validation runs.

const route = useRoute()
const router = useRouter()
const name = route.params.name as string
// Order context threaded through the guided workflow (?order=…), used by the
// stepper and to return to the right order after collecting.
const orderQuery = route.query.order as string | undefined

const loading = ref(true)
const saving = ref(false)
const error = ref('')

// Read-only context shown at the top of the form.
const meta = reactive({
  patient: '', patient_name: '', naming_series: '', status: 'Pending',
  invoiced: 0, service_request: '',
})

// Editable scalar fields.
const form = reactive({
  barcode: '', container: '', referring_practitioner: '', company: '',
  collection_point: '', sample: '', sample_uom: '', sample_qty: null as number | null,
  collected_by: '', collected_time: '', num_print: 1 as number | null,
  sample_details: '', received_condition: '', rejection_reason_text: '',
})

type ChildRow = {
  observation_template?: string
  sample?: string
  sample_qty?: number | null
  collection_point?: string
  collection_date_time?: string
  status?: string
  container_closure_color?: string
}
const rows = ref<ChildRow[]>([])

const CONTAINERS = ['Red', 'Gold', 'Lavender', 'Green', 'Grey', 'Blue', 'Yellow', 'Brown', 'White', 'Clear', 'Other']
const CONDITIONS = ['Acceptable', 'Haemolysed', 'Clotted', 'Insufficient', 'Wrong Tube', 'Other']

// Link option lists.
const specimens = ref<Array<{ name: string }>>([])
const units = ref<Array<{ name: string }>>([])
const users = ref<Array<{ name: string; full_name?: string }>>([])
const practitioners = ref<Array<{ name: string; practitioner_name?: string }>>([])
const companies = ref<Array<{ name: string }>>([])
const obsTemplates = ref<Array<{ name: string }>>([])

// Each dropdown gets an Opt[] derived from its source list, a `loadOptions`
// the Combobox calls per keystroke, and a `labelFor*` that turns the stored
// `name` back into the human label so the closed Combobox shows it.
const containerOpts = computed<Opt[]>(() => CONTAINERS.map((c) => ({ value: c, label: c })))
const conditionOpts = computed<Opt[]>(() => CONDITIONS.map((c) => ({ value: c, label: c })))
const specimenOpts  = computed<Opt[]>(() => specimens.value.map((s) => ({ value: s.name, label: s.name })))
const unitOpts      = computed<Opt[]>(() => units.value.map((u) => ({ value: u.name, label: u.name })))
const practitionerOpts = computed<Opt[]>(() => practitioners.value.map((p) => ({ value: p.name, label: p.practitioner_name || p.name })))
const companyOpts   = computed<Opt[]>(() => companies.value.map((c) => ({ value: c.name, label: c.name })))
const collectorOpts = computed<Opt[]>(() => users.value.map((u) => ({ value: u.name, label: u.full_name || u.name })))
const obsTemplateOpts = computed<Opt[]>(() => obsTemplates.value.map((o) => ({ value: o.name, label: o.name })))

const loadContainers = (q: string) => Promise.resolve(filterOpts(containerOpts.value, q))
const loadConditions = (q: string) => Promise.resolve(filterOpts(conditionOpts.value, q))
const loadSpecimens  = (q: string) => Promise.resolve(filterOpts(specimenOpts.value, q))
const loadUnits      = (q: string) => Promise.resolve(filterOpts(unitOpts.value, q))
const loadPractitioners = (q: string) => Promise.resolve(filterOpts(practitionerOpts.value, q))
const loadCompanies  = (q: string) => Promise.resolve(filterOpts(companyOpts.value, q))
const loadCollectors = (q: string) => Promise.resolve(filterOpts(collectorOpts.value, q))
const loadObsTemplates = (q: string) => Promise.resolve(filterOpts(obsTemplateOpts.value, q))

// Return the human label for a stored value. Empty string when nothing is
// selected — the Combobox shows its `placeholder` in that case (we no longer
// stuff a literal "—" into the input text). The "—" clear-row still lives at
// the top of every dropdown list inside `filterOpts` for explicit unselect.
const labelForPractitioner = (v: string) => practitioners.value.find((p) => p.name === v)?.practitioner_name || v || ''
const labelForCollector    = (v: string) => users.value.find((u) => u.name === v)?.full_name || v || ''
const labelForName = (v: string) => v || ''

function toLocal(dt?: string): string {
  if (!dt) return ''
  return dt.split('.')[0].replace(' ', 'T').slice(0, 16)
}
function toFrappe(local?: string): string {
  return local ? `${local.replace('T', ' ')}:00` : ''
}

async function load() {
  loading.value = true
  try {
    const doc = await getDoc('Sample Collection', name) as Record<string, any>
    meta.patient = doc.patient || ''
    meta.patient_name = doc.patient_name || ''
    meta.naming_series = doc.naming_series || ''
    meta.status = doc.status || 'Pending'
    meta.invoiced = doc.invoiced || 0
    meta.service_request = doc.service_request || ''

    form.barcode = doc.barcode || ''
    form.container = doc.container || ''
    form.referring_practitioner = doc.referring_practitioner || ''
    form.company = doc.company || ''
    form.collection_point = doc.collection_point || ''
    form.sample = doc.sample || ''
    form.sample_uom = doc.sample_uom || ''
    form.sample_qty = doc.sample_qty ?? null
    form.collected_by = doc.collected_by || ''
    form.collected_time = toLocal(doc.collected_time)
    form.num_print = doc.num_print ?? 1
    form.sample_details = doc.sample_details || ''
    form.received_condition = doc.received_condition || ''
    form.rejection_reason_text = doc.rejection_reason_text || ''

    rows.value = (doc.observation_sample_collection || []).map((r: any) => ({
      observation_template: r.observation_template || '',
      sample: r.sample || '',
      sample_qty: r.sample_qty ?? null,
      collection_point: r.collection_point || '',
      collection_date_time: toLocal(r.collection_date_time),
      status: r.status || 'Open',
      container_closure_color: r.container_closure_color || '',
    }))
  } catch (e: any) {
    error.value = e?.message || 'Failed to load sample'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await load()
  const [sp, un, us, pr, co, ot] = await Promise.all([
    collectionApi.sampleTypes().catch(() => []),
    collectionApi.serviceUnits().catch(() => []),
    collectionApi.collectors().catch(() => []),
    collectionApi.practitioners().catch(() => []),
    collectionApi.companies().catch(() => []),
    collectionApi.observationTemplates().catch(() => []),
  ])
  specimens.value = sp; units.value = un; users.value = us
  practitioners.value = pr; companies.value = co; obsTemplates.value = ot
})

function addRow() {
  rows.value.push({ status: 'Open', sample_qty: null })
}
function removeRow(i: number) {
  rows.value.splice(i, 1)
}

async function save(collect: boolean) {
  saving.value = true
  error.value = ''
  try {
    const values: Record<string, unknown> = {
      barcode: form.barcode,
      container: form.container,
      referring_practitioner: form.referring_practitioner,
      company: form.company,
      collection_point: form.collection_point,
      sample: form.sample,
      sample_qty: form.sample_qty,
      collected_by: form.collected_by,
      collected_time: toFrappe(form.collected_time),
      num_print: form.num_print,
      sample_details: form.sample_details,
      received_condition: form.received_condition,
      rejection_reason_text: form.rejection_reason_text,
    }
    const payloadRows = rows.value.map((r) => ({
      observation_template: r.observation_template,
      sample: r.sample,
      sample_qty: r.sample_qty,
      collection_point: r.collection_point,
      collection_date_time: toFrappe(r.collection_date_time),
      status: r.status || 'Open',
    }))
    await collectionApi.saveCollection({ name, values, rows: payloadRows, collect: collect ? 1 : 0 })
    if (collect) {
      // Advance to the accession step, carrying the order context along.
      router.push(`/lab/sample/${name}${orderQuery ? `?order=${orderQuery}` : ''}`)
    } else {
      await load()
    }
  } catch (e: any) {
    error.value = e?.response?.data?.message || e?.message || 'Failed to save'
  } finally {
    saving.value = false
  }
}

function printLabel() {
  const params = new URLSearchParams({ doctype: 'Sample Collection', name, format: 'Specimen Label', no_letterhead: '0' })
  window.open(`/printview?${params.toString()}`, '_blank')
}
</script>

<template>
  <Topbar :title="`Sample Collection · ${name}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <WorkflowStepper :order="orderQuery" :sample="name" current="collection" />

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>

  <div v-else class="space-y-4 pb-24">
    <!-- Patient Details -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-semibold">Patient Details</h3>
        <StatusPill :status="form.collected_time ? 'Collected' : 'Pending'" />
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Patient</label>
          <div class="font-medium">{{ meta.patient_name || meta.patient || '—' }}</div>
          <div class="text-xs text-surface-400">{{ meta.patient }}</div>
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Series</label>
          <div class="text-surface-600">{{ meta.naming_series || '—' }}</div>
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Order (Service Request)</label>
          <button v-if="meta.service_request" class="text-brand-teal-600 hover:underline" @click="router.push(`/orders/${meta.service_request}`)">{{ meta.service_request }}</button>
          <span v-else>—</span>
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Sample Barcode</label>
          <input v-model="form.barcode" class="input" placeholder="Scan or type the tube barcode" />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Container / Tube</label>
          <Combobox
            :load-options="loadContainers" :option-key="optKey" :option-label="optLabel"
            :model-label="labelForName(form.container)" placeholder="Select…"
            @select="(o) => (form.container = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Collection Point</label>
          <Combobox
            :load-options="loadUnits" :option-key="optKey" :option-label="optLabel"
            :model-label="labelForName(form.collection_point)"
            :placeholder="units.length ? 'Select…' : 'No service units configured'"
            :disabled="!units.length"
            @select="(o) => (form.collection_point = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Referring Practitioner</label>
          <Combobox
            :load-options="loadPractitioners" :option-key="optKey" :option-label="optLabel"
            :model-label="labelForPractitioner(form.referring_practitioner)" placeholder="Search practitioner…"
            @select="(o) => (form.referring_practitioner = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Company</label>
          <Combobox
            :load-options="loadCompanies" :option-key="optKey" :option-label="optLabel"
            :model-label="labelForName(form.company)" placeholder="Select…"
            @select="(o) => (form.company = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Invoiced</label>
          <div class="text-surface-600">{{ meta.invoiced ? 'Yes' : 'No' }}</div>
        </div>
      </div>
    </div>

    <!-- Sample Details -->
    <div class="card p-5">
      <h3 class="font-semibold mb-4">Sample Details</h3>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Sample</label>
          <Combobox
            :load-options="loadSpecimens" :option-key="optKey" :option-label="optLabel"
            :model-label="labelForName(form.sample)" placeholder="Select sample…"
            @select="(o) => (form.sample = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">UOM</label>
          <div class="input bg-surface-50 text-surface-600">{{ form.sample_uom || '— (derived from Sample)' }}</div>
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Quantity</label>
          <input v-model.number="form.sample_qty" type="number" step="any" min="0" class="input" placeholder="0" />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Collected By</label>
          <Combobox
            :load-options="loadCollectors" :option-key="optKey" :option-label="optLabel"
            :model-label="labelForCollector(form.collected_by)" placeholder="Search user…"
            @select="(o) => (form.collected_by = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Collected On</label>
          <input v-model="form.collected_time" type="datetime-local" class="input" />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">No. of prints</label>
          <input v-model.number="form.num_print" type="number" min="0" class="input" placeholder="1" />
        </div>
      </div>
    </div>

    <!-- Samples (child table) -->
    <div class="card p-5">
      <div class="flex items-center justify-between mb-3">
        <h3 class="font-semibold">Samples</h3>
        <button class="btn-ghost !py-1.5 !text-xs" @click="addRow">+ Add Row</button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-surface-500 border-b border-surface-200">
              <th class="py-2 pr-3">Observation Template</th>
              <th class="pr-3">Sample</th>
              <th class="pr-3">Quantity</th>
              <th class="pr-3">Collection Point</th>
              <th class="pr-3">Collection Date Time</th>
              <th class="pr-3">Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rows.length"><td colspan="7" class="text-center text-surface-400 py-6">No rows</td></tr>
            <tr v-for="(r, i) in rows" :key="i" class="border-b border-surface-100">
              <td class="py-2 pr-3">
                <Combobox
                  :load-options="loadObsTemplates" :option-key="optKey" :option-label="optLabel"
                  :model-label="labelForName(r.observation_template || '')" placeholder="Select…"
                  @select="(o) => (r.observation_template = o.value)"
                />
              </td>
              <td class="pr-3">
                <Combobox
                  :load-options="loadSpecimens" :option-key="optKey" :option-label="optLabel"
                  :model-label="labelForName(r.sample || '')" placeholder="Select…"
                  @select="(o) => (r.sample = o.value)"
                />
              </td>
              <td class="pr-3"><input v-model.number="r.sample_qty" type="number" step="any" min="0" class="input !py-1.5 w-24" /></td>
              <td class="pr-3">
                <Combobox
                  :load-options="loadUnits" :option-key="optKey" :option-label="optLabel"
                  :model-label="labelForName(r.collection_point || '')" placeholder="Select…"
                  :disabled="!units.length"
                  @select="(o) => (r.collection_point = o.value)"
                />
              </td>
              <td class="pr-3"><input v-model="r.collection_date_time" type="datetime-local" class="input !py-1.5" /></td>
              <td class="pr-3">
                <select v-model="r.status" class="input !py-1.5">
                  <option>Open</option><option>Collected</option>
                </select>
              </td>
              <td><button class="text-status-danger text-xs hover:underline" @click="removeRow(i)">Remove</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Collection Details -->
    <div class="card p-5">
      <h3 class="font-semibold mb-4">Collection Details</h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
        <div class="sm:col-span-2">
          <label class="block text-xs text-surface-500 mb-1">Collection Details</label>
          <textarea v-model="form.sample_details" rows="2" class="input" placeholder="Notes about the collection"></textarea>
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Received Condition</label>
          <Combobox
            :load-options="loadConditions" :option-key="optKey" :option-label="optLabel"
            :model-label="form.received_condition"
            placeholder="Not recorded"
            @select="(o) => (form.received_condition = o.value)"
          />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Rejection Reason</label>
          <textarea v-model="form.rejection_reason_text" rows="2" class="input" placeholder="If rejected, why"></textarea>
        </div>
      </div>
    </div>

    <p v-if="error" class="text-sm text-status-danger">{{ error }}</p>

    <!-- Sticky action bar -->
    <div class="fixed bottom-0 left-0 right-0 bg-white border-t border-surface-200 px-6 py-3 flex justify-end gap-2 z-30">
      <button class="btn-ghost" @click="printLabel">Print Label</button>
      <button class="btn-ghost" :disabled="saving" @click="save(false)">{{ saving ? 'Saving…' : 'Save' }}</button>
      <button class="btn-primary" :disabled="saving" @click="save(true)">{{ saving ? 'Saving…' : 'Save & Mark Collected' }}</button>
    </div>
  </div>
</template>
