<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import { useAuthStore } from '@/stores/auth'
import { settingsApi, type UserSettings } from '@/api/adms'

const auth = useAuthStore()
const settings = ref<UserSettings>({})
const busy = ref(false)
const saved = ref(false)
const error = ref('')

async function load() {
  try { settings.value = await settingsApi.get() } catch { settings.value = {} }
}
onMounted(load)

async function save() {
  busy.value = true
  saved.value = false
  error.value = ''
  try {
    await settingsApi.update({
      language: settings.value.language,
      time_zone: settings.value.time_zone,
      home_page_module: settings.value.home_page_module,
      result_density: settings.value.result_density,
      preferred_branch: settings.value.preferred_branch,
    })
    saved.value = true
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Failed to save'
  } finally { busy.value = false }
}
</script>

<template>
  <Topbar title="Settings" />
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Profile &amp; Preferences</h3>
      <p class="text-sm text-surface-500 mb-4">Manage your profile information and application preferences.</p>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Full Name</label>
          <input class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" :value="auth.user?.full_name || ''" disabled />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Email</label>
          <input class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" :value="auth.user?.email || ''" disabled />
        </div>
      </div>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-3">Roles</h3>
      <p class="text-sm text-surface-500 mb-4">Active role assignments for this user.</p>
      <div class="flex flex-wrap gap-2">
        <span v-for="r in settings.roles || []" :key="r" class="pill-info">{{ r }}</span>
        <span v-if="!settings.roles || !settings.roles.length" class="text-sm text-surface-400">No roles loaded</span>
      </div>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-3">Localization</h3>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Language</label>
          <input v-model="settings.language" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" placeholder="en" />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Time Zone</label>
          <input v-model="settings.time_zone" class="input w-full px-3 py-2 rounded border border-surface-200 text-sm" placeholder="Asia/Karachi" />
        </div>
      </div>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-3">Branch &amp; UI Preferences</h3>
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="text-sm">Preferred Branch</label>
          <input v-model="settings.preferred_branch" class="input w-44 px-3 py-2 rounded border border-surface-200 text-sm" placeholder="Main Branch" />
        </div>
        <div class="flex items-center justify-between">
          <label class="text-sm">Result Density</label>
          <select v-model="settings.result_density" class="input w-44 px-3 py-2 rounded border border-surface-200 text-sm">
            <option value="">Default</option>
            <option value="compact">Compact</option>
            <option value="comfortable">Comfortable</option>
          </select>
        </div>
        <div class="flex items-center justify-between">
          <label class="text-sm">Home Page</label>
          <input v-model="settings.home_page_module" class="input w-44 px-3 py-2 rounded border border-surface-200 text-sm" placeholder="home" />
        </div>
      </div>
    </div>
  </div>

  <div class="mt-4 flex items-center gap-3">
    <button class="btn-primary" :disabled="busy" @click="save">{{ busy ? 'Saving…' : 'Save Preferences' }}</button>
    <span v-if="saved" class="text-sm text-status-success">Saved.</span>
    <span v-if="error" class="text-sm text-status-danger">{{ error }}</span>
  </div>
</template>
