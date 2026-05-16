// Typed wrappers around `diagnostic_management.api.*` whitelisted methods.
//
// Every method matches a Python function in apps/diagnostic_management/api/.
// Each helper resolves to the unwrapped `message` payload (see client.call()).
// Pages should prefer these over raw `call('...')` strings.

import { call } from './client'

// -------------------------------------------------------------------------
// Shared types
// -------------------------------------------------------------------------

export interface PatientLite {
  name: string
  patient_name: string
  sex?: string
  dob?: string
  mobile?: string
  email?: string
  blood_group?: string
  uid?: string
  status?: string
  image?: string
}

export interface OrderRow {
  name: string
  patient: string
  patient_name: string
  priority?: string
  subject?: string
  template_dt?: string
  template_dn?: string
  status: string
  occurrence_date?: string
  creation?: string
  practitioner?: string
  imaging_modality?: string
  imaging_body_part?: string
  contrast_required?: number
  clinical_history_text?: string
}

export interface SampleRow {
  name: string
  patient?: string
  patient_name?: string
  sample?: string
  sample_qty?: number
  collection_date?: string
  collection_time?: string
  status: string
  container?: string
  barcode?: string
  received_condition?: string
  rejection_reason_text?: string
  modified?: string
}

export interface ReagentLot {
  name: string
  reagent_item: string
  lot_number: string
  section?: string
  manufacturer?: string
  received_date?: string
  expiry_date?: string
  quantity_received?: number
  quantity_on_hand?: number
  unit?: string
  status: string
  storage_location?: string
  instrument?: string
  qc_passed?: number
}

export interface LabInstrumentRow {
  name: string
  instrument_name: string
  manufacturer?: string
  model?: string
  section?: string
  location?: string
  interface_type?: string
  state: string
  last_heartbeat?: string
  last_maintenance?: string
  serial_number?: string
  host?: string
  port?: number
  stale?: boolean
}

export interface QCRow {
  name: string
  instrument: string
  section?: string
  analyte?: string
  control_level?: string
  lot_number?: string
  run_datetime?: string
  expected_value?: number
  observed_value: number
  unit?: string
  sd?: number
  z_score?: number
  westgard_flag?: string
  result: string
  status: string
  performed_by?: string
}

export interface CalibrationRow {
  name: string
  instrument: string
  calibration_type?: string
  scheduled_date?: string
  performed_date?: string
  performed_by?: string
  next_due?: string
  analyte?: string
  calibrator_lot?: string
  result: string
  status: string
}

export interface PeerReviewRow {
  name: string
  subject_report?: string
  patient?: string
  patient_name?: string
  section?: string
  modality?: string
  priority?: string
  original_reporter?: string
  assigned_reviewer?: string
  due_date?: string
  status: string
  outcome?: string
  submitted_at?: string
}

export interface PreAuthRow {
  name: string
  patient: string
  patient_name?: string
  modality?: string
  body_part?: string
  urgency?: string
  payor?: string
  policy_number?: string
  estimated_amount?: number
  status: string
  submitted_date?: string
  approved_amount?: number
  approval_reference?: string
}

export interface DoctorStatementRow {
  name: string
  period_start?: string
  period_end?: string
  issued_date?: string
  referral_count?: number
  total_billed?: number
  commission_pct?: number
  commission_amount?: number
  net_payable?: number
  status: string
  paid_date?: string
}

export interface DiagnosticReportRow {
  name: string
  docname?: string
  patient?: string
  patient_name?: string
  practitioner?: string
  status: string
  is_critical?: number
  critical_acknowledged?: number
  critical_acknowledged_at?: string
  creation?: string
  modified?: string
  log?: Array<{
    name: string
    severity?: string
    status?: string
    detected_at?: string
    notified_at?: string
    acknowledged_at?: string
    escalation_level?: number
  }>
}

export interface InvoiceRow {
  name: string
  customer?: string
  customer_name?: string
  grand_total?: number
  outstanding_amount?: number
  status: string
  posting_date?: string
  due_date?: string
  currency?: string
}

// -------------------------------------------------------------------------
// Patients
// -------------------------------------------------------------------------

export const patientsApi = {
  search: (query = '', limit = 25) =>
    call<PatientLite[]>('diagnostic_management.api.patients.search', { query, limit }),
  detail: (name: string) =>
    call<Record<string, unknown>>('diagnostic_management.api.patients.detail', { name }),
  createBasic: (payload: {
    first_name: string
    last_name?: string
    sex?: string
    dob?: string
    mobile?: string
    email?: string
    blood_group?: string
    uid?: string
    permanent_address?: string
  }) => call<{ ok: boolean; name: string; patient_name: string }>('diagnostic_management.api.patients.create_basic', payload),
}

