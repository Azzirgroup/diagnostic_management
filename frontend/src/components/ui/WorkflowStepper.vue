<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

// Guided lab-workflow progress bar, shown across the order → collection →
// store → result pages so users always see where they are and can jump
// between steps. Mirrors the genetest WorkflowWizard's pipeline, adapted to
// the ADMS (Marley-backed) doctypes.
const props = defineProps<{
  order?: string
  sample?: string
  current: 'order' | 'collection' | 'store' | 'result'
}>()

const router = useRouter()
const orderQ = computed(() => (props.order ? `?order=${props.order}` : ''))

type Step = { key: string; label: string; to: string }
const steps = computed<Step[]>(() => [
  { key: 'order', label: 'Order', to: props.order ? `/orders/${props.order}` : '' },
  { key: 'collection', label: 'Collection', to: props.sample ? `/lab/sample/${props.sample}/collect${orderQ.value}` : (props.order ? `/orders/${props.order}` : '') },
  { key: 'store', label: 'Store', to: props.sample ? `/lab/sample/${props.sample}${orderQ.value}` : '' },
  { key: 'result', label: 'Result', to: props.order ? `/orders/${props.order}` : '/lab/verification' },
])

const currentIdx = computed(() => steps.value.findIndex((s) => s.key === props.current))
// The next step after the current one — drives the explicit "Continue" button
// so users always have an obvious way forward (not just clicking a circle).
const nextStep = computed<Step | null>(() => {
  const n = steps.value[currentIdx.value + 1]
  return n && n.to ? n : null
})

function go(s: Step) {
  if (s.to) router.push(s.to)
}
</script>

<template>
  <div class="card p-4 mb-4">
    <div class="flex items-center gap-4">
      <div class="flex items-center flex-1 min-w-0">
        <template v-for="(s, i) in steps" :key="s.key">
          <button
            type="button"
            class="flex items-center gap-2 rounded-md px-1"
            :class="s.to ? 'cursor-pointer hover:bg-surface-50' : 'cursor-default'"
            :disabled="!s.to"
            :title="s.to ? `Go to ${s.label}` : ''"
            @click="go(s)"
          >
            <span
              class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold border-2"
              :class="i < currentIdx ? 'bg-brand-teal-500 text-white border-brand-teal-500'
                    : i === currentIdx ? 'bg-brand-teal-100 text-brand-teal-700 border-brand-teal-500'
                    : s.to ? 'bg-white text-brand-teal-600 border-brand-teal-300'
                    : 'bg-surface-100 text-surface-400 border-surface-300'"
            >
              <span v-if="i < currentIdx">✓</span><span v-else>{{ i + 1 }}</span>
            </span>
            <span
              class="text-sm whitespace-nowrap"
              :class="i === currentIdx ? 'font-semibold text-surface-800' : i < currentIdx ? 'text-surface-700' : s.to ? 'text-brand-teal-600' : 'text-surface-400'"
            >{{ s.label }}</span>
          </button>
          <div v-if="i < steps.length - 1" class="flex-1 h-px mx-3 min-w-[12px]" :class="i < currentIdx ? 'bg-brand-teal-400' : 'bg-surface-200'"></div>
        </template>
      </div>
      <button
        v-if="nextStep"
        class="btn-primary !py-1.5 !text-xs shrink-0"
        @click="go(nextStep)"
      >Continue: {{ nextStep.label }} →</button>
    </div>
  </div>
</template>
