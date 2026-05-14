<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import SearchBar from '@/components/ui/SearchBar.vue'

defineProps<{ title: string; subtitle?: string }>()

const auth = useAuthStore()
const router = useRouter()

async function onLogout() {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex items-center justify-between gap-6 mb-6">
    <div class="flex-1">
      <h1 class="text-2xl font-semibold text-surface-800">{{ title }}</h1>
      <p v-if="subtitle" class="text-sm text-surface-500 mt-0.5">{{ subtitle }}</p>
    </div>
    <div class="w-72 hidden md:block">
      <SearchBar placeholder="Search patients, orders, samples..." :show-kbd-hint="true" />
    </div>
    <button class="btn-ghost hidden md:flex">
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16l4-4 4 4 4-4 2 4z"/>
      </svg>
      {{ auth.activeBranch || 'Main Branch' }}
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
