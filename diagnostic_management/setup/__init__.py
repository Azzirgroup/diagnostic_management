"""Idempotent setup helpers run from hooks.after_install / after_migrate.

Everything ADMS adds to other apps (Marley, ERPNext) is installed here:
- Custom Fields on Patient, Healthcare Practitioner, Lab Test Template,
  Service Request, Sample Collection, Diagnostic Report, Healthcare Settings.
- Roles introduced by ADMS (Lab Manager, Radiologist, Phlebotomist, etc.).
- Default Code System rows for LOINC / SNOMED / ICD-10 placeholders.

None of these change Marley source files — they are pure additive overlays.
"""

import frappe

from .accounting_dimension import ensure_branch_accounting_dimension  # noqa: F401
from .custom_fields import install_custom_fields  # noqa: F401
from .print_formats import install_print_formats  # noqa: F401
from .roles import install_roles  # noqa: F401
from .seed_data import install_seed_data  # noqa: F401
from .workspaces import install_director_and_lab_manager_workspaces  # noqa: F401


def _ensure_desk_icon():
	"""Make sure the Desktop Icon + Workspace Sidebar exist for ADMS.

	Frappe normally creates these on `after_app_install`, but if that hook
	doesn't run (e.g. the app was installed before `add_to_apps_screen` was
	wired up), the tile is missing from /desk. Calling the generator here is
	idempotent — it skips icons that already exist.
	"""
	try:
		from frappe.utils.install import auto_generate_icons_and_sidebar
		auto_generate_icons_and_sidebar()
	except Exception:
		# Don't block install/migrate if the desk icon helper changes shape.
		import frappe
		frappe.log_error(title="ADMS: failed to auto-generate desktop icon")


def _ensure_healthcare_settings():
	"""Turn on the Marley settings the SPA depends on.

	`create_sample_collection_for_lab_test`: when ON, creating a Lab Test
	auto-creates a Sample Collection row — that's what makes the Collection
	worklist populate once orders are placed. Off by default in Marley.
	"""
	import frappe
	try:
		frappe.db.set_single_value(
			"Healthcare Settings",
			"create_sample_collection_for_lab_test",
			1,
		)
	except Exception:
		frappe.log_error(title="ADMS: failed to enable auto sample-collection")


def _ensure_workspace_sidebars_populated():
	"""Re-populate empty Workspace Sidebar shells for our workspaces.

	Frappe's `create_workspace_sidebar_for_workspaces` skips any workspace
	that already has a Workspace Sidebar record — so if a sidebar shell
	exists but its items table is empty (e.g. because the parent Workspace
	was manually deleted and recreated), the user lands on a "No Sidebar
	Items" page. This helper deletes empty shells so the generator will
	rebuild them on the next migrate / direct call.
	"""
	import frappe

	try:
		our_workspaces = frappe.get_all(
			"Workspace",
			filters={"app": "diagnostic_management"},
			pluck="name",
		)
	except Exception:
		our_workspaces = []

	rebuild_needed = False
	for ws in our_workspaces:
		try:
			# A sidebar with zero items is the broken case we need to fix.
			has_items = frappe.db.exists(
				"Workspace Sidebar Item",
				{"parent": ws, "parenttype": "Workspace Sidebar"},
			)
			if frappe.db.exists("Workspace Sidebar", ws) and not has_items:
				frappe.db.delete("Workspace Sidebar", {"name": ws})
				rebuild_needed = True
		except Exception:
			pass

	if rebuild_needed:
		try:
			from frappe.desk.doctype.workspace_sidebar.workspace_sidebar import (
				create_workspace_sidebar_for_workspaces,
			)
			create_workspace_sidebar_for_workspaces()
		except Exception:
			frappe.log_error(title="ADMS: failed to rebuild workspace sidebars")


