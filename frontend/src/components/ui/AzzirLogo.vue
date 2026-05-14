<script setup lang="ts">
defineProps<{ subtitle?: string; size?: 'sm' | 'md' | 'lg' }>()
</script>

<template>
  <div class="flex items-center gap-3">
    <div
      :class="size === 'lg' ? 'w-16 h-16' : size === 'sm' ? 'w-8 h-8' : 'w-12 h-12'"
      class="rounded-xl bg-brand-navy-700 text-white flex items-center justify-center shrink-0"
    >
      <svg
        :class="size === 'lg' ? 'w-9 h-9' : size === 'sm' ? 'w-5 h-5' : 'w-7 h-7'"
        fill="none" viewBox="0 0 24 24" stroke="currentColor"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v6.343M15 3v6.343M5 21h14l-4-12H9L5 21z"/>
      </svg>
    </div>
    <div class="leading-tight">
      <div
        :class="size === 'lg' ? 'text-3xl' : size === 'sm' ? 'text-base' : 'text-2xl'"
        class="font-bold text-brand-navy-700 tracking-tight"
      >
        Azzir
      </div>
      <div class="text-[10px] uppercase tracking-widest text-brand-teal-600">
        Diagnostic Management System
      </div>
      <div v-if="subtitle" class="text-xs text-brand-teal-700 mt-0.5 tracking-widest">— {{ subtitle }} —</div>
    </div>
  </div>
</template>
