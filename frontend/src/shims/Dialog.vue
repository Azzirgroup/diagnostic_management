<script setup lang="ts">
// frappe-ui <Dialog> shim: v-model open/close + an options object carrying
// title + size. Mimics the API just enough for the ported pages.
import { computed } from 'vue'
const props = defineProps<{
  modelValue: boolean
  options?: { title?: string; size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' }
}>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void }>()
function close() { emit('update:modelValue', false) }
const widthCls = computed(() => {
  const s = props.options?.size
  if (s === 'sm') return 'max-w-sm'
  if (s === 'lg') return 'max-w-2xl'
  if (s === 'xl') return 'max-w-4xl'
  if (s === '2xl') return 'max-w-6xl'
  return 'max-w-lg'
})
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue"
      class="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-16 px-4"
      @click.self="close">
      <div :class="['w-full', widthCls, 'bg-white rounded-lg shadow-xl flex flex-col max-h-[80vh]']">
        <header class="px-5 py-3 border-b border-surface-100 flex items-center justify-between">
          <h3 class="text-base font-semibold text-surface-800">{{ options?.title || '' }}</h3>
          <button type="button" class="text-surface-500 hover:text-surface-800" @click="close" aria-label="Close">✕</button>
        </header>
        <!-- The ported pages use a `#body-main` slot for form content; render
             both that AND the default slot so older usage still works. -->
        <div class="overflow-y-auto">
          <slot name="body-main" />
          <slot />
        </div>
        <footer class="px-5 py-3 border-t border-surface-100 flex items-center justify-end gap-2">
          <slot name="actions" />
        </footer>
      </div>
    </div>
  </Teleport>
</template>
