<script setup lang="ts">
import OrderIntake from '@/pages/staff/OrderIntake.vue'
// Doctor portal reuses the same Order Intake — server-side permission filters
// limit selectable patients to those the referring doctor has access to.
</script>

<template>
  <OrderIntake />
</template>
