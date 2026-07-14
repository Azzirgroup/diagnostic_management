<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import DataTable from '@/components/ui/DataTable.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import DetailPane from '@/components/ui/DetailPane.vue'
import { labApi, type PeerReviewRow } from '@/api/adms'
import { frappeError } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
// Peer review access rule: anyone can review EXCEPT the original reporter
// (the user who entered the results). No role gate — small labs may not
// have dedicated Lab Managers, so peers review each other. Server
// enforces the same rule via `_reject_self_review`.
const isOriginalReporter = computed(() =>
  !!selected.value?.original_reporter && selected.value.original_reporter === auth.user?.name,
)
// Amend follows the same rule now (was System Manager + Lab Manager only).
const canAmend = computed(() => !isOriginalReporter.value)

const rows = ref<PeerReviewRow[]>([])
const selected = ref<PeerReviewRow | null>(null)
const reviewNotes = ref('')
const busy = ref(false)
const amendError = ref('')
// Analytes for the currently-selected case — loaded on selection so the
// reviewer can see exactly what they're approving without navigating away.
const detail = ref<Awaited<ReturnType<typeof labApi.peerReviewDetail>> | null>(null)
const detailLoading = ref(false)

async function load() {
  try { rows.value = await labApi.peerReviewList() } catch { rows.value = [] }
}
onMounted(load)

// Load analytes each time a case is selected. Never blocks selecting a case;
// on error we just show a hint that the analytes couldn't load.
watch(selected, async (s) => {
  detail.value = null
  if (!s) return
  detailLoading.value = true
  try {
    detail.value = await labApi.peerReviewDetail(s.name)
  } catch (e: any) {
    amendError.value = frappeError(e, 'Failed to load results for review')
  } finally { detailLoading.value = false }
})

const kpis = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  const pending = rows.value.filter((r) => r.status === 'Open' || r.status === 'In Review').length
  const overdue = rows.value.filter((r) => r.due_date && r.due_date < today && r.status !== 'Closed').length
  const discussion = rows.value.filter((r) => r.status === 'Discussion').length
  const completed = rows.value.filter((r) => r.status === 'Closed').length
  return { pending, overdue, discussion, completed }
})

async function submit(outcome: string) {
  if (!selected.value) return
  busy.value = true; amendError.value = ''
  try {
    await labApi.submitPeerReview({ name: selected.value.name, outcome, review_notes: reviewNotes.value })
    reviewNotes.value = ''
    selected.value = null
    await load()
  } catch (e: any) {
    // Surface the actual server error inline (used to just swallow, which
    // combined with the old 403→logout interceptor made it look like a
    // silent logout).
    amendError.value = frappeError(e, 'Failed to submit peer review')
  } finally { busy.value = false }
}