// -------------------------------------------------------------------------
// Orders
// -------------------------------------------------------------------------

export interface CatalogItem {
  template_dt: string
  template_dn: string
  label: string
  rate?: number
  sample?: string
  category: string
}

export const ordersApi = {
  create: (payload: {
    patient: string
    practitioner?: string
    priority?: string
    tests?: Array<{ template_dt: string; template_dn: string; subject?: string }>
    clinical_history?: string
    imaging_modality?: string
    imaging_body_part?: string
    contrast_required?: number
    occurrence_date?: string
  }) => call<{ ok: boolean; orders: string[]; count: number }>('diagnostic_management.api.orders.create_order', payload),
  forPatient: (patient: string, limit = 50) =>
    call<OrderRow[]>('diagnostic_management.api.orders.list_for_patient', { patient, limit }),
  worklist: (status?: string, priority?: string, limit = 100) =>
    call<OrderRow[]>('diagnostic_management.api.orders.worklist', { status, priority, limit }),
  cancel: (name: string, reason = '') =>
    call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.orders.cancel', { name, reason }),
  testCatalog: (query = '', limit = 50) =>
    call<CatalogItem[]>('diagnostic_management.api.orders.test_catalog', { query, limit }),
}

// -------------------------------------------------------------------------
// Collection / Sample
// -------------------------------------------------------------------------

export const collectionApi = {
  worklist: (status?: string, limit = 100) =>
    call<SampleRow[]>('diagnostic_management.api.collection.worklist', { status, limit }),
  markCollected: (sample: string, container?: string, barcode?: string) =>
    call<{ ok: boolean; sample: string; status: string }>('diagnostic_management.api.collection.mark_collected', { sample, container, barcode }),
  accessionQueue: (limit = 100) =>
    call<SampleRow[]>('diagnostic_management.api.collection.accession_queue', { limit }),
}

export const sampleApi = {
  accept: (sample: string, destination?: string, notes = '') =>
    call<{ ok: boolean; sample: string; status: string }>('diagnostic_management.api.sample.accept', { sample, destination, notes }),
  reject: (payload: {
    sample: string
    reason: string
    severity?: string
    notes?: string
    recollection_required?: boolean
    target_date?: string
    target_time?: string
    notify_caller?: boolean
  }) => call<{ ok: boolean; sample: string; status: string }>('diagnostic_management.api.sample.reject', payload),
}

// -------------------------------------------------------------------------
// Lab Hub / Verification / Peer Review
// -------------------------------------------------------------------------

export interface LabHubSummary {
  pending_accession: number
  in_analysis: number
  pending_verification: number
  qc_open: number
  calibration_due: number
  peer_review_open: number
}

export const labApi = {
  hubSummary: () => call<LabHubSummary>('diagnostic_management.api.lab.hub_summary'),
  verificationQueue: (limit = 100) =>
    call<DiagnosticReportRow[]>('diagnostic_management.api.lab.verification_queue', { limit }),
  verify: (name: string, conclusion?: string) =>
    call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.lab.verify_report', { name, conclusion }),
  amend: (name: string, reason: string) =>
    call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.lab.amend_report', { name, reason }),
  peerReviewList: (status?: string, mine = 0, limit = 100) =>
    call<PeerReviewRow[]>('diagnostic_management.api.lab.peer_review_list', { status, mine, limit }),
  submitPeerReview: (payload: {
    name: string
    outcome?: string
    review_notes?: string
    discrepancy_severity?: string
    concurrence?: number
  }) => call<{ ok: boolean; name: string; status: string; outcome: string }>('diagnostic_management.api.lab.submit_peer_review', payload),
}

// -------------------------------------------------------------------------
// Reagents
// -------------------------------------------------------------------------

