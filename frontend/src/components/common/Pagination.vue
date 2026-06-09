<script setup>
// Page navigator used by ShiftList tabs. Same prop names as genetest's
// component so the ported template binds cleanly.
import { computed } from 'vue'
const props = defineProps({
  total: { type: Number, default: 0 },
  pageSize: { type: Number, default: 25 },
  currentPage: { type: Number, default: 1 },
})
const emit = defineEmits(['change'])
const totalPages = computed(() => Math.max(1, Math.ceil((props.total || 0) / (props.pageSize || 25))))
const go = (p) => {
  const np = Math.min(Math.max(1, p), totalPages.value)
  if (np !== props.currentPage) emit('change', np)
}
</script>

<template>
  <nav v-if="totalPages > 1" class="flex items-center justify-between text-xs text-surface-500 px-4 py-2 border-t border-surface-100">
    <span>Page {{ currentPage }} of {{ totalPages }} · {{ total }} total</span>
    <div class="flex items-center gap-1">
      <button class="px-2 py-1 rounded hover:bg-surface-100 disabled:opacity-40" :disabled="currentPage <= 1" @click="go(currentPage - 1)">‹ Prev</button>
      <button class="px-2 py-1 rounded hover:bg-surface-100 disabled:opacity-40" :disabled="currentPage >= totalPages" @click="go(currentPage + 1)">Next ›</button>
    </div>
  </nav>
</template>
