import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// The SPA is mounted by Frappe at one of four URL roots, each served by a
// thin www/<root>.html shim. Detect the root at boot from window.__ADMS_BASE__
// (set by the shim) or fall back to URL inspection so the same bundle runs
// correctly under any base.
function detectBase(): string {
  const fromShim = (window as any).__ADMS_BASE__ as string | undefined
  if (fromShim) return fromShim
  const p = window.location.pathname
  if (p.startsWith('/doctor-register')) return '/doctor-register'
  if (p.startsWith('/doctor-login')) return '/doctor-login'
  if (p.startsWith('/doctor')) return '/doctor'
  if (p.startsWith('/diagnostic_management')) return '/diagnostic_management'
  return '/'
}

const base = detectBase()

const routes: RouteRecordRaw[] = []

// --- Auth (visible under any base) ---
const authChildren = [
  { path: '', name: 'staff-login', component: () => import('@/pages/auth/StaffLogin.vue') },
]
const doctorAuthChildren = [
  { path: '', name: 'doctor-login', component: () => import('@/pages/auth/DoctorLogin.vue') },
]
const doctorRegChildren = [
  { path: '', name: 'doctor-register', component: () => import('@/pages/auth/DoctorRegister.vue') },
]

if (base === '/doctor-login') {
  routes.push({ path: '/', component: () => import('@/layouts/AuthLayout.vue'), children: doctorAuthChildren })
} else if (base === '/doctor-register') {
  routes.push({ path: '/', component: () => import('@/layouts/AuthLayout.vue'), children: doctorRegChildren })
} else if (base === '/doctor') {
  // Doctor portal — routes mounted at root because the base is already /doctor.
  routes.push({
    path: '/',
    component: () => import('@/layouts/DoctorLayout.vue'),
    meta: { requiresAuth: true, portal: 'doctor' },
    children: [
      { path: '', name: 'doctor-dashboard', component: () => import('@/pages/doctor/DoctorDashboard.vue') },
      { path: 'results', name: 'doctor-results', component: () => import('@/pages/doctor/ResultInbox.vue') },
      { path: 'results/:name', name: 'doctor-result-detail', component: () => import('@/pages/doctor/ResultDetail.vue') },
      { path: 'results/:name/acknowledge', name: 'doctor-critical-ack', component: () => import('@/pages/doctor/CriticalAcknowledgement.vue') },
      { path: 'patients', name: 'doctor-patients', component: () => import('@/pages/doctor/MyPatients.vue') },
      { path: 'patients/:name', name: 'doctor-patient-detail', component: () => import('@/pages/doctor/PatientDetail.vue') },
      { path: 'orders', name: 'doctor-orders', component: () => import('@/pages/doctor/NewOrder.vue') },
      { path: 'statements', name: 'doctor-statements', component: () => import('@/pages/doctor/Statements.vue') },
      { path: 'settings', name: 'doctor-settings', component: () => import('@/pages/doctor/DoctorSettings.vue') },
    ],
  })
} else {
  // Staff app under /diagnostic_management — full app with login at /login.
  routes.push(
    { path: '/login', component: () => import('@/layouts/AuthLayout.vue'), children: authChildren },
    {
      path: '/',
      component: () => import('@/layouts/StaffLayout.vue'),
      meta: { requiresAuth: true, portal: 'staff' },
      children: [
        { path: '', name: 'home', component: () => import('@/pages/staff/Home.vue') },
        { path: 'patients', name: 'patients', component: () => import('@/pages/staff/Patients.vue') },
        { path: 'patients/new', name: 'patient-new', component: () => import('@/pages/staff/NewPatient.vue') },
        { path: 'patients/:name', name: 'patient-detail', component: () => import('@/pages/staff/PatientProfile.vue') },
        { path: 'orders', name: 'orders', component: () => import('@/pages/staff/Orders.vue') },
        { path: 'orders/new', name: 'order-new', component: () => import('@/pages/staff/OrderIntake.vue') },
        { path: 'orders/:name/edit', name: 'order-edit', component: () => import('@/pages/staff/OrderIntake.vue') },
        { path: 'orders/:name', name: 'order-detail', component: () => import('@/pages/staff/OrderDetail.vue') },
        { path: 'collection', name: 'collection', component: () => import('@/pages/staff/CollectionWorklist.vue') },
        { path: 'lab', name: 'lab', component: () => import('@/pages/staff/LabHub.vue') },
        { path: 'lab/accession', name: 'lab-accession', component: () => import('@/pages/staff/SampleAccession.vue') },
        { path: 'lab/sample/:name', name: 'sample-detail', component: () => import('@/pages/staff/SampleDetail.vue') },
        { path: 'lab/reagents', name: 'reagents', component: () => import('@/pages/staff/Reagents.vue') },
        { path: 'lab/instruments', name: 'instruments', component: () => import('@/pages/staff/LabInstruments.vue') },
        { path: 'lab/qc', name: 'qc', component: () => import('@/pages/staff/QcStation.vue') },
        { path: 'lab/calibration', name: 'calibration', component: () => import('@/pages/staff/Calibration.vue') },
        { path: 'lab/analyzer-monitor', name: 'analyzer-monitor', component: () => import('@/pages/staff/AnalyzerMonitor.vue') },
        { path: 'lab/verification', name: 'verification', component: () => import('@/pages/staff/VerificationQueue.vue') },
        { path: 'lab/peer-review', name: 'peer-review', component: () => import('@/pages/staff/PeerReview.vue') },
        { path: 'radiology', name: 'radiology', component: () => import('@/pages/staff/RadiologyDashboard.vue') },
        { path: 'radiology/worklist', name: 'reading-worklist', component: () => import('@/pages/staff/ReadingWorklist.vue') },
        { path: 'radiology/viewer/:name?', name: 'image-viewer', component: () => import('@/pages/staff/ImageViewer.vue') },
        { path: 'radiology/report/:name?', name: 'report-editor', component: () => import('@/pages/staff/ReportEditor.vue') },
        { path: 'radiology/pre-auth', name: 'pre-auth', component: () => import('@/pages/staff/PreAuthQueue.vue') },
        { path: 'critical-findings', name: 'critical-findings', component: () => import('@/pages/staff/CriticalFindings.vue') },
        { path: 'critical-findings/:name', name: 'critical-findings-detail', component: () => import('@/pages/staff/CriticalFindingDetail.vue') },
        { path: 'billing', name: 'billing', component: () => import('@/pages/staff/BillingQueue.vue') },
        { path: 'billing/:name', name: 'invoice-detail', component: () => import('@/pages/staff/InvoiceDetail.vue') },
        // Generic doctype detail routes — driven by route.meta.doctype.
        { path: 'lab/reagent/:name', name: 'reagent-detail', meta: { doctype: 'Reagent Lot', title: 'Reagent Lot' }, component: () => import('@/pages/staff/DocDetail.vue') },
        { path: 'lab/instrument/:name', name: 'instrument-detail', meta: { doctype: 'Lab Instrument', title: 'Lab Instrument' }, component: () => import('@/pages/staff/DocDetail.vue') },
        { path: 'lab/qc/:name', name: 'qc-detail', meta: { doctype: 'QC Run', title: 'QC Run' }, component: () => import('@/pages/staff/DocDetail.vue') },
        { path: 'lab/calibration/:name', name: 'calibration-detail', meta: { doctype: 'Calibration Run', title: 'Calibration Run' }, component: () => import('@/pages/staff/DocDetail.vue') },
        { path: 'lab/peer-review/:name', name: 'peer-review-detail', meta: { doctype: 'Peer Review Case', title: 'Peer Review Case' }, component: () => import('@/pages/staff/DocDetail.vue') },
        { path: 'radiology/pre-auth/:name', name: 'pre-auth-detail', meta: { doctype: 'Radiology Pre-Auth', title: 'Radiology Pre-Auth' }, component: () => import('@/pages/staff/DocDetail.vue') },
        { path: 'analytics', name: 'analytics', component: () => import('@/pages/staff/Analytics.vue') },
        { path: 'audit', name: 'audit', component: () => import('@/pages/staff/AuditCompliance.vue') },
        { path: 'settings', name: 'settings', component: () => import('@/pages/staff/Settings.vue') },
        { path: 'reception', name: 'reception', component: () => import('@/pages/staff/ReceptionDashboard.vue') },
        { path: 'director', name: 'director', component: () => import('@/pages/staff/DirectorDashboard.vue') },
        { path: 'pathologist', name: 'pathologist', component: () => import('@/pages/staff/PathologistDashboard.vue') },
      ],
    },
  )
}

// Catch-all
routes.push({ path: '/:pathMatch(.*)*', redirect: '/' })

export const router = createRouter({
  history: createWebHistory(base),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.bootstrap()

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    // Push the user to the appropriate login URL (cross-base, full reload).
    const next = encodeURIComponent(window.location.pathname + window.location.search)
    const loginPath = to.meta.portal === 'doctor' ? '/doctor-login' : '/diagnostic_management/login'
    window.location.assign(`${loginPath}?next=${next}`)
    return false
  }
})

export default router
