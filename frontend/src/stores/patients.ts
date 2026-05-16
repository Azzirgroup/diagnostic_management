import { defineStore } from 'pinia'
import { ref } from 'vue'
import { patientsApi, type PatientLite } from '@/api/adms'

export type Patient = PatientLite

export const usePatientsStore = defineStore('patients', () => {
  const list = ref<Patient[]>([])
  const loading = ref(false)
  const selected = ref<Record<string, unknown> | null>(null)

  async function fetch(limit = 50, search?: string) {
    loading.value = true
    try {
      list.value = await patientsApi.search(search || '', limit)
    } catch {
      list.value = []
    } finally {
      loading.value = false
    }
  }

  async function load(name: string) {
    selected.value = await patientsApi.detail(name)
    return selected.value
  }

  return { list, loading, selected, fetch, load }
})
