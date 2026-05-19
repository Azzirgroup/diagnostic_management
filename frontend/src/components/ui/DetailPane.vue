<script setup lang="ts">
defineProps<{ title?: string; subtitle?: string }>()
const emit = defineEmits<{ (e: 'close'): void }>()
</script>

<template>
  <div class="card p-6 sticky top-4">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h3 class="text-lg font-semibold text-surface-800">{{ title }}</h3>
        <p v-if="subtitle" class="text-sm text-surface-500 mt-0.5">{{ subtitle }}</p>
      </div>
      <button class="text-surface-400 hover:text-surface-700" @click="emit('close')">
        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
    <slot />
  </div>
</template>
