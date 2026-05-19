import { defineStore } from 'pinia'
import { ref } from 'vue'
import { call } from '@/api/client'

// Dashboard KPIs are computed server-side by
// diagnostic_management.api.dashboard.* so we don't make the SPA chase several
// list calls just to get counts.
//
// The shape is deliberately flat — each frontend view picks what it needs.

export interface LabManagerKpi {
  pending_samples: number
  pending_delta: number
  avg_tat_minutes: number
  critical_results: number
  reagent_alerts: number
}

export interface DoctorKpi {
  pending_results: number
  recent_patients: number
  new_orders: number
  unpaid_amount: number
}

export const useDashboardStore = defineStore('dashboard', () => {
  const lab = ref<LabManagerKpi | null>(null)
  const doctor = ref<DoctorKpi | null>(null)
  const loading = ref(false)

  async function fetchLab() {
    loading.value = true
    try {
      lab.value = await call<LabManagerKpi>('diagnostic_management.api.dashboard.lab_manager')
    } finally {
      loading.value = false
    }
  }

  async function fetchDoctor() {
    loading.value = true
    try {
      doctor.value = await call<DoctorKpi>('diagnostic_management.api.dashboard.doctor')
    } finally {
      loading.value = false
    }
  }

  return { lab, doctor, loading, fetchLab, fetchDoctor }
})
