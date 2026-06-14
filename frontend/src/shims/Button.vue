<script setup lang="ts">
// frappe-ui <Button> shim. Accepts the same props but only renders styling
// for variant/theme/size combinations actually used in the ported pages.
import { computed } from 'vue'
const props = defineProps<{
  variant?: 'solid' | 'outline' | 'ghost'
  theme?: 'gray' | 'blue' | 'red' | 'green'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
}>()
const cls = computed(() => {
  const base = ['inline-flex items-center gap-1 rounded font-medium transition disabled:opacity-50 disabled:cursor-not-allowed']
  const size = props.size === 'sm' ? 'px-2 py-1 text-xs' : props.size === 'lg' ? 'px-4 py-2 text-base' : 'px-3 py-1.5 text-sm'
  let color: string
  if (props.variant === 'outline') {
    color = props.theme === 'blue' ? 'border border-blue-500 text-blue-700 hover:bg-blue-50'
          : props.theme === 'red'  ? 'border border-red-500  text-red-700  hover:bg-red-50'
          : props.theme === 'green'? 'border border-emerald-500 text-emerald-700 hover:bg-emerald-50'
          : 'border border-surface-300 text-surface-700 hover:bg-surface-50'
  } else if (props.variant === 'ghost') {
    color = 'text-surface-700 hover:bg-surface-100'
  } else {
    // solid (default)
    color = props.theme === 'red'   ? 'bg-red-600 text-white hover:bg-red-700'
          : props.theme === 'green' ? 'bg-emerald-600 text-white hover:bg-emerald-700'
          : props.theme === 'gray'  ? 'bg-surface-700 text-white hover:bg-surface-800'
          : 'bg-blue-600 text-white hover:bg-blue-700'
  }
  return [...base, size, color].join(' ')
})
</script>

<template>
  <button :class="cls" :disabled="disabled || loading" type="button">
    <slot name="prefix" />
    <span v-if="loading" class="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin"></span>
    <slot />
    <slot name="suffix" />
  </button>
</template>
