<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import { checkinApi, type CheckinStatus, type CheckinToday, type CheckinRow } from '@/api/adms'
import { frappeError } from '@/api/client'

// Personal Check-In page — the calling user clocks IN at the start of their
// day and OUT when they leave. Each click hits HRMS's Employee Checkin
// doctype via diagnostic_management.api.checkin.*; visibility is scoped to
// the current user's own employee record.

const status = ref<CheckinStatus | null>(null)
const today = ref<CheckinToday | null>(null)
const history = ref<CheckinRow[]>([])
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const flash = ref('')

// Live wall-clock for the big "now" display.
const now = ref(new Date())
let tick: ReturnType<typeof setInterval> | null = null

async function loadAll() {
  loading.value = true; error.value = ''
  try {
    const [s, t, h] = await Promise.all([
      checkinApi.status(),
      checkinApi.myToday(),
      checkinApi.myHistory(30),
    ])
    status.value = s; today.value = t; history.value = h
  } catch (e: any) {
    error.value = frappeError(e, 'Failed to load check-in data')
  } finally { loading.value = false }
}

async function clockIn() {
  busy.value = true; error.value = ''
  try {
    const r = await checkinApi.clockIn()
    flash.value = `Clocked IN at ${formatTime(r.time)}`
    setTimeout(() => { flash.value = '' }, 2500)
    await loadAll()
  } catch (e: any) { error.value = frappeError(e, 'Clock In failed') }
  finally { busy.value = false }
}

async function clockOut() {
  busy.value = true; error.value = ''
  try {
    const r = await checkinApi.clockOut()
    flash.value = `Clocked OUT at ${formatTime(r.time)}`
    setTimeout(() => { flash.value = '' }, 2500)
    await loadAll()
  } catch (e: any) { error.value = frappeError(e, 'Clock Out failed') }
  finally { busy.value = false }
}

onMounted(() => {
  loadAll()
  tick = setInterval(() => { now.value = new Date() }, 1000)
})
onBeforeUnmount(() => { if (tick) clearInterval(tick) })

// ────────────── helpers ──────────────
function pad(n: number) { return n < 10 ? '0' + n : '' + n }
function formatClock(d: Date) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
function formatDate(d: Date) {
  return d.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })
}
function formatTime(ts: string) {
  if (!ts) return '—'
  const d = new Date(ts.replace(' ', 'T'))
  if (isNaN(d.getTime())) return ts
  return d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}
function formatDateTime(ts: string) {
  if (!ts) return '—'
  const d = new Date(ts.replace(' ', 'T'))
  if (isNaN(d.getTime())) return ts
  return d.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
function formatDuration(mins: number | null | undefined) {
  if (mins == null) return '—'
  if (mins < 60) return `${mins.toFixed(0)} min`
  const h = Math.floor(mins / 60); const m = Math.round(mins % 60)
  return `${h}h ${pad(m)}m`
}

const totalMinutesPretty = computed(() => formatDuration(today.value?.total_minutes ?? 0))

// Group history by day for the list display.
const historyByDay = computed(() => {
  const out: Record<string, CheckinRow[]> = {}
  for (const r of history.value) {
    const day = (r.time || '').slice(0, 10)
    if (!out[day]) out[day] = []
    out[day].push(r)
  }
  return out
})
</script>

<template>
  <Topbar title="Check-In" subtitle="Clock in when you start, clock out when you leave" />

  <div v-if="error" class="card mb-4 p-3 text-sm text-red-700 bg-red-50 border-l-4 border-red-500">{{ error }}</div>
  <div v-if="flash" class="card mb-4 p-3 text-sm text-emerald-700 bg-emerald-50 border-l-4 border-emerald-500">{{ flash }}</div>

  <!-- Live clock + main action -->
  <div class="card p-6 mb-4 text-center">
    <div class="text-sm text-surface-500">{{ formatDate(now) }}</div>
    <div class="text-5xl font-bold text-surface-800 mt-2 tabular-nums tracking-tight">{{ formatClock(now) }}</div>
    <div class="mt-1 text-sm text-surface-500">
      <span v-if="status?.employee">{{ status.employee.employee_name }} · <span class="text-surface-400">{{ status.employee.name }}</span></span>
      <span v-else-if="loading">Loading…</span>
    </div>

    <div class="mt-5 flex items-center justify-center gap-3">
      <button
        v-if="!status?.is_in"
        class="px-6 py-3 rounded-lg bg-emerald-600 text-white font-semibold hover:bg-emerald-700 disabled:opacity-50"
        :disabled="busy || loading || !status?.employee"
        @click="clockIn">
        {{ busy ? 'Clocking in…' : '🟢 Clock In' }}
      </button>
      <button
        v-else
        class="px-6 py-3 rounded-lg bg-red-600 text-white font-semibold hover:bg-red-700 disabled:opacity-50"
        :disabled="busy"
        @click="clockOut">
        {{ busy ? 'Clocking out…' : '🔴 Clock Out' }}
      </button>
    </div>

    <div v-if="status?.last_log" class="mt-3 text-xs text-surface-500">
      Last log: <span :class="status.is_in ? 'text-emerald-700 font-medium' : 'text-red-700 font-medium'">{{ status.last_log.log_type }}</span>
      at {{ formatDateTime(status.last_log.time) }}
    </div>
  </div>

  <!-- Today: paired sessions + total -->
  <div class="card p-4 mb-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="font-semibold text-sm">Today</h3>
      <span class="text-xs text-surface-500">
        Total worked: <span class="font-medium text-surface-700">{{ totalMinutesPretty }}</span>
      </span>
    </div>
    <div v-if="!today || today.sessions.length === 0" class="text-sm text-surface-400 text-center py-4">
      No check-ins yet today.
    </div>
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="text-left text-surface-500 border-b border-surface-200">
          <th class="py-2">In</th>
          <th class="py-2">Out</th>
          <th class="py-2 text-right">Duration</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="s in today.sessions" :key="s.in_name" class="border-b border-surface-100">
          <td class="py-2 text-emerald-700 font-medium">{{ formatTime(s.in_time) }}</td>
          <td class="py-2" :class="s.out_time ? 'text-red-700 font-medium' : 'text-surface-400'">
            {{ s.out_time ? formatTime(s.out_time) : '— still in —' }}
          </td>
          <td class="py-2 text-right">{{ formatDuration(s.duration_minutes) }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <!-- Recent history -->
  <div class="card p-4">
    <h3 class="font-semibold text-sm mb-3">Recent History</h3>
    <div v-if="!history.length" class="text-sm text-surface-400 text-center py-4">
      No previous check-ins.
    </div>
    <div v-else class="space-y-3">
      <div v-for="(rows, day) in historyByDay" :key="day">
        <div class="text-xs uppercase tracking-wide text-surface-500 mb-1">{{ day }}</div>
        <div class="space-y-1">
          <div v-for="r in rows" :key="r.name"
            class="flex items-center justify-between px-3 py-1.5 rounded border border-surface-100 text-sm">
            <span class="flex items-center gap-2">
              <span :class="['text-xs font-bold px-1.5 py-0.5 rounded',
                              r.log_type === 'IN' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700']">
                {{ r.log_type }}
              </span>
              <span class="text-surface-700">{{ formatTime(r.time) }}</span>
            </span>
            <span class="text-xs text-surface-400">{{ r.device_id || '' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