def _ensure_apps_screen_tiles():
	"""Synchronise the desk Apps-screen tiles with hooks.add_to_apps_screen.

	`add_to_apps_screen` only fires on `after_install` in Frappe, so a tile
	added after the app was installed never appears unless we manually upsert
	the corresponding Desktop Icon row. This helper iterates the hook config
	and reconciles each entry — adds missing tiles, refreshes logo/route on
	existing ones, and unhides any that were hidden by orphan cleanup.
	"""
	import frappe

	try:
		entries = frappe.get_hooks("add_to_apps_screen", app_name="diagnostic_management") or []
	except Exception:
		entries = []

	for raw in entries:
		# Hook values come as dicts wrapped in a list of dicts of lists in Frappe.
		entry = _normalize_hook_entry(raw)
		if not entry or not entry.get("title"):
			continue
		title = entry["title"]
		try:
			existing = frappe.db.get_value("Desktop Icon", {"label": title}, "name")
			if existing:
				doc = frappe.get_doc("Desktop Icon", existing)
			else:
				doc = frappe.new_doc("Desktop Icon")
				doc.label = title
			doc.app = "diagnostic_management"
			doc.link = entry.get("route") or "/diagnostic_management"
			doc.logo_url = entry.get("logo") or doc.logo_url
			# Desktop Icon.icon_type only accepts Link/Folder/App — "Link" is the
			# correct choice for a URL-routed tile.
			doc.icon_type = "Link"
			doc.standard = 1
			doc.hidden = 0
			doc.flags.ignore_permissions = True
			doc.save() if existing else doc.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to sync apps-screen tile {title}")


def _normalize_hook_entry(raw):
	# frappe.get_hooks returns values flattened; each entry can be a dict or a
	# list-of-dicts depending on how the hook was registered. Coerce both shapes
	# into a single dict so callers don't have to special-case.
	if isinstance(raw, dict):
		# Some hooks come back as { key: [value] } — un-listify the single values.
		out = {}
		for k, v in raw.items():
			out[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
		return out
	return None


def after_install():
	install_roles()
	install_custom_fields()
	ensure_branch_accounting_dimension()
	install_print_formats()
	install_seed_data()
	_ensure_healthcare_settings()
	_ensure_desk_icon()
	_ensure_apps_screen_tiles()
	_ensure_workspace_sidebars_populated()
	_ensure_shift_role_perms()
	install_director_and_lab_manager_workspaces()
	_pin_patient_field_uniqueness()
	_pin_default_print_formats()
	_allow_doctor_after_submit()
	_align_lab_report_status_options()
	_allow_result_edit_after_submit()
	_ensure_user_company_default()


def after_migrate():
	# Custom fields & print formats are idempotent — safe to re-run on every
	# migrate, so updates to either land without manual import steps.
	install_custom_fields()
	ensure_branch_accounting_dimension()
	install_print_formats()
	install_seed_data()
	_ensure_healthcare_settings()
	_ensure_desk_icon()
	_ensure_apps_screen_tiles()
	_ensure_workspace_sidebars_populated()
	_ensure_shift_role_perms()
	install_director_and_lab_manager_workspaces()
	_pin_patient_field_uniqueness()
	_pin_default_print_formats()
	_allow_doctor_after_submit()
	_align_lab_report_status_options()
	_allow_result_edit_after_submit()
	_ensure_user_company_default()
	# Fill `branch` on historical financial docs (Sales Invoice / Payment
	# Entry / Purchase Invoice / Journal Entry) that posted before the
	# Branch dimension was registered. Idempotent — only touches rows with
	# branch IS NULL.
	from diagnostic_management.finance.stamp import backfill_branch_on_existing_docs
	backfill_branch_on_existing_docs()


def _ensure_shift_role_perms():
	"""Grant the shift-using roles (Billing Officer / Receptionist / Lab
	Manager / Diagnostic Director) read+create+write on POS Profile / POS
	Opening Entry / POS Closing Entry. Idempotent: skips rows that exist."""
	import frappe

	plan = {
		"POS Profile": {
			"Billing Officer": {"read": 1},
			"Receptionist": {"read": 1},
			"Lab Manager": {"read": 1, "write": 1, "create": 1},
			"Diagnostic Director": {"read": 1, "write": 1, "create": 1},
		},
		"POS Opening Entry": {
			"Billing Officer": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Receptionist": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Lab Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
			"Diagnostic Director": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
		},
		"POS Closing Entry": {
			"Billing Officer": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Receptionist": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Lab Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
			"Diagnostic Director": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
		},
	}
	for dt, role_perms in plan.items():
		if not frappe.db.exists("DocType", dt):
			continue
		for role, perms in role_perms.items():
			if not frappe.db.exists("Role", role):
				continue
			existing = frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role})
			if existing:
				continue
			cd = frappe.get_doc({
				"doctype": "Custom DocPerm",
				"parent": dt, "parenttype": "DocType", "parentfield": "permissions",
				"role": role, "permlevel": 0, **perms,
			})
			cd.flags.ignore_permissions = True
			cd.insert()
	frappe.clear_cache()


