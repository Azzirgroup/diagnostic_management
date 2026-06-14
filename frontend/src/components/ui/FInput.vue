<script setup lang="ts">
// Lightweight replacement for frappe-ui's <Input> used by ported components.
defineProps<{ modelValue?: string; label?: string; type?: string; placeholder?: string; rows?: number }>()
defineEmits<{ (e: 'update:modelValue', v: string): void }>()
</script>

<template>
  <div>
    <label v-if="label" class="block text-sm font-medium text-gray-700 mb-1">{{ label }}</label>
    <textarea
      v-if="type === 'textarea'"
      :value="modelValue"
      :rows="rows || 3"
      :placeholder="placeholder"
      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
      @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    ></textarea>
    <input
      v-else
      :value="modelValue"
      :type="type || 'text'"
      :placeholder="placeholder"
      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-green-500 focus:border-green-500"
      @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    />
  </div>
</template>
