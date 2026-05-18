<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { call } from '@/api/client'

interface LogEntry {
  name: string
  severity?: string
  status?: string
  detected_at?: string
  notified_at?: string
  acknowledged_at?: string
  acknowledged_by?: string
  ack_notes?: string
  notification_channel?: string
  escalation_level?: number
  test_or_modality?: string
  summary?: string
}

interface CriticalDetail {
  name: string
  patient?: string
  patient_name?: string
  practitioner?: string
  status: string
  is_critical?: number
  critical_acknowledged?: number
  critical_acknowledged_at?: string
  creation?: string
  title?: string
  docname?: string
  ref_doctype?: string
  log: LogEntry[]
}

const route = useRoute()
const router = useRouter()
const report = ref<CriticalDetail | null>(null)
const loading = ref(false)
const notes = ref('')
const busy = ref(false)
const error = ref('')

async function load() {
  loading.value = true
  try {
    report.value = await call<CriticalDetail>('diagnostic_management.api.critical.detail', { report: route.params.name as string })
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to load critical finding'
  } finally { loading.value = false }
}
onMounted(load)

const isAcked = computed(() => !!report.value?.critical_acknowledged)

async function acknowledge() {
  if (!report.value) return
  busy.value = true
  error.value = ''
  try {
    await call('diagnostic_management.api.critical.acknowledge', {
      report: report.value.name,
      notes: notes.value,
    })
    notes.value = ''
    await load()
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to acknowledge'
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar :title="`Critical Finding · ${report?.name || ''}`" />
  <button class="text-sm text-brand-teal-600 hover:underline mb-3" @click="router.back()">← Back</button>

  <div v-if="loading" class="card p-12 text-center text-surface-400">Loading…</div>
  <div v-else-if="!report" class="card p-12 text-center text-surface-400">
    Critical finding not found.
    <button class="btn-ghost block mx-auto mt-3" @click="router.push('/critical-findings')">Back to list</button>
  </div>

  <div v-else class="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <div class="lg:col-span-2 space-y-4">
      <div class="card p-5">
        <div class="flex items-start justify-between flex-wrap gap-3">
          <div>
            <h3 class="font-semibold text-lg">{{ report.patient_name || report.name }}</h3>
            <div class="text-xs text-surface-500 mt-1">Report {{ report.docname || report.name }} · MRN {{ report.patient || '—' }}</div>
          </div>
          <div class="flex items-center gap-2">
            <span class="pill-danger">CRITICAL</span>
            <StatusPill :status="report.status" />
            <span v-if="isAcked" class="pill-success">Acknowledged</span>
          </div>
        </div>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-3">Report Summary</h3>
        <dl class="text-sm grid grid-cols-2 gap-y-2">
          <dt class="text-surface-500">Title</dt><dd>{{ report.title || '—' }}</dd>
          <dt class="text-surface-500">Linked Doc</dt><dd>{{ report.ref_doctype ? `${report.ref_doctype} / ${report.docname || '—'}` : '—' }}</dd>
          <dt class="text-surface-500">Practitioner</dt><dd>{{ report.practitioner || '—' }}</dd>
        </dl>
      </div>

      <div class="card p-5">
        <h3 class="font-semibold mb-4">Escalation Timeline</h3>
        <div v-if="!report.log || !report.log.length" class="text-sm text-surface-400 py-4">
          No log entries yet. The first entry will be created when this finding is detected by the lab/radiology workflow.
        </div>
        <ol v-else class="space-y-3">
          <li v-for="(l, i) in report.log" :key="l.name" class="flex gap-3 text-sm">
            <div class="flex flex-col items-center">
              <div :class="[
                'w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold',
                l.status === 'Acknowledged' ? 'bg-status-success-bg text-status-success'
                  : l.status === 'Escalated' ? 'bg-status-danger-bg text-status-danger'
                  : 'bg-status-warning-bg text-status-warning']">
                {{ i + 1 }}
              </div>
              <div v-if="i < report.log.length - 1" class="w-px h-full bg-surface-200 mt-1"></div>
            </div>
            <div class="flex-1 pb-3">
              <div class="flex items-center gap-2">
                <strong>{{ l.status }}</strong>
                <span v-if="l.severity" class="pill-warning text-xs">{{ l.severity }}</span>
                <span v-if="l.escalation_level" class="pill-danger text-xs">Level {{ l.escalation_level }}</span>
              </div>
              <div class="text-xs text-surface-500 mt-0.5">
                {{ l.detected_at || l.notified_at || l.acknowledged_at }}
                <span v-if="l.acknowledged_by"> · by {{ l.acknowledged_by }}</span>
                <span v-if="l.notification_channel"> · via {{ l.notification_channel }}</span>
              </div>
              <p v-if="l.summary" class="text-sm mt-1 text-surface-700">{{ l.summary }}</p>
              <p v-if="l.ack_notes" class="text-sm mt-1 text-status-success">"{{ l.ack_notes }}"</p>
            </div>
          </li>
        </ol>
      </div>
    </div>

    <div class="space-y-4">
      <div class="card p-5">
        <h3 class="font-semibold mb-3">Summary</h3>
        <dl class="text-sm space-y-2">
          <div class="flex justify-between"><dt class="text-surface-500">Practitioner</dt><dd>{{ report.practitioner || '—' }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Created</dt><dd>{{ report.creation?.split('.')[0] }}</dd></div>
          <div class="flex justify-between"><dt class="text-surface-500">Acknowledged</dt><dd>{{ isAcked ? 'Yes' : 'No' }}</dd></div>
          <div v-if="report.critical_acknowledged_at" class="flex justify-between"><dt class="text-surface-500">Ack At</dt><dd>{{ report.critical_acknowledged_at }}</dd></div>
        </dl>
      </div>

      <div v-if="!isAcked" class="card p-5">
        <h3 class="font-semibold mb-3">Acknowledge</h3>
        <label class="block text-xs text-surface-500 mb-1">Notes (optional)</label>
        <textarea v-model="notes" rows="3" placeholder="Patient contacted, treatment initiated…" class="w-full px-3 py-2 rounded border border-surface-200 text-sm mb-3"></textarea>
        <p v-if="error" class="text-sm text-status-danger mb-2">{{ error }}</p>
        <button class="btn-primary w-full" :disabled="busy" @click="acknowledge">
          {{ busy ? 'Acknowledging…' : 'Acknowledge Critical Result' }}
        </button>
      </div>
      <div v-else class="card p-5 text-sm text-surface-500">
        This finding was acknowledged{{ report.critical_acknowledged_at ? ' on ' + report.critical_acknowledged_at : '' }}.
      </div>
    </div>
  </div>
</template>