def _pin_default_print_formats():
	"""Set Sales Invoice default_print_format to 'Genetest Sales Invoice'
	so any 'Print' action (Desk + SPA) uses it without the user picking.
	Idempotent — make_property_setter upserts by (doc_type, field_name,
	property)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	if frappe.db.exists("Print Format", "Genetest Sales Invoice"):
		try:
			make_property_setter(
				"Sales Invoice", None, "default_print_format",
				"Genetest Sales Invoice", "Data",
				for_doctype=True, validate_fields_for_doctype=False,
			)
		except Exception:
			frappe.log_error(title="_pin_default_print_formats(SalesInvoice) failed")


def _align_lab_report_status_options():
	"""Sync the Select `options` on Lab Report child tables' `status` field with
	the canonical enum (Normal / High / Low / … / Pre-diabetic / Diabetic).

	Historical Property Setters on these child doctypes shipped without the
	banded labels (Pre-diabetic / Diabetic), so `_build_lab_report` — which
	now derives status via `banded_flag` for HbA1c-like analytes — fails
	validation with `Row #N: Status cannot be "Diabetic". It should be one of
	"Normal", "High", ...`. This helper rewrites those Property Setters (kept
	as PS rather than deleted so a manual customisation stays reversible).

	Idempotent — `make_property_setter` upserts by (doc_type, field_name,
	property)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	# Leading blank kept — matches the original PS shape so the dropdown
	# still offers an "empty" pick that the frontend uses for unset rows.
	CANONICAL = (
		"\nNormal\nHigh\nLow\nAbnormal\nCritical\nOptimal\nIntermediate"
		"\nDeficiency\nInsufficiency\nSufficiency\nPotential Toxicity"
		"\nPre-diabetic\nDiabetic"
	)
	for dt in ("Lab Report Numeric Result", "Lab Report Test",
	           "Lab Report Grouped Result", "Lab Report Qualitative Result"):
		if not frappe.db.exists("DocType", dt):
			continue
		try:
			make_property_setter(
				dt, "status", "options", CANONICAL, "Text",
				for_doctype=False, validate_fields_for_doctype=False,
			)
		except Exception:
			frappe.log_error(title=f"_align_lab_report_status_options({dt}) failed")


def _ensure_user_company_default():
	"""Stamp the site's Company as a per-user default on every enabled user.

	Without this, standard ERPNext reports opened from the desk (Sales
	Register, Accounts Receivable, Cash Flow, Profitability Analysis, …)
	render EMPTY: the Framework UI auto-populates the Company filter from
	the user's DefaultValue map, and if it's missing, the filter goes in
	blank → SQL matches nothing → report looks empty even though rows
	exist. Symptom: Director Workspace KPI cards show real revenue but
	every linked report is empty.

	We only stamp when the site has EXACTLY ONE Company — multi-company
	sites need the user to pick their own default via User Settings.
	Idempotent: only inserts a DefaultValue row when one doesn't already
	exist for that user."""
	companies = frappe.get_all("Company", pluck="name")
	if len(companies) != 1:
		return
	company = companies[0]
	users = frappe.get_all("User",
		filters={"enabled": 1, "user_type": ["!=", "Website User"]},
		pluck="name")
	from frappe.defaults import add_default
	for u in users:
		if u in ("Administrator", "Guest"):
			continue
		existing = frappe.db.exists("DefaultValue",
			{"parent": u, "defkey": "company"})
		if existing:
			continue
		try:
			add_default("company", company, u, parenttype="User Permission")
		except Exception:
			# Signature differs by Frappe version — fall back to raw insert.
			try:
				frappe.get_doc({
					"doctype": "DefaultValue",
					"parent": u, "parenttype": "User Permission",
					"parentfield": "system_defaults",
					"defkey": "company", "defvalue": company,
				}).insert(ignore_permissions=True)
			except Exception:
				frappe.log_error(title=f"_ensure_user_company_default({u}) failed")


