<script setup lang="ts">
defineProps<{
  label: string
  value: string | number
  delta?: string
  deltaDirection?: 'up' | 'down' | 'flat'
  iconColor?: string
  iconBg?: string
  sub?: string
}>()
</script>

<template>
  <div class="card p-5">
    <div class="flex items-start justify-between">
      <div class="flex items-center gap-4">
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center"
          :style="{ backgroundColor: iconBg || 'rgb(230 244 245)' }"
        >
          <slot name="icon">
            <svg class="w-6 h-6" :style="{ color: iconColor || 'rgb(26 139 150)' }" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-6h6v6m-9 4h12a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
            </svg>
          </slot>
        </div>
        <div>
          <div class="text-sm text-surface-500">{{ label }}</div>
          <div class="text-2xl font-semibold text-surface-800 mt-1">{{ value }}</div>
          <div v-if="delta" class="text-xs mt-1 flex items-center gap-1" :class="{
            'text-status-success': deltaDirection === 'up',
            'text-status-danger': deltaDirection === 'down',
            'text-surface-500': !deltaDirection || deltaDirection === 'flat',
          }">
            <span v-if="deltaDirection === 'up'">↑</span>
            <span v-else-if="deltaDirection === 'down'">↓</span>
            <span v-else>—</span>
            {{ delta }}
          </div>
          <div v-else-if="sub" class="text-xs mt-1 text-surface-500">{{ sub }}</div>
        </div>
      </div>
    </div>
  </div>
</template>
