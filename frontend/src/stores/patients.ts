import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getList, getDoc } from '@/api/client'

export interface Patient {
  name: string
  patient_name: string
  sex?: string
  dob?: string
  mobile?: string
  email?: string
  blood_group?: string
  uid?: string
  image?: string
}

export const usePatientsStore = defineStore('patients', () => {
  const list = ref<Patient[]>([])
  const loading = ref(false)
  const selected = ref<Patient | null>(null)

  async function fetch(limit = 50, search?: string) {
    loading.value = true
    try {
      const filters = search ? { patient_name: ['like', `%${search}%`] } : undefined
      list.value = await getList<Patient>({
        doctype: 'Patient',
        fields: ['name', 'patient_name', 'sex', 'dob', 'mobile', 'email', 'blood_group', 'uid', 'image'],
        filters,
        limit_page_length: limit,
        order_by: 'modified desc',
      })
    } finally {
      loading.value = false
    }
  }

  async function load(name: string) {
    selected.value = await getDoc<Patient>('Patient', name)
    return selected.value
  }

  return { list, loading, selected, fetch, load }
})
