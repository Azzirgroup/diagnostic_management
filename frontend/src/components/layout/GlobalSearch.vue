<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { scanApi, patientsApi, type PatientLite } from '@/api/adms'

// Global scan / quick-lookup box (the topbar search). Press ⌘K / Ctrl+K to
// focus. Type or scan a code and press Enter: a barcode/id resolves to the
// matching record (sample, order, patient, invoice) and navigates there;
// otherwise it falls back to patient suggestions shown as you type.
const router = useRouter()
const root = ref<HTMLElement | null>(null)
const inputRef = ref<HTMLInputElement | null>(null)
const query = ref('')
const open = ref(false)
const loading = ref(false)
const patients = ref<PatientLite[]>([])
const message = ref('')
let timer: ReturnType<typeof setTimeout> | null = null

function onInput() {
  open.value = true
  message.value = ''
  if (timer) clearTimeout(timer)
  const q = query.value.trim()
  if (!q) { patients.value = []; return }
  timer = setTimeout(async () => {
    loading.value = true
    try { patients.value = await patientsApi.search(q, 6) } catch { patients.value = [] }
    finally { loading.value = false }
  }, 200)
}

async function onEnter() {
  const q = query.value.trim()
  if (!q) return
  message.value = ''
  try {
    const res = await scanApi.resolve(q)
    if (res.found && res.route) { go(res.route); return }
  } catch { /* ignore, fall back below */ }
  if (patients.value.length === 1) { go(`/patients/${patients.value[0].name}`); return }
  message.value = `No record matches "${q}"`
}

function go(route: string) {
  query.value = ''
  patients.value = []
  open.value = false
  message.value = ''
  router.push(route)
}

function onGlobalKey(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    open.value = true
    inputRef.value?.focus()
  }
}
onMounted(() => window.addEventListener('keydown', onGlobalKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKey))
onClickOutside(root, () => { open.value = false })
</script>

<template>
  <div ref="root" class="relative">
    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>
      </svg>
    </span>
    <input
      ref="inputRef"
      v-model="query"
      class="input pl-9 pr-12"
      placeholder="Scan or search patients, orders, samples…"
      autocomplete="off"
      @focus="open = true"
      @input="onInput"
      @keydown.enter="onEnter"
      @keydown.esc="open = false"
    />
    <span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-surface-400 border border-surface-200 rounded px-1.5 py-0.5">⌘ K</span>

    <div v-if="open && (query || patients.length || message)" class="absolute z-40 mt-1 w-full max-h-72 overflow-y-auto bg-white border border-surface-200 rounded-lg shadow-card">
      <div v-if="loading" class="px-3 py-3 text-sm text-surface-400">Searching…</div>
      <template v-else>
        <button
          v-for="p in patients"
          :key="p.name"
          type="button"
          class="w-full text-left px-3 py-2 hover:bg-brand-teal-50/40 border-b border-surface-100 last:border-0"
          @click="go(`/patients/${p.name}`)"
        >
          <div class="text-sm text-surface-800">{{ p.patient_name || p.name }}</div>
          <div class="text-xs text-surface-500">{{ p.sex || '—' }}<span v-if="p.mobile"> · {{ p.mobile }}</span> · {{ p.name }}</div>
        </button>
        <div v-if="query && !patients.length && !message" class="px-3 py-3 text-sm text-surface-400">
          Press <span class="border border-surface-200 rounded px-1 text-xs">Enter</span> to open "{{ query.trim() }}"
        </div>
        <div v-if="message" class="px-3 py-3 text-sm text-status-danger">{{ message }}</div>
      </template>
    </div>
  </div>
</template>