def _allow_result_edit_after_submit():
	"""Let peer-review corrections edit result values on submitted Lab Tests.

	The peer-review path used to CANCEL the Lab Test and copy_doc a new
	`-1` amendment — Frappe's default `amend_doc` flow. Two failure modes
	followed: the amendment carried the old values forward (looked like
	the reviewer's correction was ignored), and rebills piled a second
	batch onto the same reused Sample Collection (duplicate rows on
	Results). The new peer-review "Send Back for Correction" path keeps
	the Lab Test submitted and mutates result rows in place; each mutation
	is audit-logged as a Comment on the parent Lab Test. To make that
	possible without cancelling, the mutable result fields must be
	allow_on_submit.

	Idempotent — `make_property_setter` upserts by
	(doc_type, field_name, property)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	targets = [
		# Numeric / range analytes (Chemistry, Haematology).
		("Normal Test Result", "result_value"),
		("Normal Test Result", "lab_test_comment"),
		# Free-text narratives (Histology, Radiology-narrative).
		("Descriptive Test Result", "result_value"),
		# Microbiology — antibiotic sensitivity (which drug, susceptibility).
		("Sensitivity Test Result", "antibiotic"),
		("Sensitivity Test Result", "antibiotic_sensitivity"),
		# Microbiology — organism identification + colony count.
		("Organism Test Result", "organism"),
		("Organism Test Result", "colony_population"),
		("Organism Test Result", "colony_uom"),
	]
	for dt, field in targets:
		if not frappe.db.exists("DocType", dt):
			continue
		try:
			make_property_setter(
				dt, field, "allow_on_submit", "1", "Check",
				for_doctype=False, validate_fields_for_doctype=False,
			)
		except Exception:
			frappe.log_error(title=f"_allow_result_edit_after_submit({dt}.{field}) failed")


def _allow_doctor_after_submit():
	"""Allow `Sales Invoice.custom_doctor` to be edited AFTER the invoice
	is submitted. Without this the field is locked once the SI is
	docstatus=1 — and legacy invoices that were imported/created without
	a Referring Doctor would need to be cancelled + amended to correct.

	Idempotent property setter; ships in `after_install` + `after_migrate`."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	try:
		make_property_setter(
			"Sales Invoice", "custom_doctor", "allow_on_submit", "1", "Check",
			for_doctype=False, validate_fields_for_doctype=False,
		)
	except Exception:
		frappe.log_error(title="_allow_doctor_after_submit(SalesInvoice) failed")


def _pin_patient_field_uniqueness():
	"""Defensively pin Property Setters that relax Healthcare's Patient
	uniqueness constraints. Clinics commonly need to:

	  - Use the same `mobile` for related patients (parent + child, etc.).
	    Healthcare's Patient.mobile is already unique=0, but we pin it to
	    survive any upstream change.
	  - Use the same `uid` (National ID / MRN) for related records when the
	    workflow uses that field as a household identifier.

	Idempotent — `make_property_setter` with `for_doctype=False` upserts
	the row keyed by (doc_type, field_name, property)."""
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter
	for field in ("mobile", "uid"):
		try:
			make_property_setter(
				"Patient", field, "unique", "0", "Int",
				for_doctype=False, validate_fields_for_doctype=False,
			)
		except Exception:
			# Skip silently when the Patient doctype isn't installed on this
			# site or the field doesn't exist (e.g. customised Healthcare).
			frappe.log_error(title=f"_pin_patient_field_uniqueness({field}) failed")