export const reagentsApi = {
  listLots: (status?: string, section?: string, limit = 100) =>
    call<ReagentLot[]>('diagnostic_management.api.reagents.list_lots', { status, section, limit }),
  lowStock: (threshold_pct = 20, limit = 100) =>
    call<ReagentLot[]>('diagnostic_management.api.reagents.low_stock', { threshold_pct, limit }),
  expiringSoon: (days = 30, limit = 100) =>
    call<ReagentLot[]>('diagnostic_management.api.reagents.expiring_soon', { days, limit }),
  addLot: (payload: {
    reagent_item: string
    lot_number: string
    section?: string
    manufacturer?: string
    received_date?: string
    expiry_date?: string
    quantity_received?: number
    unit?: string
    storage_location?: string
    instrument?: string
  }) => call<{ ok: boolean; name: string }>('diagnostic_management.api.reagents.add_lot', payload),
  logUsage: (lot: string, amount: number, notes?: string) =>
    call<{ ok: boolean; lot: string; quantity_on_hand: number; status: string }>('diagnostic_management.api.reagents.log_usage', { lot, amount, notes }),
  reagentItems: (query = '', limit = 50) =>
    call<Array<{ name: string; item_name: string; item_code: string; stock_uom?: string }>>('diagnostic_management.api.reagents.reagent_items', { query, limit }),
}

// -------------------------------------------------------------------------
// Instruments
// -------------------------------------------------------------------------

export const instrumentsApi = {
  list: (section?: string, state?: string, limit = 100) =>
    call<LabInstrumentRow[]>('diagnostic_management.api.instruments.list_instruments', { section, state, limit }),
  monitor: () => call<LabInstrumentRow[]>('diagnostic_management.api.instruments.monitor'),
  setState: (instrument: string, state: string, note = '') =>
    call<{ ok: boolean; instrument: string; state: string }>('diagnostic_management.api.instruments.set_state', { instrument, state, note }),
  heartbeat: (instrument: string) =>
    call<{ ok: boolean; instrument: string }>('diagnostic_management.api.instruments.heartbeat', { instrument }),
}

// -------------------------------------------------------------------------
// QC
// -------------------------------------------------------------------------

export const qcApi = {
  list: (filters: { status?: string; result?: string; instrument?: string; section?: string; limit?: number } = {}) =>
    call<QCRow[]>('diagnostic_management.api.qc.list_runs', filters),
  submit: (payload: {
    instrument: string
    analyte: string
    control_level: string
    observed_value: number
    expected_value?: number
    sd?: number
    lot_number?: string
    unit?: string
    westgard_flag?: string
    notes?: string
  }) => call<{ ok: boolean; name: string; result: string; z_score?: number }>('diagnostic_management.api.qc.submit_run', payload),
  approve: (name: string, notes = '') =>
    call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.qc.approve', { name, notes }),
  reject: (name: string, corrective_action = '') =>
    call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.qc.reject', { name, corrective_action }),
}

// -------------------------------------------------------------------------
// Calibration
// -------------------------------------------------------------------------

export const calibrationApi = {
  list: (filters: { status?: string; instrument?: string; limit?: number } = {}) =>
    call<CalibrationRow[]>('diagnostic_management.api.calibration.list_runs', filters),
  dueSoon: (days = 14, limit = 100) =>
    call<CalibrationRow[]>('diagnostic_management.api.calibration.due_soon', { days, limit }),
  log: (payload: {
    instrument: string
    calibration_type?: string
    result?: string
    analyte?: string
    calibrator_lot?: string
    calibrator_expiry?: string
    findings?: string
    corrective_action?: string
  }) => call<{ ok: boolean; name: string; next_due?: string }>('diagnostic_management.api.calibration.log', payload),
}

// -------------------------------------------------------------------------
// Radiology
// -------------------------------------------------------------------------

export interface RadDashboard {
  pending_studies: number
  pending_pre_auth: number
  approved_pre_auth: number
  reports_pending: number
  critical: number
}

export const radiologyApi = {
  readingWorklist: (filters: { modality?: string; priority?: string; status?: string; limit?: number } = {}) =>
    call<OrderRow[]>('diagnostic_management.api.radiology.reading_worklist', filters),
  dashboard: () => call<RadDashboard>('diagnostic_management.api.radiology.dashboard'),
  preAuthQueue: (status?: string, limit = 100) =>
    call<PreAuthRow[]>('diagnostic_management.api.radiology.preauth_queue', { status, limit }),
  createPreAuth: (payload: {
    patient: string
    modality?: string
    body_part?: string
    urgency?: string
    payor?: string
    policy?: string
    policy_number?: string
    estimated_amount?: number
    clinical_justification?: string
    service_request?: string
  }) => call<{ ok: boolean; name: string }>('diagnostic_management.api.radiology.create_preauth', payload),
  submitPreAuth: (name: string) =>
    call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.radiology.submit_preauth', { name }),
  decidePreAuth: (payload: {
    name: string
    decision: 'Approved' | 'Denied' | 'Expired' | 'Cancelled'
    approved_amount?: number
    approval_reference?: string
    denial_reason?: string
  }) => call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.radiology.decide_preauth', payload),
  saveReport: (payload: {
    name?: string
    patient?: string
    service_request?: string
    practitioner?: string
    findings?: string
    impression?: string
    recommendations?: string
    is_critical?: number
    status?: string
  }) => call<{ ok: boolean; name: string; status: string }>('diagnostic_management.api.radiology.save_report', payload),
}

