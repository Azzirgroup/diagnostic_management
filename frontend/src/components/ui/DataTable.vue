<script setup lang="ts" generic="T extends Record<string, any>">
import { ref } from 'vue'

interface Column<TRow> {
  key: keyof TRow & string
  label: string
  width?: string
  render?: (row: TRow) => unknown
}

const props = defineProps<{
  rows: T[]
  columns: Column<T>[]
  selectable?: boolean
  rowKey?: keyof T & string
  initialSelectedIndex?: number
  emptyText?: string
}>()

const emit = defineEmits<{
  (e: 'select', row: T): void
}>()

const selectedIndex = ref<number | null>(props.initialSelectedIndex ?? null)

function pick(row: T, c: Column<T>) {
  if (c.render) return c.render(row)
  return row[c.key]
}

function onRowClick(row: T, i: number) {
  if (!props.selectable) return
  selectedIndex.value = i
  emit('select', row)
}
</script>

<template>
  <div class="overflow-x-auto">
    <table class="w-full text-sm">
      <thead>
        <tr class="border-b border-surface-200">
          <th v-if="selectable" class="w-8"></th>
          <th
            v-for="col in columns"
            :key="col.key"
            class="table-header text-left px-3 py-3"
            :style="col.width ? { width: col.width } : undefined"
          >
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + (selectable ? 1 : 0)" class="text-center text-surface-400 py-12">
            {{ emptyText || 'No records' }}
          </td>
        </tr>
        <tr
          v-for="(row, i) in rows"
          :key="(rowKey ? row[rowKey] : i) as any"
          class="border-b border-surface-100 hover:bg-surface-50 transition-colors cursor-pointer"
          :class="{ 'row-selected': selectable && selectedIndex === i }"
          @click="onRowClick(row, i)"
        >
          <td v-if="selectable" class="px-3 py-3">
            <input
              type="radio"
              :checked="selectedIndex === i"
              class="w-4 h-4 accent-brand-navy-700"
              @click.stop="onRowClick(row, i)"
            />
          </td>
          <td v-for="col in columns" :key="col.key" class="px-3 py-3 align-top">
            <slot :name="`cell-${col.key}`" :row="row" :value="pick(row, col)">
              <component v-if="false" :is="'span'" />
              {{ pick(row, col) }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
