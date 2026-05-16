"""Patient-centric helpers used by the SPA.

The frontend uses /api/resource/Patient for CRUD; this module supplies the
typeahead/search payload and a richer detail view that pulls together orders
and reports for the patient profile page.
"""

import frappe


_PATIENT_FIELDS = [
	"name", "patient_name", "sex", "dob", "mobile", "email",
	"blood_group", "uid", "image", "status",
]


@frappe.whitelist()
def search(query: str = "", limit: int = 25) -> list[dict]:
	"""Lightweight typeahead. Matches name/MRN/mobile/email."""
	q = (query or "").strip()
	limit = max(1, min(int(limit or 25), 100))
	filters = []
	if q:
		filters = [
			["Patient", "patient_name", "like", f"%{q}%"],
		]
	rows = frappe.get_all(
		"Patient",
		fields=_PATIENT_FIELDS,
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
		fields=["name", "status", "priority", "subject", "template_dt", "template_dn", "occurrence_date", "creation"],
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
	mobile: str | None = None,
	email: str | None = None,
	blood_group: str | None = None,
	uid: str | None = None,
	permanent_address: str | None = None,
) -> dict:
	"""Convenience create. Skips fields the frontend doesn't expose so users
	can register a patient with just the required minimum."""
	doc = frappe.get_doc({
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
	}).insert(ignore_permissions=False)
	return {"ok": True, "name": doc.name, "patient_name": doc.patient_name}
