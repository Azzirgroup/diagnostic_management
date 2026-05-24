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
			"Radiology Technologist", "Radiologist", "Radiology Manager",
			"Diagnostic Director", "Billing Officer", "Insurance Officer",
			"Referring Doctor", "Auditor",
		]]],
	},
]
