app_name = "diagnostic_management"
app_title = "Diagnostic Management"
app_publisher = "Surajit Das"
app_description = "Diagnostic Management for healthcare"
app_email = "surajit.das0320@gmail.com"
app_license = "mit"

# ADMS extends Marley Health (the `healthcare` app) and ERPNext additively.
# We never fork them — extensions ship via Custom Fields installed below.
required_apps = ["frappe", "erpnext", "healthcare"]

# Show the SPA on the desk "Apps" launcher so users can jump straight into it.
# Two tiles: the underlying app + the Kanonas Diagnosis branded entry. Both
# route into the same SPA but the second mirrors the workspace name so users
# who think of the product as "Kanonas Diagnosis" find it where they expect.
add_to_apps_screen = [
	{
		"name": "diagnostic_management",
		"logo": "/assets/diagnostic_management/images/logo.svg",
		"title": "Diagnostic Management",
		"route": "/diagnostic_management",
		"has_permission": "diagnostic_management.api.permission.has_app_permission",
	},
	{
		"name": "kanonas_diagnosis",
		"logo": "/assets/diagnostic_management/images/kanonas.svg",
		"title": "Kanonas Diagnosis",
		"route": "/diagnostic_management",
		"has_permission": "diagnostic_management.api.permission.has_app_permission",
	},
]

# Serve the SPA shell at every deep link. The Vue Router decides which page
# to render client-side. Each base route has its own www/<base>.html shim,
# and these rules route the *deep* links (e.g. /doctor/results/123) to the
# matching shim.
website_route_rules = [
	{"from_route": "/diagnostic_management/<path:app_path>", "to_route": "diagnostic_management"},
	{"from_route": "/doctor/<path:app_path>", "to_route": "doctor"},
	{"from_route": "/doctor-login/<path:app_path>", "to_route": "doctor-login"},
	{"from_route": "/doctor-register/<path:app_path>", "to_route": "doctor-register"},
]

# Jinja helpers usable inside Print Formats (e.g. {{ generate_barcode_svg(doc.name) }}).
jinja = {
	"methods": [
		"diagnostic_management.utils.formatters.generate_barcode_svg",
		"diagnostic_management.utils.formatters.generate_barcode_base64",
		"diagnostic_management.utils.formatters.generate_qr_code_base64",
		"diagnostic_management.utils.formatters.format_report_datetime",
		"diagnostic_management.utils.formatters.format_report_date",
		"diagnostic_management.utils.formatters.format_patient_age",
		"diagnostic_management.utils.formatters.result_flag",
		"diagnostic_management.utils.formatters.get_patient_test_history",
		"diagnostic_management.utils.formatters.generate_trend_chart_svg",
	],
}

# Installation hooks. setup/ is idempotent so it's safe on every migrate.
after_install = "diagnostic_management.setup.after_install"
after_migrate = "diagnostic_management.setup.after_migrate"

# Override Marley's Lab Test Template controller so sample_qty=0 is allowed
# (qualitative tests / swabs / panel-billed entries don't have a numeric qty).
# Tag Sales Invoices created during an open shift with the cashier's
# POS Opening Entry, so the shift-close reconciliation can pull a clean
# invoice list rather than guess by timestamp.
doc_events = {
	"Sales Invoice": {
		"validate": "diagnostic_management.api.shifts.tag_sales_invoice_with_shift",
		# Branch Accounting Dimension auto-stamp — precedence in
		# `diagnostic_management.finance.stamp._sales_invoice_branch`.
		"before_insert": "diagnostic_management.finance.stamp.stamp_sales_invoice",
	},
	"Payment Entry": {
		"before_insert": "diagnostic_management.finance.stamp.stamp_payment_entry",
	},
	"Purchase Invoice": {
		"before_insert": "diagnostic_management.finance.stamp.stamp_purchase_invoice",
	},
	"Journal Entry": {
		"before_insert": "diagnostic_management.finance.stamp.stamp_journal_entry",
	},
	# Auto-tag Patient with the creating user's branch (if they have one).
	"Patient": {
		"validate": "diagnostic_management.api.branches.auto_set_patient_branch",
	},
	# When a Lab Test stamped with a Sales Invoice is inserted, push that
	# stamp onto the parent Sample Collection too (if it doesn't have one
	# yet). Lets every downstream list filter by SI in one step.
	# Also expand Grouped-inside-Grouped templates. Marley's load_result_format()
	# has no branch for a Grouped member of a Grouped package, so nested packages
	# (TFT / Electrolytes / Lipid Profile inside "Afya Bora") were silently
	# dropped from normal_test_items. Runs after Marley's own expansion.
	"Lab Test": {
		"after_insert": [
			"diagnostic_management.api.branches.stamp_sample_collection_si",
			"diagnostic_management.overrides.lab_test_expansion.expand_nested_groups",
		],
	},
}

# Per-doctype list filter — a Lab Tech in Branch A sees only their branch's
# patients in any list / search. Admins and unscoped users bypass.
permission_query_conditions = {
	"Patient": "diagnostic_management.api.branches.patient_query_conditions",
}
has_permission = {
	"Patient": "diagnostic_management.api.branches.patient_has_permission",
}

override_doctype_class = {
	"Lab Test Template": "diagnostic_management.overrides.lab_test_template.LabTestTemplate",
}

# Ship workspace + ADMS roles with the app so a fresh install boots usable.
fixtures = [
	{
		"dt": "Workspace",
		"filters": [["module", "=", "Diagnostic Management"]],
	},
	{
		"dt": "Role",
		"filters": [["role_name", "in", [
			"Receptionist", "Phlebotomist", "Sample Receiver", "Lab Technician",
			"Lab Quality Officer", "Pathologist", "Lab Manager",
			"Urgent Review Officer",
			"Radiology Technologist", "Radiologist", "Radiology Manager",
			"Diagnostic Director", "Billing Officer", "Insurance Officer",
			"Referring Doctor", "Auditor",
		]]],
	},
	# Custom Field records that attach ADMS extensions to Marley/ERPNext
	# doctypes. setup/custom_fields.install_custom_fields is the canonical
	# installer (idempotent on every migrate). Exporting them as fixtures
	# means a plain `git pull` + restart on live is enough.
	{
		"dt": "Custom Field",
		"filters": [["fieldname", "in", [
			"loinc_code", "tat_routine_minutes", "tat_urgent_minutes", "tat_stat_minutes",
			"critical_value_low", "critical_value_high",
			"custom_reference_ranges_section", "custom_reference_ranges",
			"mrn_group", "preferred_result_channel", "preferred_language_for_reports",
			"consent_contrast", "consent_radiation",
			"practitioner_role", "is_external_referrer", "referrer_commission_pct",
			"e_signature_image", "external_practice_name",
			"imaging_modality", "imaging_body_part", "contrast_required", "clinical_history_text",
			"barcode", "container", "workflow_status", "is_urgent",
			"received_datetime", "processed_datetime", "department_barcodes",
			"received_condition", "rejection_reason_text",
			"is_critical", "critical_acknowledged", "critical_acknowledged_at",
			"diagnosis", "clinical_notes", "pathologist_remarks", "accreditation_type",
			"report_signature", "signed_by", "pathologist_signature", "pathologist_name",
			"urgent_review_status", "urgent_reviewed_by", "urgent_reviewed_at",
			"custom_sales_invoice",
		]]],
	},
]
