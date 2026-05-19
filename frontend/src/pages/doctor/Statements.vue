<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'
import { doctorApi, type DoctorStatementRow } from '@/api/adms'

const statements = ref<DoctorStatementRow[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try { statements.value = await doctorApi.statements(undefined, 100) } catch { statements.value = [] }
  finally { loading.value = false }
}
onMounted(load)

const summary = computed(() => {
  const totalCommission = statements.value.reduce((s, r) => s + (r.commission_amount || 0), 0)
  const paid = statements.value.filter((r) => r.status === 'Paid').reduce((s, r) => s + (r.commission_amount || 0), 0)
  const outstanding = totalCommission - paid
  return { totalCommission, paid, outstanding }
})
</script>

<template>
  <Topbar title="Commission Statements" subtitle="Your referral commission statements" />
  <div class="card p-5 mb-4">
    <h3 class="font-semibold mb-3">Summary</h3>
    <div class="grid grid-cols-3 gap-3">
      <div><div class="text-xs text-surface-500">Total Commission</div><div class="text-lg font-semibold">{{ summary.totalCommission.toLocaleString() }}</div></div>
      <div><div class="text-xs text-surface-500">Paid</div><div class="text-lg font-semibold text-status-success">{{ summary.paid.toLocaleString() }}</div></div>
      <div><div class="text-xs text-surface-500">Outstanding</div><div class="text-lg font-semibold text-status-warning">{{ summary.outstanding.toLocaleString() }}</div></div>
    </div>
  </div>

  <div class="card p-5">
    <h3 class="font-semibold mb-3">Statements</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">Reference</th><th>Period</th><th>Referrals</th><th>Billed</th><th>Commission</th><th>Status</th><th>Paid Date</th>
      </tr></thead>
      <tbody>
        <tr v-if="!statements.length"><td colspan="7" class="py-6 text-center text-surface-400">{{ loading ? 'Loading…' : 'No statements yet' }}</td></tr>
        <tr v-for="c in statements" :key="c.name" class="border-b border-surface-100">
          <td class="py-2 text-brand-teal-600">{{ c.name }}</td>
          <td>{{ c.period_start }} → {{ c.period_end }}</td>
          <td>{{ c.referral_count ?? 0 }}</td>
          <td>{{ (c.total_billed ?? 0).toLocaleString() }}</td>
          <td>{{ (c.commission_amount ?? 0).toLocaleString() }}</td>
          <td><StatusPill :status="c.status" /></td>
          <td>{{ c.paid_date || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
