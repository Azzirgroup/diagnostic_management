<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AzzirLogo from '@/components/ui/AzzirLogo.vue'

const usr = ref('')
const pwd = ref('')
const branch = ref('Main Branch')
const showPwd = ref(false)
const remember = ref(false)
const submitting = ref(false)
const error = ref('')

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function onSubmit() {
  if (!usr.value || !pwd.value) {
    error.value = 'Please enter your username and password.'
    return
  }
  error.value = ''
  submitting.value = true
  try {
    const user = await auth.login(usr.value, pwd.value)
    auth.setBranch(branch.value)
    if (!user) throw new Error('Login succeeded but no user came back.')
    if (auth.isReferringDoctor) {
      router.push('/doctor')
    } else {
      const next = route.query.next as string | undefined
      router.push(next || '/')
    }
  } catch (e: any) {
    error.value = e?.response?.data?.message || e?.message || 'Login failed. Check credentials.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex-1 flex">
    <!-- Left brand panel -->
    <div class="hidden lg:flex w-1/2 px-12 py-16 flex-col justify-between">
      <AzzirLogo size="lg" subtitle="ADMS" />
      <div>
        <h2 class="text-3xl font-bold text-brand-navy-700 mb-2">Smart. Connected. Reliable.</h2>
        <p class="text-surface-500">Empowering diagnostics. Enabling better outcomes.</p>
      </div>
      <div class="opacity-40">
        <svg viewBox="0 0 320 240" class="w-full max-w-md mx-auto">
          <circle cx="80" cy="120" r="60" fill="none" stroke="#1A8B96" stroke-width="2"/>
          <rect x="170" y="120" width="14" height="80" fill="#E4E9F1" rx="4"/>
          <rect x="190" y="100" width="14" height="100" fill="#E4E9F1" rx="4"/>
          <rect x="210" y="80" width="14" height="120" fill="#E4E9F1" rx="4"/>
          <circle cx="260" cy="100" r="36" fill="none" stroke="#0B2440" stroke-width="3"/>
        </svg>
      </div>
    </div>

    <!-- Right form panel -->
    <div class="flex-1 flex items-center justify-center px-6 py-12">
      <form class="w-full max-w-md card p-8" @submit.prevent="onSubmit">
        <h1 class="text-2xl font-bold text-brand-navy-700">Welcome Back</h1>
        <p class="text-surface-500 mt-1">Sign in to access ADMS and manage operations across your branches.</p>

        <div class="mt-6 space-y-4">
          <div>
            <label class="block text-sm font-medium text-surface-700 mb-1">Branch</label>
            <select v-model="branch" class="input">
              <option>Main Branch</option>
              <option>North Branch</option>
              <option>East Branch</option>
              <option>West Branch</option>
              <option>South Branch</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-700 mb-1">Username or Email</label>
            <input v-model="usr" class="input" type="text" autocomplete="username" placeholder="Enter your username or email" />
          </div>
          <div>
            <label class="block text-sm font-medium text-surface-700 mb-1">Password</label>
            <div class="relative">
              <input v-model="pwd" :type="showPwd ? 'text' : 'password'" class="input pr-10" autocomplete="current-password" placeholder="Enter your password" />
              <button type="button" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400" @click="showPwd = !showPwd">
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.46 12C3.73 7.94 7.52 5 12 5c4.48 0 8.27 2.94 9.54 7-1.27 4.06-5.06 7-9.54 7-4.48 0-8.27-2.94-9.54-7z"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="flex items-center justify-between text-sm">
            <label class="flex items-center gap-2 text-surface-600">
              <input v-model="remember" type="checkbox" class="rounded accent-brand-teal-500" />
              Remember me
            </label>
            <a href="#" class="text-brand-teal-600 hover:underline">Forgot password?</a>
          </div>
          <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg">{{ error }}</p>
          <button class="btn-primary w-full" :disabled="submitting">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 11c0-1.66 1.34-3 3-3s3 1.34 3 3v2H6v-2c0-1.66 1.34-3 3-3 .56 0 1.08.15 1.53.41M12 11V8a4 4 0 118 0v3"/>
            </svg>
            {{ submitting ? 'Signing in…' : 'Sign In' }}
          </button>
        </div>

        <div class="mt-6 flex items-center justify-center gap-2 text-sm text-surface-500">
          <svg class="w-4 h-4 text-brand-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Secure access to ADMS
        </div>

        <div class="mt-8 text-center text-xs text-surface-500">
          Built for multi-branch diagnostic operations<br>
          <span class="text-brand-teal-700">Secure · Compliant · Connected</span>
        </div>
      </form>
    </div>
  </div>
</template>
