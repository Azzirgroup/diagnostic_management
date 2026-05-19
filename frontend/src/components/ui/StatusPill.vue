<script setup lang="ts">
const props = defineProps<{ status: string; tone?: 'success' | 'warning' | 'danger' | 'info' | 'neutral' }>()

// Heuristic: if no `tone` prop, infer from status text — matches screenshots:
//   'In Stock' / 'Passed' / 'Online' / 'Verified' / 'Operational' / 'Normal'  -> success
//   'Low Stock' / 'Pending' / 'Due Today' / 'Warning' / 'Waiting' / 'In Progress' / 'Routine' / 'Low' / 'Expiring Soon' / 'In Analysis' / 'Awaiting Submission' / 'Pending Approval' / 'Draft' / 'In Processing' / 'Scheduled' / 'On Hold' -> warning/neutral
//   'Out of Stock' / 'Failed' / 'Rejected' / 'Critical' / 'Overdue' / 'Offline' / 'Error' / 'Deficient' / 'High' / 'Cancelled' / 'Denied' / 'Unack.' -> danger

const successWords = ['in stock', 'passed', 'online', 'verified', 'operational', 'normal', 'approved', 'paid', 'completed', 'collected', 'good', 'ack.', 'acknowledged', 'sent']
const warningWords = ['low stock', 'pending', 'due today', 'warning', 'waiting', 'in progress', 'routine', 'low', 'expiring soon', 'in analysis', 'awaiting submission', 'pending approval', 'draft', 'in processing', 'scheduled', 'on hold', 'medium', 'attention', 'check', 'delayed', 'queued', 'pending review', 'partially paid', 'upcoming', 'insurance split']
const dangerWords = ['out of stock', 'failed', 'rejected', 'critical', 'overdue', 'offline', 'error', 'deficient', 'high', 'cancelled', 'denied', 'unack.', 'escalated', 'breached']
const infoWords = ['stat', 'new', 'ready to bill', 'in stock blue', 'unread', 'live', 'final', 'exception']

function inferTone(s: string): string {
  const low = s.toLowerCase().trim()
  if (successWords.some((w) => low === w)) return 'success'
  if (dangerWords.some((w) => low === w)) return 'danger'
  if (infoWords.some((w) => low === w)) return 'info'
  if (warningWords.some((w) => low === w)) return 'warning'
  return 'neutral'
}

const tone = () => props.tone || inferTone(props.status)
</script>

<template>
  <span :class="`pill-${tone()}`">{{ status }}</span>
</template>
