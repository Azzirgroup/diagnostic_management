<script setup lang="ts" generic="T">
import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
import { onClickOutside } from '@vueuse/core'

// Searchable dropdown. Clicking the field opens the list and loads options
// (empty query = all); typing filters via `loadOptions`. Used for both
// single-select (pass `modelLabel`) and repeated multi-add (pass
// `clearOnSelect` + `keepOpenOnSelect`, e.g. adding tests to an order).
//
// The dropdown panel is teleported to <body> with position:fixed so it
// floats above any clipping ancestor (table wrappers with overflow, modals,
// etc.). Position is recomputed on any scroll or resize.
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
const inputEl = ref<HTMLInputElement | null>(null)
const panelEl = ref<HTMLElement | null>(null)
const query = ref('')
const open = ref(false)
const loading = ref(false)
const options = ref([]) as Ref<T[]>
const pos = ref({ top: 0, left: 0, width: 0 })
let timer: ReturnType<typeof setTimeout> | null = null

function updatePosition() {
  const el = inputEl.value
  if (!el) return
  const r = el.getBoundingClientRect()
  pos.value = { top: r.bottom + 4, left: r.left, width: r.width }
}

async function fetchOptions(q: string) {
  loading.value = true
  try { options.value = await props.loadOptions(q) } catch { options.value = [] }
  finally { loading.value = false }
}

function onFocus() {
  if (props.disabled) return
  open.value = true
  updatePosition()
  fetchOptions(query.value)
}
function onInput() {
  open.value = true
  updatePosition()
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
    updatePosition()
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
// Close on outside click — but the teleported panel is no longer inside
// `root`, so tell clickOutside to also ignore clicks landing on the panel.
onClickOutside(root, close, { ignore: [panelEl] })

watch(
  () => props.modelLabel,
  (v) => { if (v !== undefined) query.value = v || '' },
  { immediate: true },
)

// Keep the floating panel glued to the input on scroll/resize. `capture:true`
// catches scrolls on ANY ancestor (e.g. the table's overflow-x-auto wrapper).
onMounted(() => {
  window.addEventListener('scroll', updatePosition, true)
  window.addEventListener('resize', updatePosition)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', updatePosition, true)
  window.removeEventListener('resize', updatePosition)
})
</script>

<template>
  <div ref="root" class="relative">
    <input
      ref="inputEl"
      v-model="query"
      class="input"
      :placeholder="placeholder"
      :disabled="disabled"
      autocomplete="off"
      @focus="onFocus"
      @input="onInput"
      @keydown.esc="close"
    />
    <Teleport to="body">
      <div
        v-if="open"
        ref="panelEl"
        class="fixed z-[1000] max-h-64 overflow-y-auto bg-white border border-surface-200 rounded-lg shadow-card"
        :style="{ top: pos.top + 'px', left: pos.left + 'px', width: pos.width + 'px' }"
      >
        <div v-if="loading" class="px-3 py-3 text-sm text-surface-400">Loading…</div>
        <div v-else-if="!options.length" class="px-3 py-3 text-sm text-surface-400">No matches</div>
        <div
          v-for="item in options"
          :key="optionKey(item)"
          class="border-b border-surface-100 last:border-0"
        >
          <!-- `#row` slot wins when the caller wants a custom row (e.g. with a
               star button). It receives `item` plus the `choose` callback so it
               can still trigger the select. Default fallback = the original
               clickable row. -->
          <slot name="row" :item="item" :choose="choose">
            <button
              type="button"
              class="w-full text-left px-3 py-2 hover:bg-brand-teal-50/40"
              @click="choose(item)"
            >
              <div class="text-sm text-surface-800">{{ optionLabel(item) }}</div>
              <div v-if="optionSubtitle && optionSubtitle(item)" class="text-xs text-surface-500">{{ optionSubtitle(item) }}</div>
            </button>
          </slot>
        </div>
      </div>
    </Teleport>
  </div>
</template>
