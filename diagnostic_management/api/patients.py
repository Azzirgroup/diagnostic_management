"""Patient-centric helpers used by the SPA.

The frontend uses /api/resource/Patient for CRUD; this module supplies the
typeahead/search payload and a richer detail view that pulls together orders
and reports for the patient profile page.

Branch scoping note:
  These endpoints use `frappe.get_all`, which bypasses Frappe's
  `permission_query_conditions` hook. The SPA's branch-scoping rule
  (User → Branch → only sees same-branch Patients) is applied here
  explicitly via `_branch_filter()` so the result respects the user's
  branch even though we skip the standard list-perm machinery.
"""

import frappe
from diagnostic_management.api.branches import _user_branch


def _branch_filter() -> dict:
	"""Filter dict restricting Patient to the calling user's branch.

	STRICT: only matches Patient.branch == user's branch. Branchless
	(legacy) patients are HIDDEN from branch-scoped users — back-fill them
	with a branch (see `branches.backfill_patient_branches`) so they show
	up in the right place. Empty dict for admins / unscoped users (see all).
	"""
	b = _user_branch()
	if not b:
		return {}
	return {"branch": b}


_PATIENT_FIELDS = [
	"name", "patient_name", "sex", "dob", "mobile", "email",
	"blood_group", "uid", "image", "status",
]


@frappe.whitelist()
def search(query: str = "", limit: int = 25) -> list[dict]:
	"""Lightweight typeahead. Matches name/MRN/mobile/email.

	Results are filtered to the calling user's branch (see _branch_filter)
	so a Lab Tech in Branch A only sees Branch A's patients in the typeahead."""
	q = (query or "").strip()
	limit = max(1, min(int(limit or 25), 100))
	rows = frappe.get_all(
		"Patient",
		fields=_PATIENT_FIELDS + ["branch"],
		filters=_branch_filter(),
		or_filters=[
			["Patient", "patient_name", "like", f"%{q}%"],
			["Patient", "name", "like", f"%{q}%"],
			["Patient", "mobile", "like", f"%{q}%"],
			["Patient", "email", "like", f"%{q}%"],
		] if q else None,
		limit_page_length=limit,
		order_by="modified desc",
	)
	return rows or []


@frappe.whitelist()
def detail(name: str) -> dict:
	"""Return the patient record + recent orders/reports/samples for the profile page."""
	if not name:
		frappe.throw("Missing patient")
	patient = frappe.get_doc("Patient", name)
	out = patient.as_dict()

	out["orders"] = frappe.get_all(
		"Service Request",
		fields=["name", "status", "priority", "title", "template_dt", "template_dn", "occurrence_date", "creation"],
		filters={"patient": name},
		order_by="creation desc",
		limit_page_length=20,
	)
	out["samples"] = frappe.get_all(
		"Sample Collection",
		fields=["name", "sample", "sample_qty", "status", "creation"],
		filters={"patient": name},
		order_by="creation desc",
		limit_page_length=20,
	)
	out["reports"] = frappe.get_all(
		"Diagnostic Report",
		fields=["name", "docname", "status", "is_critical", "critical_acknowledged", "creation"],
		filters={"patient": name},
		order_by="creation desc",
		limit_page_length=20,
	) if frappe.db.exists("DocType", "Diagnostic Report") else []
	out["invoices"] = frappe.get_all(
		"Sales Invoice",
		fields=["name", "customer", "grand_total", "outstanding_amount", "status", "posting_date"],
		filters={"patient": name} if _has_invoice_patient() else {"customer_name": ["like", f"%{patient.patient_name or ''}%"]},
		order_by="posting_date desc",
		limit_page_length=20,
	)
	return out


def _has_invoice_patient() -> bool:
	try:
		meta = frappe.get_meta("Sales Invoice")
		return any(df.fieldname == "patient" for df in meta.fields)
	except Exception:
		return False


@frappe.whitelist()
def create_basic(
	first_name: str,
	last_name: str | None = None,
	sex: str = "Other",
	dob: str | None = None,
	custom_age: float | int | None = None,
	custom_age_type: str | None = None,
	mobile: str | None = None,
	email: str | None = None,
	blood_group: str | None = None,
	uid: str | None = None,
	permanent_address: str | None = None,
	branch: str | None = None,
) -> dict:
	"""Convenience create. Skips fields the frontend doesn't expose so users
	can register a patient with just the required minimum.

	Age can be supplied either as `dob` (Date) OR as `custom_age` +
	`custom_age_type` (Years / Months / Days) — the latter matches how
	receptionists actually take patient info at the desk ("30 years old",
	not a birth date). If both are given, DOB wins.

	`branch`: if supplied, written onto Patient.branch. If omitted, the
	`auto_set_patient_branch` validate hook falls back to the creating
	user's branch tag — so reception staff at Westlands get Westlands
	patients by default."""
	payload = {
		"doctype": "Patient",
		"first_name": first_name,
		"last_name": last_name or "",
		"sex": sex,
		"dob": dob,
		"mobile": mobile,
		"email": email,
		"blood_group": blood_group,
		"uid": uid,
		"permanent_address": permanent_address,
		"status": "Active",
	}
	# Only stamp custom_age fields when DOB isn't provided AND the site
	# actually has those custom fields installed (they're custom_field on
	# Patient — safe-guard so a fresh site without them doesn't fail).
	if not dob and custom_age not in (None, "", 0, "0"):
		pmeta = {df.fieldname for df in frappe.get_meta("Patient").fields}
		if "custom_age" in pmeta:
			payload["custom_age"] = float(custom_age)
		if "custom_age_type" in pmeta:
			payload["custom_age_type"] = (custom_age_type or "Years").strip() or "Years"
	if branch:
		payload["branch"] = branch
	doc = frappe.get_doc(payload).insert(ignore_permissions=False)
	return {"ok": True, "name": doc.name, "patient_name": doc.patient_name}


@frappe.whitelist()
def update_basic(
	name: str,
	first_name: str | None = None,
	last_name: str | None = None,
	sex: str | None = None,
	dob: str | None = None,
	mobile: str | None = None,
	email: str | None = None,
	blood_group: str | None = None,
	uid: str | None = None,
	permanent_address: str | None = None,
) -> dict:
	"""Edit the same basic fields exposed by `create_basic`. Only fields the
	caller actually sends are written — None means "leave it alone". Empty
	string is a real value, so the user can clear an optional field by passing
	"".
	"""
	doc = frappe.get_doc("Patient", name)
	# Map of arg -> value; only apply when the caller sent it.
	updates = {
		"first_name": first_name, "last_name": last_name, "sex": sex, "dob": dob,
		"mobile": mobile, "email": email, "blood_group": blood_group, "uid": uid,
		"permanent_address": permanent_address,
	}
	for field, value in updates.items():
		if value is not None:
			doc.set(field, value)
	# Marley Healthcare's Patient.set_contact saves the linked Contact in the
	# same transaction, which bumps Contact.modified and then makes its own
	# follow-up Contact save trip Frappe's timestamp check. Skip the version
	# check on this save — we already loaded the latest Patient doc above.
	doc.flags.ignore_version = True
	doc.save(ignore_permissions=False)
	return {"ok": True, "name": doc.name, "patient_name": doc.patient_name}
