<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import GlobalSearch from '@/components/layout/GlobalSearch.vue'

defineProps<{ title: string; subtitle?: string }>()

const auth = useAuthStore()
const router = useRouter()

async function onLogout() {
  await auth.logout()
  router.push('/login')
}

// Branch switcher — only rendered when the user is allowed to switch.
// Picking an option calls auth.setActiveBranch which refreshes the
// branch state; we then reload so every page re-fetches its data
// against the new branch lens.
const switching = ref(false)
async function onBranchChange(ev: Event) {
  const val = (ev.target as HTMLSelectElement).value
  if (switching.value) return
  switching.value = true
  try {
    await auth.setActiveBranch(val || null)
    // Reload so every screen's data is re-fetched under the new lens.
    window.location.reload()
  } finally { switching.value = false }
}
</script>

<template>
  <div class="flex items-center justify-between gap-6 mb-6">
    <div class="flex-1">
      <h1 class="text-2xl font-semibold text-surface-800">{{ title }}</h1>
      <p v-if="subtitle" class="text-sm text-surface-500 mt-0.5">{{ subtitle }}</p>
    </div>
    <div class="w-80 hidden md:block">
      <GlobalSearch />
    </div>
    <!-- Branch switcher: dropdown for users who can switch, static label otherwise. -->
    <label v-if="auth.canSwitchBranch && auth.availableBranches.length"
      class="btn-ghost hidden md:flex items-center gap-2 cursor-pointer !pr-1">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l4-4 4 4 4-4 2 4z"/>
      </svg>
      <select
        :value="auth.isBranchScoped ? auth.activeBranch : ''"
        class="bg-transparent border-0 text-sm font-medium outline-none cursor-pointer pr-1"
        :disabled="switching"
        @change="onBranchChange"
        :title="switching ? 'Switching…' : 'Switch branch view'">
        <option value="">All Branches</option>
        <option v-for="b in auth.availableBranches" :key="b" :value="b">{{ b }}</option>
      </select>
    </label>
    <button v-else
      class="btn-ghost hidden md:flex items-center gap-1"
      :title="auth.branchSource === 'shift' ? 'Branch switched because your open shift is on a different branch. Close the shift to revert to your tagged branch.' : 'Your branch (set by an administrator)'">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l4-4 4 4 4-4 2 4z"/>
      </svg>
      {{ auth.activeBranch || 'Main Branch' }}
      <span v-if="auth.branchSource === 'shift'"
        class="ml-1 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-100 text-amber-800 text-xs font-medium">
        via shift
      </span>
    </button>
    <button class="btn-ghost hidden md:flex">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
      </svg>
      {{ new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) }}
    </button>
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-full bg-brand-navy-700 text-white flex items-center justify-center text-sm font-semibold">
        {{ auth.initials }}
      </div>
      <div class="hidden md:block leading-tight">
        <div class="text-sm font-medium text-surface-800">{{ auth.user?.full_name || 'User' }}</div>
        <div class="text-xs text-surface-500">{{ auth.primaryRole || 'Staff' }}</div>
      </div>
      <button class="text-surface-400 hover:text-surface-700" @click="onLogout" title="Sign out">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h6a2 2 0 012 2v1"/>
        </svg>
      </button>
    </div>
  </div>
</template>
