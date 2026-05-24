<script setup lang="ts">
// Section header shim for ported genetest step components.
defineProps<{ sectionNumber?: number; title?: string; description?: string; color?: string }>()
</script>

<template>
  <div class="mb-6 flex items-center gap-3">
    <span class="w-8 h-8 rounded-full bg-brand-navy-700 text-white flex items-center justify-center text-sm font-semibold shrink-0">{{ sectionNumber }}</span>
    <div>
      <h2 class="text-lg font-semibold text-surface-800">{{ title }}</h2>
      <p v-if="description" class="text-sm text-surface-500">{{ description }}</p>
    </div>
  </div>
</template>
