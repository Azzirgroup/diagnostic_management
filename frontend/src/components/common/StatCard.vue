<script setup>
// Simple KPI card used by the Shift Report tab. Mirrors the prop shape from
// genetest (title / value / color / icon) so the ported template renders.
import { computed } from 'vue'
const props = defineProps({
  title: String,
  value: [String, Number],
  color: { type: String, default: 'gray' },
  icon: { type: String, default: '' },
})
const palette = {
  blue:  { bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-200' },
  green: { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
  amber: { bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200' },
  red:   { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200' },
  gray:  { bg: 'bg-surface-50', text: 'text-surface-700', border: 'border-surface-200' },
}
const p = computed(() => palette[props.color] || palette.gray)
</script>

<template>
  <div :class="['rounded-lg border p-4 flex items-center justify-between gap-3', p.bg, p.border]">
    <div>
      <div class="text-xs uppercase tracking-wide text-surface-500">{{ title }}</div>
      <div :class="['text-2xl font-bold mt-1', p.text]">{{ value }}</div>
    </div>
  </div>
</template>
