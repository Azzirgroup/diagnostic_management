<script setup lang="ts">
defineProps<{ icon?: string; label?: string; variant?: 'primary' | 'ghost' | 'danger' }>()
</script>

<template>
  <button
    :class="[
      'inline-flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
      variant === 'primary'
        ? 'bg-brand-navy-700 text-white hover:bg-brand-navy-800'
        : variant === 'danger'
          ? 'bg-white border border-status-danger/30 text-status-danger hover:bg-status-danger-bg'
          : 'bg-white border border-surface-200 text-surface-700 hover:bg-surface-50',
    ]"
  >
    <slot name="icon" />
    <slot>{{ label }}</slot>
  </button>
</template>
