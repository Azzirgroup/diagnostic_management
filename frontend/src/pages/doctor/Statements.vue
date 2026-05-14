<script setup lang="ts">
import Topbar from '@/components/layout/Topbar.vue'
import StatusPill from '@/components/ui/StatusPill.vue'

const invoices = [
  { ref: 'INV-2025-052', period: 'May 2025', type: 'Invoice', amt: 25000, status: 'Paid', issued: 'May 20, 2025', due: 'Jun 04, 2025' },
  { ref: 'INV-2025-051', period: 'Apr 2025', type: 'Invoice', amt: 22500, status: 'Paid', issued: 'Apr 20, 2025', due: 'May 05, 2025' },
  { ref: 'INV-2025-050', period: 'Mar 2025', type: 'Invoice', amt: 24000, status: 'Paid', issued: 'Mar 20, 2025', due: 'Apr 04, 2025' },
  { ref: 'INV-2025-049', period: 'Feb 2025', type: 'Invoice', amt: 21000, status: 'Paid', issued: 'Feb 20, 2025', due: 'Mar 07, 2025' },
  { ref: 'INV-2025-048', period: 'Jan 2025', type: 'Invoice', amt: 26000, status: 'Partially Paid', issued: 'Jan 20, 2025', due: 'Feb 04, 2025' },
  { ref: 'INV-2024-123', period: 'Dec 2024', type: 'Invoice', amt: 23500, status: 'Overdue', issued: 'Dec 20, 2024', due: 'Jan 04, 2025' },
]
const commissions = [
  { ref: 'COM-2025-005', period: 'May 2025', amt: 5500, status: 'Paid', issued: 'Jun 05, 2025', paid: 'Jun 10, 2025' },
  { ref: 'COM-2025-004', period: 'Apr 2025', amt: 5000, status: 'Paid', issued: 'May 05, 2025', paid: 'May 10, 2025' },
  { ref: 'COM-2025-003', period: 'Mar 2025', amt: 4750, status: 'Paid', issued: 'Apr 05, 2025', paid: 'Apr 11, 2025' },
  { ref: 'COM-2025-001', period: 'Jan 2025', amt: 4975, status: 'Pending', issued: 'Feb 05, 2025', paid: '—' },
]
</script>

<template>
  <Topbar title="Invoices &amp; Commission" subtitle="View your invoices (statements) and commission summary." />
  <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Summary <span class="text-xs text-surface-400">(This Year)</span></h3>
      <div class="grid grid-cols-3 gap-3">
        <div><div class="text-xs text-surface-500">Total Invoiced</div><div class="text-lg font-semibold">PKR 237,450</div></div>
        <div><div class="text-xs text-surface-500">Total Paid</div><div class="text-lg font-semibold text-status-success">PKR 180,000</div></div>
        <div><div class="text-xs text-surface-500">Total Outstanding</div><div class="text-lg font-semibold text-status-warning">PKR 57,450</div></div>
      </div>
    </div>
    <div class="card p-5">
      <h3 class="font-semibold mb-3">Commission Summary <span class="text-xs text-surface-400">(This Year)</span></h3>
      <div class="grid grid-cols-3 gap-3">
        <div><div class="text-xs text-surface-500">Total Earned</div><div class="text-lg font-semibold">PKR 28,725</div></div>
        <div><div class="text-xs text-surface-500">Paid</div><div class="text-lg font-semibold text-status-success">PKR 20,000</div></div>
        <div><div class="text-xs text-surface-500">Outstanding</div><div class="text-lg font-semibold text-status-warning">PKR 8,725</div></div>
      </div>
    </div>
  </div>

  <div class="card p-5 mb-4">
    <h3 class="font-semibold mb-3">Invoices / Statements</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">Reference</th><th>Period</th><th>Amount (PKR)</th><th>Status</th><th>Issued</th><th>Due</th>
      </tr></thead>
      <tbody>
        <tr v-for="i in invoices" :key="i.ref" class="border-b border-surface-100">
          <td class="py-2 text-brand-teal-600">{{ i.ref }}</td>
          <td>{{ i.period }}</td>
          <td>{{ i.amt.toLocaleString() }}</td>
          <td><StatusPill :status="i.status" /></td>
          <td>{{ i.issued }}</td>
          <td>{{ i.due }}</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="card p-5">
    <h3 class="font-semibold mb-3">Commission Statements</h3>
    <table class="w-full text-sm">
      <thead><tr class="text-left text-surface-500 border-b border-surface-200">
        <th class="py-2">Reference</th><th>Period</th><th>Amount (PKR)</th><th>Status</th><th>Issued</th><th>Paid On</th>
      </tr></thead>
      <tbody>
        <tr v-for="c in commissions" :key="c.ref" class="border-b border-surface-100">
          <td class="py-2 text-brand-teal-600">{{ c.ref }}</td>
          <td>{{ c.period }}</td>
          <td>{{ c.amt.toLocaleString() }}</td>
          <td><StatusPill :status="c.status" /></td>
          <td>{{ c.issued }}</td>
          <td>{{ c.paid }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
