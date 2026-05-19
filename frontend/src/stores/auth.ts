import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<authApi.FrappeUser | null>(null)
  const activeBranch = ref<string>('Main Branch')
  const ready = ref(false)

  const roles = computed(() => user.value?.roles || [])
  const primaryRole = computed(() => {
    if (!user.value) return ''
    const priority = [
      'Diagnostic Director',
      'Lab Director',
      'Lab Manager',
      'Radiology Manager',
      'Pathologist',
      'Radiologist',
      'Lab Quality Officer',
      'Lab Supervisor',
      'Lab Technician',
      'Radiology Technologist',
      'Phlebotomist',
      'Sample Receiver',
      'Receptionist',
      'Billing Officer',
      'Insurance Officer',
      'Physician',
      'Doctor',
      'Auditor',
    ]
    return priority.find((r) => roles.value.includes(r)) || roles.value[0] || 'Staff'
  })

  // External referring doctors get the doctor portal. Internal staff get the staff app.
  const isReferringDoctor = computed(
    () => roles.value.includes('Doctor') || roles.value.includes('Referring Doctor'),
  )
  const isStaff = computed(() => !isReferringDoctor.value && roles.value.length > 0)
  const isLoggedIn = computed(() => !!user.value)

  const initials = computed(() => {
    const full = user.value?.full_name || user.value?.name || ''
    return full
      .split(' ')
      .map((s) => s[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase()
  })

  async function bootstrap() {
    if (ready.value) return
    user.value = await authApi.getLoggedUser()
    ready.value = true
  }

  async function login(usr: string, pwd: string) {
    await authApi.login(usr, pwd)
    user.value = await authApi.getLoggedUser()
    return user.value
  }

  async function logout() {
    await authApi.logout()
    user.value = null
  }

  function setBranch(name: string) {
    activeBranch.value = name
  }

  return {
    user,
    activeBranch,
    ready,
    roles,
    primaryRole,
    isReferringDoctor,
    isStaff,
    isLoggedIn,
    initials,
    bootstrap,
    login,
    logout,
    setBranch,
  }
})
