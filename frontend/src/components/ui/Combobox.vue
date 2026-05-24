<script setup lang="ts" generic="T">
import { ref, watch, type Ref } from 'vue'
import { onClickOutside } from '@vueuse/core'

// Searchable dropdown. Clicking the field opens the list and loads options
// (empty query = all); typing filters via `loadOptions`. Used for both
// single-select (pass `modelLabel`) and repeated multi-add (pass
// `clearOnSelect` + `keepOpenOnSelect`, e.g. adding tests to an order).
const props = defineProps<{
  placeholder?: string
  loadOptions: (q: string) => Promise<T[]>
  optionKey: (item: T) => string
  optionLabel: (item: T) => string
  optionSubtitle?: (item: T) => string
  modelLabel?: string
  clearOnSelect?: boolean
  keepOpenOnSelect?: boolean
  disabled?: boolean
}>()
const emit = defineEmits<{ (e: 'select', item: T): void }>()

const root = ref<HTMLElement | null>(null)
const query = ref('')
const open = ref(false)
const loading = ref(false)
const options = ref([]) as Ref<T[]>
let timer: ReturnType<typeof setTimeout> | null = null

async function fetchOptions(q: string) {
  loading.value = true
  try { options.value = await props.loadOptions(q) } catch { options.value = [] }
  finally { loading.value = false }
}

function onFocus() {
  if (props.disabled) return
  open.value = true
  fetchOptions(query.value)
}
function onInput() {
  open.value = true
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => fetchOptions(query.value), 200)
}
function choose(item: T) {
  emit('select', item)
  if (props.clearOnSelect) {
    query.value = ''
  } else {
    query.value = props.optionLabel(item)
  }
  if (props.keepOpenOnSelect) {
    fetchOptions(query.value)
  } else {
    open.value = false
  }
}
function close() {
  open.value = false
  // Single-select: snap the box back to the selected label so a half-typed
  // search doesn't linger. Multi-add boxes (no modelLabel) keep their text.
  if (props.modelLabel !== undefined) query.value = props.modelLabel || ''
}
onClickOutside(root, close)

watch(
  () => props.modelLabel,
  (v) => { if (v !== undefined) query.value = v || '' },
  { immediate: true },
)
</script>

<template>
  <div ref="root" class="relative">
    <input
      v-model="query"
      class="input"
      :placeholder="placeholder"
      :disabled="disabled"
      autocomplete="off"
      @focus="onFocus"
      @input="onInput"
      @keydown.esc="close"
    />
    <div
      v-if="open"
      class="absolute z-40 mt-1 w-full max-h-64 overflow-y-auto bg-white border border-surface-200 rounded-lg shadow-card"
    >
      <div v-if="loading" class="px-3 py-3 text-sm text-surface-400">Loading…</div>
      <div v-else-if="!options.length" class="px-3 py-3 text-sm text-surface-400">No matches</div>
      <button
        v-for="item in options"
        :key="optionKey(item)"
        type="button"
        class="w-full text-left px-3 py-2 hover:bg-brand-teal-50/40 border-b border-surface-100 last:border-0"
        @click="choose(item)"
      >
        <div class="text-sm text-surface-800">{{ optionLabel(item) }}</div>
        <div v-if="optionSubtitle && optionSubtitle(item)" class="text-xs text-surface-500">{{ optionSubtitle(item) }}</div>
      </button>
    </div>
  </div>
</template>
