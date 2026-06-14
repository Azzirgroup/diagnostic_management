import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<authApi.FrappeUser | null>(null)
  // Branch the topbar displays. Fetched from
  // diagnostic_management.api.branches.get_my_branch on bootstrap.
  //  - admins / unscoped users see "All Branches"
  //  - users with a branch tag see that branch name
  const activeBranch = ref<string>('All Branches')
  const isBranchScoped = ref<boolean>(false)
  // Whether the topbar should render the branch-switcher dropdown.
  const canSwitchBranch = ref<boolean>(false)
  // All branches available to switch to (loaded once on bootstrap when can_switch).
  const availableBranches = ref<string[]>([])
  // Why the active branch is what it is: 'override' | 'shift' | 'tag' | null.
  const branchSource = ref<string | null>(null)
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
    await refreshBranchState()
    ready.value = true
  }

  // Re-fetch the user's branch state (after a switch or on login).
  async function refreshBranchState() {
    try {
      const { branchesApi } = await import('@/api/adms')
      const mb = await branchesApi.myBranch()
      if (mb.sees_all_branches) {
        activeBranch.value = 'All Branches'
        isBranchScoped.value = false
      } else if (mb.branch) {
        activeBranch.value = mb.branch
        isBranchScoped.value = true
      }
      canSwitchBranch.value = !!mb.can_switch_branch
      branchSource.value = mb.source || null
      // Load the branch list lazily for the dropdown.
      if (canSwitchBranch.value && !availableBranches.value.length) {
        try {
          const list = await branchesApi.list()
          availableBranches.value = list.map((b) => b.name)
        } catch { /* keep empty */ }
      }
    } catch { /* leave default */ }
  }

  // Admin (or any unrestricted user) sets the active-branch lens.
  // Pass null/'' to revert to "All Branches".
  async function setActiveBranch(branch: string | null) {
    const { branchesApi } = await import('@/api/adms')
    await branchesApi.setActiveBranch(branch || null)
    await refreshBranchState()
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
    isBranchScoped,
    canSwitchBranch,
    availableBranches,
    branchSource,
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
    setActiveBranch,
    refreshBranchState,
  }
})
