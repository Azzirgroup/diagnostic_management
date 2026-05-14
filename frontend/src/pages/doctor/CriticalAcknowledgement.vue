<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Topbar from '@/components/layout/Topbar.vue'
import { call, getDoc } from '@/api/client'

const route = useRoute()
const router = useRouter()
const ack = ref(false)
const comment = ref('')
const submitting = ref(false)
const report = ref<any>(null)

const patientName = computed(() => report.value?.patient_name || '—')
const patientMrn = computed(() => report.value?.patient || '—')
const initials = computed(() => {
  const n = patientName.value
  if (!n || n === '—') return '—'
  return n.split(' ').slice(0, 2).map((s: string) => s[0]).join('').toUpperCase()
})

onMounted(async () => {
  try {
    report.value = await getDoc<any>('Diagnostic Report', route.params.name as string)
  } catch {
    report.value = null
  }
})

async function submit() {
  if (!ack.value) return
  submitting.value = true
  try {
    await call('diagnostic_management.api.critical.acknowledge', {
      report: route.params.name,
      notes: comment.value,
    })
    router.push('/doctor/results')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <Topbar title="Critical Result Acknowledgement" />
  <div class="card p-5 mb-4 flex items-center gap-6">
    <div class="w-14 h-14 rounded-full bg-brand-teal-100 text-brand-teal-700 flex items-center justify-center font-semibold">{{ initials }}</div>
    <div>
      <div class="font-semibold">{{ patientName }}</div>
      <div class="text-xs text-surface-500">MRN: {{ patientMrn }}</div>
    </div>
    <div class="text-sm text-surface-500 ml-auto">{{ report?.docname || report?.name || '—' }}</div>
    <span class="pill-danger">CRITICAL</span>
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Report Summary</h3>
      <div class="text-status-danger text-sm font-semibold mb-2">Critical Finding</div>
      <div class="card p-3 bg-status-danger-bg/30 mb-4">
        <div class="font-medium">{{ report?.docname || '—' }}</div>
        <div class="text-xs text-surface-500">{{ report?.status || 'Pending' }}</div>
      </div>
      <div class="text-sm font-semibold text-surface-800">Interpretation</div>
      <p class="text-sm text-surface-600 mt-1">{{ report?.conclusion || '—' }}</p>
    </div>
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Acknowledgement</h3>
      <div class="bg-status-danger-bg/30 border border-status-danger/30 rounded-lg p-3 mb-4">
        <div class="text-status-danger font-semibold">Critical Result</div>
        <p class="text-sm text-surface-700 mt-1">
          This result is outside the critical range and requires your acknowledgement.
        </p>
      </div>
      <label class="flex items-start gap-2 text-sm cursor-pointer">
        <input type="checkbox" v-model="ack" class="mt-1 accent-brand-teal-500" />
        <span>I acknowledge that I have reviewed this critical result.</span>
      </label>
      <label class="block text-xs text-surface-500 mt-4 mb-1">Comment (Optional)</label>
      <textarea v-model="comment" class="input" rows="4" placeholder="Add any relevant notes regarding this result..." maxlength="500"></textarea>
      <button class="btn-primary w-full mt-4" :disabled="!ack || submitting" @click="submit">
        {{ submitting ? 'Submitting…' : 'Acknowledge Critical Result' }}
      </button>
    </div>
  </div>
</template>
