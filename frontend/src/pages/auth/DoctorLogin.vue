<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AzzirLogo from '@/components/ui/AzzirLogo.vue'

const usr = ref('')
const pwd = ref('')
const showPwd = ref(false)
const submitting = ref(false)
const error = ref('')

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

async function onSubmit() {
  error.value = ''
  submitting.value = true
  try {
    await auth.login(usr.value, pwd.value)
    const next = route.query.next as string | undefined
    router.push(next || '/doctor')
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Login failed. Check credentials.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex-1 flex items-center justify-center px-6 py-12">
    <div class="w-full max-w-md">
      <div class="flex flex-col items-center text-center mb-8">
        <AzzirLogo size="lg" subtitle="ADMS" />
      </div>
      <h1 class="text-2xl font-bold text-brand-navy-700 text-center">Doctor Login</h1>
      <p class="text-surface-500 text-center mt-1">Sign in to access your ADMS portal</p>

      <form class="mt-8 space-y-4" @submit.prevent="onSubmit">
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
            </svg>
          </span>
          <input v-model="usr" class="input pl-11" placeholder="Email or Username" />
        </div>
        <div class="relative">
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-surface-400">
            <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 11c-1.66 0-3 1.34-3 3v2h6v-2c0-1.66-1.34-3-3-3zm6-1V8a6 6 0 10-12 0v2h12z"/>
            </svg>
          </span>
          <input v-model="pwd" :type="showPwd ? 'text' : 'password'" class="input pl-11 pr-10" placeholder="Password" />
          <button type="button" class="absolute right-3 top-1/2 -translate-y-1/2 text-surface-400" @click="showPwd = !showPwd">
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
            </svg>
          </button>
        </div>
        <div class="text-right">
          <a href="#" class="text-sm text-brand-teal-600 hover:underline">Forgot Password?</a>
        </div>
        <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg">{{ error }}</p>
        <button class="btn-primary w-full py-3" :disabled="submitting">
          {{ submitting ? 'Signing in…' : 'Sign In' }}
        </button>
        <div class="text-center text-sm text-surface-500 pt-2">
          New here?
          <a href="#" class="text-brand-teal-600 hover:underline">Accept an invite</a>
          or
          <RouterLink to="/doctor-register" class="text-brand-teal-600 hover:underline">Register</RouterLink>
        </div>
      </form>
    </div>
  </div>
</template>
