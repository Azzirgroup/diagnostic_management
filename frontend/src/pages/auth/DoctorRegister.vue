<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { call } from '@/api/client'
import AzzirLogo from '@/components/ui/AzzirLogo.vue'

const inviteCode = ref('')
const fullName = ref('')
const email = ref('')
const phone = ref('')
const license = ref('')
const pwd = ref('')
const pwd2 = ref('')
const submitting = ref(false)
const error = ref('')
const router = useRouter()

async function onSubmit() {
  if (pwd.value !== pwd2.value) {
    error.value = 'Passwords do not match.'
    return
  }
  submitting.value = true
  error.value = ''
  try {
    await call('diagnostic_management.api.auth.accept_doctor_invite', {
      invite_code: inviteCode.value,
      full_name: fullName.value,
      email: email.value,
      phone: phone.value,
      license: license.value,
      password: pwd.value,
    })
    router.push('/doctor-login')
  } catch (e: any) {
    error.value = e?.response?.data?.message || 'Registration failed.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="flex-1 flex items-center justify-center px-6 py-12">
    <div class="w-full max-w-3xl">
      <div class="flex flex-col items-center text-center mb-8">
        <AzzirLogo size="lg" />
      </div>
      <div class="card p-8">
        <h2 class="text-xl font-bold text-brand-navy-700 text-center">Doctor Self-Registration / Invite Acceptance</h2>
        <p class="text-surface-500 text-center mt-1">Enter your invite code and complete your details to create your doctor account.</p>

        <form class="mt-8 space-y-6" @submit.prevent="onSubmit">
          <div>
            <div class="text-brand-teal-700 font-semibold mb-3">Invite Details</div>
            <label class="block text-sm font-medium text-surface-700 mb-1">Invite Code / Token</label>
            <input v-model="inviteCode" class="input" placeholder="Enter invite code or token" />
          </div>

          <div>
            <div class="text-brand-teal-700 font-semibold mb-3">Doctor Information</div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-surface-700 mb-1">Full Name</label>
                <input v-model="fullName" class="input" placeholder="Enter full name" />
              </div>
              <div>
                <label class="block text-sm font-medium text-surface-700 mb-1">Email Address</label>
                <input v-model="email" type="email" class="input" placeholder="Enter email address" />
              </div>
              <div>
                <label class="block text-sm font-medium text-surface-700 mb-1">Phone Number</label>
                <input v-model="phone" class="input" placeholder="Enter phone number" />
              </div>
              <div>
                <label class="block text-sm font-medium text-surface-700 mb-1">License / Registration Number</label>
                <input v-model="license" class="input" placeholder="Enter license or registration number" />
              </div>
            </div>
          </div>

          <div>
            <div class="text-brand-teal-700 font-semibold mb-3">Create Password</div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-surface-700 mb-1">Password</label>
                <input v-model="pwd" type="password" class="input" placeholder="Create password" />
              </div>
              <div>
                <label class="block text-sm font-medium text-surface-700 mb-1">Confirm Password</label>
                <input v-model="pwd2" type="password" class="input" placeholder="Confirm password" />
              </div>
            </div>
            <p class="text-xs text-surface-500 mt-2">
              Password must be at least 8 characters and include uppercase, lowercase, number, and special character.
            </p>
          </div>

          <p v-if="error" class="text-sm text-status-danger bg-status-danger-bg p-2 rounded-lg">{{ error }}</p>
          <button class="btn-primary w-full py-3" :disabled="submitting">
            {{ submitting ? 'Submitting…' : 'Complete Registration' }}
          </button>
        </form>
      </div>
    </div>
  </div>
</template>