// -------------------------------------------------------------------------
// Critical findings
// -------------------------------------------------------------------------

export const criticalApi = {
  listOpen: (severity?: string, limit = 100) =>
    call<DiagnosticReportRow[]>('diagnostic_management.api.critical.list_open', { severity, limit }),
  acknowledge: (report: string, notes = '') =>
    call<{ ok: boolean; report: string }>('diagnostic_management.api.critical.acknowledge', { report, notes }),
  logFinding: (payload: {
    report: string
    severity?: string
    test_or_modality?: string
    summary?: string
    notification_channel?: string
  }) => call<{ ok: boolean; name: string }>('diagnostic_management.api.critical.log_finding', payload),
}

// -------------------------------------------------------------------------
// Billing
// -------------------------------------------------------------------------

export interface BillingSummary {
  draft: { count: number; total: number }
  unpaid: { count: number; total: number }
  paid: { count: number; total: number }
}

export const billingApi = {
  queue: (status?: string, limit = 100) =>
    call<InvoiceRow[]>('diagnostic_management.api.billing.queue', { status, limit }),
  forPatient: (patient: string, limit = 50) =>
    call<InvoiceRow[]>('diagnostic_management.api.billing.for_patient', { patient, limit }),
  summary: () => call<BillingSummary>('diagnostic_management.api.billing.summary'),
}

// -------------------------------------------------------------------------
// Analytics & Audit
// -------------------------------------------------------------------------

export interface AnalyticsKpis {
  orders: number
  samples: number
  reports_completed: number
  critical_results: number
  pre_auth_approved: number
  qc_failed: number
}

export const analyticsApi = {
  kpis: (days = 7) => call<AnalyticsKpis>('diagnostic_management.api.analytics.kpis', { days }),
  volumeTrend: (days = 14) =>
    call<Array<{ date: string; orders: number; samples: number; reports: number }>>('diagnostic_management.api.analytics.volume_trend', { days }),
  sectionMix: (days = 30) =>
    call<Array<{ section: string; count: number }>>('diagnostic_management.api.analytics.section_mix', { days }),
}

export const auditApi = {
  activity: (days = 7, limit = 200, doctype?: string) =>
    call<Array<{ name: string; subject: string; user: string; operation?: string; reference_doctype?: string; reference_name?: string; creation: string }>>(
      'diagnostic_management.api.audit.activity',
      { days, limit, doctype },
    ),
  criticalAudit: (days = 30, limit = 100) =>
    call<DiagnosticReportRow[]>('diagnostic_management.api.audit.critical_audit', { days, limit }),
  rejectionLog: (days = 30, limit = 100) =>
    call<SampleRow[]>('diagnostic_management.api.audit.rejection_log', { days, limit }),
}

// -------------------------------------------------------------------------
// Doctor portal
// -------------------------------------------------------------------------

export const doctorApi = {
  resultsInbox: (status?: string, limit = 100) =>
    call<DiagnosticReportRow[]>('diagnostic_management.api.doctor.results_inbox', { status, limit }),
  myPatients: (limit = 100) =>
    call<PatientLite[]>('diagnostic_management.api.doctor.my_patients', { limit }),
  myOrders: (limit = 100) =>
    call<OrderRow[]>('diagnostic_management.api.doctor.my_orders', { limit }),
  statements: (status?: string, limit = 50) =>
    call<DoctorStatementRow[]>('diagnostic_management.api.doctor.statements', { status, limit }),
  criticalToAck: (limit = 50) =>
    call<DiagnosticReportRow[]>('diagnostic_management.api.doctor.critical_to_ack', { limit }),
}

// -------------------------------------------------------------------------
// Settings
// -------------------------------------------------------------------------

export interface UserSettings {
  language?: string
  time_zone?: string
  user_image?: string
  theme?: string
  roles?: string[]
  home_page_module?: string
  result_density?: string
  preferred_branch?: string
}

export const settingsApi = {
  get: () => call<UserSettings>('diagnostic_management.api.settings.get'),
  update: (payload: Partial<UserSettings>) =>
    call<{ ok: boolean }>('diagnostic_management.api.settings.update', { payload }),
}
