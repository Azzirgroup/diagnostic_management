<script setup lang="ts">
import PatientProfile from '@/pages/staff/PatientProfile.vue'
// Doctor portal reuses the same Patient Profile 360 view as the staff app —
// permissions are enforced server-side via the Doctor role.
</script>

<template>
  <PatientProfile />
</template>
