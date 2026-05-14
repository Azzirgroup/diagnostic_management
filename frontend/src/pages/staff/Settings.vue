<script setup lang="ts">
import Topbar from '@/components/layout/Topbar.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
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
          <input class="input" :value="auth.user?.full_name || ''" disabled />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">Email</label>
          <input class="input" :value="auth.user?.email || ''" disabled />
        </div>
      </div>
      <button class="btn-secondary mt-4">Save Changes</button>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-3">Notifications</h3>
      <p class="text-sm text-surface-500 mb-4">Choose how and when you want to be notified.</p>
      <ul class="text-sm space-y-3">
        <li v-for="n in ['Critical Results Alerts','Order Updates','System Announcements','Email Notifications','Sound Alerts']" :key="n" class="flex items-center justify-between">
          <span>{{ n }}</span>
          <button class="w-10 h-5 rounded-full bg-brand-teal-500 relative">
            <span class="absolute top-0.5 right-0.5 w-4 h-4 bg-white rounded-full"/>
          </button>
        </li>
      </ul>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-3">Password &amp; Security</h3>
      <p class="text-sm text-surface-500 mb-4">Manage your password and security preferences.</p>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-xs text-surface-500 mb-1">Current Password</label>
          <input type="password" class="input" placeholder="••••••••" />
        </div>
        <div>
          <label class="block text-xs text-surface-500 mb-1">New Password</label>
          <input type="password" class="input" placeholder="••••••••" />
        </div>
        <div class="col-span-2">
          <label class="block text-xs text-surface-500 mb-1">Confirm New Password</label>
          <input type="password" class="input" placeholder="••••••••" />
        </div>
      </div>
      <button class="btn-secondary mt-4">Update Password</button>
    </div>

    <div class="card p-5">
      <h3 class="font-semibold mb-3">Branch &amp; Session Preferences</h3>
      <p class="text-sm text-surface-500 mb-4">Configure your default branch and session behavior.</p>
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <label class="text-sm">Default Branch</label>
          <select class="input w-44"><option>Main Branch</option></select>
        </div>
        <div class="flex items-center justify-between">
          <label class="text-sm">Session Timeout</label>
          <select class="input w-44"><option>30 Minutes</option></select>
        </div>
        <div class="flex items-center justify-between">
          <label class="text-sm">Warn Before Logout</label>
          <select class="input w-44"><option>5 Minutes</option></select>
        </div>
      </div>
      <button class="btn-secondary mt-4">Save Preferences</button>
    </div>
  </div>
</template>