// Close the case with outcome=Amend AND re-open the underlying Lab Tests so
// the technologist can edit the actual analyte values. Restricted server-side
// to System Manager + Lab Manager; the button is also hidden for other roles.
async function submitAmend() {
  if (!selected.value) return
  busy.value = true; amendError.value = ''
  try {
    const r = await labApi.submitPeerReviewAmend({
      name: selected.value.name,
      review_notes: reviewNotes.value,
      discrepancy_severity: 'Major',
    })
    reviewNotes.value = ''
    selected.value = null
    await load()
    alert(`Report ${r.report} sent back for amendment. ${r.amended_lab_tests.length} lab test(s) re-opened for editing.`)
  } catch (e: any) {
    amendError.value = frappeError(e, 'Failed to request amendment')
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Peer Review Queue" />
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
    <KpiCard label="Pending Reviews" :value="kpis.pending" icon-bg="rgb(239 246 255)" icon-color="rgb(29 78 216)" />
    <KpiCard label="Overdue" :value="kpis.overdue" icon-bg="rgb(254 226 226)" icon-color="rgb(185 28 28)" />
    <KpiCard label="In Discussion" :value="kpis.discussion" icon-bg="rgb(243 232 255)" icon-color="rgb(126 34 206)" />
    <KpiCard label="Completed" :value="kpis.completed" icon-bg="rgb(220 252 231)" icon-color="rgb(21 128 61)" />
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 card p-1">
      <DataTable
        :rows="rows"
        row-key="name"
        :selectable="true"
        @select="(r) => (selected = r as any)"
        empty-text="No peer review cases"
        :columns="[
          { key: 'name', label: 'Case ID' },
          { key: 'patient_name', label: 'Patient' },
          { key: 'modality', label: 'Test / Modality' },
          { key: 'original_reporter', label: 'Reporter' },
          { key: 'assigned_reviewer', label: 'Reviewer' },
          { key: 'due_date', label: 'Due Date' },
          { key: 'status', label: 'Status' },
        ]"
      >
        <template #cell-name="{ value }">
          <button class="text-brand-teal-600 hover:underline" @click.stop="$router.push(`/lab/peer-review/${value}`)">{{ value }}</button>
        </template>
        <template #cell-status="{ value }"><StatusPill :status="value as string"/></template>
      </DataTable>
    </div>
    <DetailPane v-if="selected" :title="selected.name" :subtitle="selected.patient_name || ''" @close="selected = null">
      <dl class="text-sm space-y-3">
        <div class="flex justify-between"><dt class="text-surface-500">Modality / Test</dt><dd>{{ selected.modality || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reporter</dt><dd>{{ selected.original_reporter || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Reviewer</dt><dd>{{ selected.assigned_reviewer || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Due</dt><dd>{{ selected.due_date || '—' }}</dd></div>
        <div class="flex justify-between"><dt class="text-surface-500">Status</dt><dd><StatusPill :status="selected.status" /></dd></div>
      </dl>

      <!-- Read-only analytes so the reviewer sees exactly what they are
           approving (results, ranges, flagged status) on the SAME page. -->
      <div class="mt-4 border-t border-surface-100 pt-3">
        <h4 class="text-sm font-semibold text-surface-800 mb-2">Results to review</h4>
        <div v-if="detailLoading" class="text-xs text-surface-400">Loading results…</div>
        <div v-else-if="!detail?.lab_tests?.length" class="text-xs text-surface-400">No results found for this case.</div>
        <div v-else>
          <div v-for="t in detail.lab_tests" :key="t.name" class="mb-3">
            <div class="text-xs font-semibold text-surface-700 mb-1">{{ t.template || t.name }}</div>
            <table v-if="t.normal_test_items?.length" class="w-full text-xs">
              <thead>
                <tr class="text-left text-surface-500 border-b border-surface-200">
                  <th class="py-1 pr-2">Analyte</th>
                  <th class="pr-2">Result</th>
                  <th class="pr-2">Unit</th>
                  <th class="pr-2">Reference</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in t.normal_test_items" :key="r.name" class="border-b border-surface-50">
                  <td class="py-1 pr-2">{{ r.lab_test_name }}</td>
                  <td class="pr-2 font-mono" :class="r.status && r.status !== 'Normal' ? 'text-status-danger font-semibold' : ''">{{ r.result_value || '—' }}</td>
                  <td class="pr-2 text-surface-500">{{ r.lab_test_uom || '—' }}</td>
                  <td class="pr-2 text-surface-500 whitespace-pre-line">{{ r.normal_range || '—' }}</td>
                  <td><StatusPill :status="r.status || 'Normal'" /></td>
                </tr>
              </tbody>
            </table>
            <div v-for="r in (t.descriptive_test_items || [])" :key="r.name" class="text-xs mb-2">
              <div class="text-surface-500">{{ r.lab_test_particulars }}</div>
              <div class="whitespace-pre-line">{{ r.result_value || '—' }}</div>
            </div>
          </div>
          <div v-if="detail?.diagnostic_report?.conclusion" class="mt-2 p-2 rounded bg-surface-50 text-xs">
            <div class="text-surface-500 mb-0.5">Reporter's conclusion</div>
            <div class="whitespace-pre-line">{{ detail.diagnostic_report.conclusion }}</div>
          </div>
        </div>
      </div>

      <button v-if="detail?.workflow_session" class="btn-ghost w-full mt-3 !text-xs"
              @click="$router.push(`/workflow/${detail.workflow_session}`)">
        ↩ Open Lab Workflow ({{ detail.workflow_session }})
      </button>

      <label class="block text-xs text-surface-500 mt-4 mb-1">Review Notes (Required)</label>
      <textarea v-model="reviewNotes" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" rows="4" placeholder="Enter your comparison, comments, or additional findings..."></textarea>
      <!-- Self-review guard: the user who entered the results can't close
           their own case. Hide the submit buttons entirely with a clear
           reason so the next reviewer knows to log in. -->
      <div v-if="isOriginalReporter" class="mt-4 p-3 bg-amber-50 border border-amber-200 rounded text-sm text-amber-800">
        You entered these results — someone else must peer-review this case.
        Ask a colleague to log in and close it.
      </div>
      <template v-else>
        <p v-if="!reviewNotes.trim()" class="text-xs text-amber-600 mt-2">
          Enter Review Notes above to enable the submit buttons.
        </p>
        <button class="btn-primary w-full mt-4" :disabled="busy || !reviewNotes.trim()"
                :title="!reviewNotes.trim() ? 'Enter Review Notes first' : ''"
                @click="submit('Agree')">Submit · Agree</button>
        <button class="btn-secondary w-full mt-2" :disabled="busy || !reviewNotes.trim()"
                :title="!reviewNotes.trim() ? 'Enter Review Notes first' : ''"
                @click="submit('Minor Disagreement')">Submit · Minor Disagree</button>
        <button class="btn-danger-ghost w-full mt-2" :disabled="busy || !reviewNotes.trim()"
                :title="!reviewNotes.trim() ? 'Enter Review Notes first' : ''"
                @click="submit('Major Disagreement')">Submit · Major Disagree</button>
        <button
          v-if="canAmend"
          class="btn-danger w-full mt-2"
          :disabled="busy || !reviewNotes.trim()"
          :title="'Closes the case with outcome=Amendment Required AND re-opens the underlying Lab Tests for editing.'"
          @click="submitAmend"
        >
          Submit &amp; Amend (re-open results for editing)
        </button>
      </template>
      <p v-if="amendError" class="text-status-danger text-xs mt-2">{{ amendError }}</p>
    </DetailPane>
    <div v-else class="card p-6 text-center text-surface-400">Select a case to review</div>
  </div>
</template>
