<script setup>
// Horizontal-bar breakdown of payment-mode totals over the report window.
// Expects { paymentModeTotals: [{ mode_of_payment, expected, closing, difference }] }
import { computed } from 'vue'
const props = defineProps({
  paymentModeTotals: { type: Array, default: () => [] },
})
const maxAmt = computed(() => Math.max(1, ...props.paymentModeTotals.flatMap(r => [Number(r.expected) || 0, Number(r.closing) || 0])))
const fmt = v => 'Ksh ' + (Number(v) || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })
</script>

<template>
  <div class="rounded-lg border border-surface-200 bg-white p-3">
    <h4 class="text-sm font-semibold text-surface-700 mb-2">Expected vs Closing by Payment Mode</h4>
    <div v-if="!paymentModeTotals.length" class="text-xs text-surface-400 py-8 text-center">No reconciliation data.</div>
    <div v-else class="space-y-2">
      <div v-for="r in paymentModeTotals" :key="r.mode_of_payment" class="text-xs">
        <div class="flex items-center justify-between mb-1">
          <span class="font-medium">{{ r.mode_of_payment }}</span>
          <span :class="(Number(r.difference) || 0) === 0 ? 'text-emerald-700' : 'text-amber-700'">
            Δ {{ fmt(r.difference) }}
          </span>
        </div>
        <div class="space-y-0.5">
          <div class="flex items-center gap-2">
            <span class="w-20 text-surface-500">Expected</span>
            <div class="flex-1 h-3 bg-surface-100 rounded overflow-hidden">
              <div class="h-full bg-blue-500" :style="{ width: ((Number(r.expected) || 0) / maxAmt * 100) + '%' }"></div>
            </div>
            <span class="w-24 text-right tabular-nums">{{ fmt(r.expected) }}</span>
          </div>
          <div class="flex items-center gap-2">
            <span class="w-20 text-surface-500">Closing</span>
            <div class="flex-1 h-3 bg-surface-100 rounded overflow-hidden">
              <div class="h-full bg-emerald-500" :style="{ width: ((Number(r.closing) || 0) / maxAmt * 100) + '%' }"></div>
            </div>
            <span class="w-24 text-right tabular-nums">{{ fmt(r.closing) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
