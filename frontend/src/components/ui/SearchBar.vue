<script setup lang="ts">
defineProps<{ modelValue?: string; placeholder?: string; showKbdHint?: boolean }>()
defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <div class="relative">
    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M11 19a8 8 0 100-16 8 8 0 000 16z"/>
      </svg>
    </span>
    <input
      class="input pl-9 pr-12"
      :value="modelValue"
      :placeholder="placeholder || 'Search...'"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
    <span v-if="showKbdHint" class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-surface-400 border border-surface-200 rounded px-1.5 py-0.5">
      ⌘ K
    </span>
  </div>
</template>
