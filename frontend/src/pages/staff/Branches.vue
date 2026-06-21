<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import { branchesApi, type BranchRow, type UserBranchRow } from '@/api/adms'
import { frappeError } from '@/api/client'

// Branches admin — manage Branch records (HRMS Branch doctype) and assign
// users to a branch. A user with no branch sees ALL branches' data;
// admins always see everything regardless.

const branches = ref<BranchRow[]>([])
const users = ref<UserBranchRow[]>([])
const newBranch = ref('')
const loading = ref(false)
const error = ref('')
const flash = ref('')
const savingUserId = ref<string | null>(null)

async function load() {
  loading.value = true; error.value = ''
  try {
    const [b, u] = await Promise.all([branchesApi.list(), branchesApi.listUsers()])
    branches.value = b
    users.value = u
  } catch (e: any) { error.value = frappeError(e, 'Failed to load branches') }
  finally { loading.value = false }
}
onMounted(load)

async function createBranch() {
  if (!newBranch.value.trim()) return
  error.value = ''
  try {
    await branchesApi.create(newBranch.value.trim())
    flash.value = `Created branch "${newBranch.value.trim()}"`
    newBranch.value = ''
    setTimeout(() => { flash.value = '' }, 2500)
    await load()
  } catch (e: any) { error.value = frappeError(e, 'Failed to create branch') }
}

async function assignBranch(user: string, branch: string) {
  savingUserId.value = user
  error.value = ''
  try {
    await branchesApi.setUserBranch(user, branch || null)
    flash.value = `Saved branch for ${user}`
    setTimeout(() => { flash.value = '' }, 2000)
    await load()
  } catch (e: any) { error.value = frappeError(e, 'Failed to update user branch') }
  finally { savingUserId.value = null }
}
</script>

<template>
  <Topbar title="Branches" subtitle="Manage branches and assign users — empty branch on a user means they see ALL branches" />

  <div v-if="error" class="card mb-4 p-3 text-sm text-red-700 bg-red-50 border-l-4 border-red-500">{{ error }}</div>
  <div v-if="flash" class="card mb-4 p-3 text-sm text-emerald-700 bg-emerald-50 border-l-4 border-emerald-500">{{ flash }}</div>

  <!-- Branches list + create -->
  <div class="card p-4 mb-4">
    <h3 class="font-semibold text-sm mb-3">Branches ({{ branches.length }})</h3>
    <div class="flex gap-2 mb-4">
      <input v-model="newBranch" type="text" placeholder="e.g. Westlands Branch"
        class="input flex-1" @keyup.enter="createBranch" />
      <button class="btn-primary" :disabled="!newBranch.trim() || loading" @click="createBranch">+ Add Branch</button>
    </div>
    <table v-if="branches.length" class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">Name</th>
        <th class="py-2 text-right">Patients</th>
        <th class="py-2 text-right">Users assigned</th>
      </tr></thead>
      <tbody>
        <tr v-for="b in branches" :key="b.name" class="border-b border-surface-100">
          <td class="py-2 font-medium">{{ b.branch || b.name }}</td>
          <td class="py-2 text-right font-semibold text-brand-navy-700">{{ b.patient_count ?? 0 }}</td>
          <td class="py-2 text-right text-surface-500">{{ users.filter(u => u.branch === b.name).length }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="text-surface-400 text-sm">No branches yet. Create one above.</p>
  </div>

  <!-- Users + their branch -->
  <div class="card p-4">
    <h3 class="font-semibold text-sm mb-3">User Assignments</h3>
    <p class="text-xs text-surface-500 mb-3">
      Pick a branch for each user. <strong>Leave blank</strong> if they should see data from all branches.
    </p>
    <div v-if="!users.length" class="text-surface-400 text-sm">Loading…</div>
    <table v-else class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">User</th>
        <th class="py-2">Branch</th>
        <th class="py-2 text-right">Status</th>
      </tr></thead>
      <tbody>
        <tr v-for="u in users" :key="u.name" class="border-b border-surface-100">
          <td class="py-2">
            <div class="font-medium text-surface-800">{{ u.full_name || u.name }}</div>
            <div class="text-xs text-surface-400">{{ u.name }}</div>
          </td>
          <td class="py-2 w-72">
            <select :value="u.branch || ''" class="input"
              :disabled="savingUserId === u.name"
              @change="assignBranch(u.name, ($event.target as HTMLSelectElement).value)">
              <option value="">— all branches —</option>
              <option v-for="b in branches" :key="b.name" :value="b.name">{{ b.branch || b.name }}</option>
            </select>
          </td>
          <td class="py-2 text-right text-xs">
            <span v-if="savingUserId === u.name" class="text-surface-400">Saving…</span>
            <span v-else-if="u.branch" class="text-emerald-700">Scoped to {{ u.branch }}</span>
            <span v-else class="text-surface-500">All branches</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
