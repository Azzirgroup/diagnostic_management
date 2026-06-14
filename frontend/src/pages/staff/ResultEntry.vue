<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { resultsApi, type LabTestResult } from '@/api/adms'

// Enter results into a Lab Test's expanded child rows (Marley fans templates
// into normal/descriptive rows by type — Single/Compound/Descriptive/Grouped).
const route = useRoute()
const router = useRouter()
const lt = ref<LabTestResult | null>(null)
const saving = ref(false)
const error = ref('')
const orderQuery = route.query.order as string | undefined

const finalised = () => lt.value?.docstatus === 1

async function load() {
  try { lt.value = await resultsApi.getLabTest(route.params.name as string) }
  catch (e: any) { error.value = e?.message || 'Failed to load test' }
}
onMounted(load)

async function save(complete: boolean) {
  if (!lt.value) return
  saving.value = true; error.value = ''
  try {
    const res = await resultsApi.save({
      name: lt.value.name,
      normal: lt.value.normal_test_items.map((r) => ({ name: r.name, result_value: r.result_value ?? '', lab_test_comment: r.lab_test_comment ?? '' })),
      descriptive: lt.value.descriptive_test_items.map((r) => ({ name: r.name, result_value: r.result_value ?? '' })),
      complete: complete ? 1 : 0,
    })
    if (complete) {
      router.push(orderQuery ? `/orders/${orderQuery}` : '/lab/verification')
    } else {
      lt.value.status = res.status
      await load()
    }
  } catch (e: any) {
    error.value = e?.response?.data?.message || e?.message || 'Failed to save results'
  } finally { saving.value = false }
}

const hasRows = () => !!lt.value && (lt.value.normal_test_items.length > 0 || lt.value.descriptive_test_items.length > 0)
</script>

<template>
  <Topbar :title="`Results · ${lt?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="lt" class="space-y-4 max-w-3xl">
    <div class="card p-5">
      <div class="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 class="font-semibold text-lg">{{ lt.template || lt.name }}</h3>
          <div class="text-sm text-surface-500">{{ lt.patient_name || lt.patient }} · {{ lt.name }}</div>
        </div>
        <StatusPill :status="lt.status || 'Draft'" />
      </div>
    </div>

    <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg">{{ error }}</p>

    <div v-if="finalised()" class="card p-5 text-sm text-surface-500">
      Results are finalised (test Completed). Reopen via the desk form to amend.
    </div>

    <div v-if="!hasRows()" class="card p-5 text-sm text-surface-400">
      This test's template has no result components configured. Set the Lab Test Template's
      <span class="font-medium">type</span> (Single / Compound / Descriptive / Grouped) and its analytes,
      then create the order again so the result rows expand.
    </div>

    <!-- Numeric / Single / Compound results -->
    <div v-if="lt.normal_test_items.length" class="card p-5">
      <h3 class="font-semibold mb-3">Results</h3>
      <table class="w-full text-sm">
        <thead><tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2 pr-3">Analyte</th><th class="pr-3 w-40">Result</th><th class="pr-3">Unit</th><th class="pr-3">Reference Range</th><th>Comment</th>
        </tr></thead>
        <tbody>
          <tr v-for="r in lt.normal_test_items" :key="r.name" class="border-b border-surface-100">
            <td class="py-2 pr-3 font-medium">{{ r.lab_test_name }}</td>
            <td class="pr-3"><input v-model="r.result_value" :disabled="finalised()" class="input !py-1.5" /></td>
            <td class="pr-3 text-surface-500">{{ r.lab_test_uom || '—' }}</td>
            <td class="pr-3 text-surface-500 whitespace-pre-line">{{ r.normal_range || '—' }}</td>
            <td><input v-model="r.lab_test_comment" :disabled="finalised()" class="input !py-1.5" placeholder="—" /></td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Descriptive results -->
    <div v-if="lt.descriptive_test_items.length" class="card p-5">
      <h3 class="font-semibold mb-3">Descriptive Findings</h3>
      <div v-for="r in lt.descriptive_test_items" :key="r.name" class="mb-3">
        <label class="block text-xs text-surface-500 mb-1">{{ r.lab_test_particulars }}</label>
        <textarea v-model="r.result_value" :disabled="finalised()" rows="2" class="input"></textarea>
      </div>
    </div>

    <div v-if="hasRows() && !finalised()" class="flex justify-end gap-2">
      <button class="btn-ghost" :disabled="saving" @click="save(false)">{{ saving ? 'Saving…' : 'Save Draft' }}</button>
      <button class="btn-primary" :disabled="saving" @click="save(true)">{{ saving ? 'Saving…' : 'Save & Complete' }}</button>
    </div>
  </div>
  <div v-else-if="!error" class="card p-12 text-center text-surface-400">Loading test…</div>
</template>
