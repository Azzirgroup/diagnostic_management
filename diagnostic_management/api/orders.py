"""Order intake (Service Request) helpers.

Frappe v16 Healthcare's `Service Request` is a FHIR-style doctype with
several required Link fields that the SPA doesn't surface (status as a
Code Value, priority as a Code Value, practitioner, company). This module
normalises friendly input ("Routine", "Active") into the Code Value rows
the doctype expects and back-fills sensible defaults for the SPA flow.
"""

from typing import Any

import frappe
from frappe.utils import nowdate, nowtime


# FHIR-style Code Values for the SPA's friendly aliases. The right-hand
# value is the actual `Code Value` document name in Marley v16.
_STATUS_ALIASES = {
	"active": "active-Request Status",
	"draft": "draft-Request Status",
	"completed": "completed-Request Status",
	"on-hold": "on-hold-Request Status",
	"revoked": "revoked-Request Status",
	"entered-in-error": "entered-in-error-Request Status",
	"unknown": "unknown-Request Status",
}

_PRIORITY_ALIASES = {
	"routine": "Routine-Priority",
	"urgent": "Urgent-Priority",
	"asap": "ASAP-Priority",
	"stat": "STAT-Priority",
	"high": "Urgent-Priority",
}


def _resolve_code_value(table: dict, friendly: str, fallback: str) -> str:
	"""Map a friendly label (e.g. "Routine") to its Code Value name.

	If the looked-up row exists, return its document name. Otherwise return
	`fallback` — the caller can decide whether to retry without the field.
	"""
	if not friendly:
		return fallback
	mapped = table.get(friendly.strip().lower(), friendly)
	if frappe.db.exists("Code Value", mapped):
		return mapped
	# Try the friendly value itself (some sites use plain names).
	if frappe.db.exists("Code Value", friendly):
		return friendly
	return fallback


def _default_practitioner() -> str | None:
	"""Find a sensible practitioner for the current user.

	Preference order:
	  1. Healthcare Practitioner linked to the logged-in user
	  2. Any active Healthcare Practitioner
	  3. None (caller may still skip the field if Marley allows it)
	"""
	user = frappe.session.user
	pr = frappe.db.get_value("Healthcare Practitioner", {"user_id": user}, "name")
	if pr:
		return pr
	return frappe.db.get_value(
		"Healthcare Practitioner",
		{"status": ["in", ["Active", ""]]},
		"name",
	) or frappe.db.get_value("Healthcare Practitioner", {}, "name")


def _default_company() -> str | None:
	return (
		frappe.defaults.get_user_default("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")
	)


@frappe.whitelist()
def create_order(
	patient: str,
	practitioner: str | None = None,
	priority: str = "Routine",
	tests: list | str | None = None,
	clinical_history: str | None = None,
	imaging_modality: str | None = None,
	imaging_body_part: str | None = None,
	contrast_required: int = 0,
	occurrence_date: str | None = None,
	submit: int = 1,
) -> dict:
	"""Create one Service Request per test/imaging entry.

	Returns the created order IDs so the SPA can navigate to the first one.
	Falls back to defaults for status/priority/company/practitioner so the
	SPA doesn't have to know about Marley's FHIR Code Value lookup rules.
	"""
	if isinstance(tests, str):
		import json
		try:
			tests = json.loads(tests)
		except Exception:
			tests = [tests]
	tests = tests or []
	if not patient:
		frappe.throw("patient is required")

	patient_name = frappe.db.get_value("Patient", patient, "patient_name") or ""
	resolved_status = _resolve_code_value(_STATUS_ALIASES, "active", "active-Request Status")
	resolved_priority = _resolve_code_value(_PRIORITY_ALIASES, priority, "")
	resolved_practitioner = practitioner or _default_practitioner()
	resolved_company = _default_company()
	today = occurrence_date or nowdate()
	now_t = nowtime()

	created: list[str] = []
	for t in tests:
		template_dt = t.get("template_dt") if isinstance(t, dict) else "Lab Test Template"
		template_dn = t.get("template_dn") if isinstance(t, dict) else t
		title = (t.get("subject") or t.get("title")) if isinstance(t, dict) else None
		if not template_dn:
			continue
		req: dict[str, Any] = {
			"doctype": "Service Request",
			"patient": patient,
			"patient_name": patient_name,
			"practitioner": resolved_practitioner,
			"title": title or template_dn,
			"template_dt": template_dt,
			"template_dn": template_dn,
			"status": resolved_status,
			"order_date": today,
			"order_time": now_t,
			"occurrence_date": today,
			"company": resolved_company,
		}
		if resolved_priority:
			req["priority"] = resolved_priority
		if imaging_modality:
			req["imaging_modality"] = imaging_modality
		if imaging_body_part:
			req["imaging_body_part"] = imaging_body_part
		if contrast_required:
			req["contrast_required"] = 1
		if clinical_history:
			req["clinical_history_text"] = clinical_history
		doc = frappe.get_doc(req).insert(ignore_permissions=False)
		# `submit=1` (the SPA's "Submit Order" path) advances docstatus 0 → 1
		# and Marley moves status from draft to active. `submit=0` is the
		# "Save as Draft" path — the row stays editable until the user comes
		# back to it.
		if int(submit or 0):
			try:
				if getattr(doc.meta, "is_submittable", 0):
					doc.submit()
			except Exception:
				frappe.log_error(title=f"orders.create_order: submit failed for {doc.name}")
				raise
			# Once submitted, fan the order out into the lab pipeline. Each
			# Lab Test creation triggers Marley's create_sample_collection
			# hook (controlled by Healthcare Settings) so the Sample
			# Collection automatically appears in the Collection worklist.
			_fan_out_to_lab_test(doc)
		created.append(doc.name)

	return {"ok": True, "orders": created, "count": len(created)}


def _fan_out_to_lab_test(service_request) -> str | None:
	"""Create a Lab Test from a submitted Service Request.

	Only fires for Lab-type orders (template_dt == "Lab Test Template"). For
	imaging / procedure orders Marley uses a different downstream doctype, so
	we skip and let those flows be handled elsewhere.
	"""
	if (service_request.template_dt or "") != "Lab Test Template":
		return None
	if not service_request.template_dn:
		return None
	# Skip if a Lab Test already exists for this service request (e.g. user
	# re-submitted manually). Marley's controller throws otherwise.
	existing = frappe.db.get_value(
		"Lab Test",
		{"service_request": service_request.name, "docstatus": ["!=", 2]},
		"name",
	)
	if existing:
		return existing
	try:
		patient_sex = frappe.db.get_value("Patient", service_request.patient, "sex") or "Other"
		lab_test = frappe.get_doc({
			"doctype": "Lab Test",
			"patient": service_request.patient,
			"patient_sex": patient_sex,
			"template": service_request.template_dn,
			"service_request": service_request.name,
			"company": service_request.company,
			"practitioner": service_request.practitioner,
			"status": "Draft",
		})
		lab_test.insert(ignore_permissions=False)
		return lab_test.name
	except Exception:
		frappe.log_error(title=f"orders._fan_out_to_lab_test failed for {service_request.name}")
		return None


@frappe.whitelist()
def update_order(
	name: str,
	patient: str | None = None,
	priority: str | None = None,
	title: str | None = None,
	clinical_history: str | None = None,
	occurrence_date: str | None = None,
	submit: int = 0,
) -> dict:
	"""Update a DRAFT Service Request. Submitted orders are read-only.

	With `submit=1` the doc is saved AND submitted in one round trip — this
	is the SPA's "Submit Order" button on the edit page. With `submit=0`
	(default) the doc is saved but stays as draft (`Save as Draft`).
	"""
	if not name:
		frappe.throw("name is required")
	doc = frappe.get_doc("Service Request", name)
	if int(doc.docstatus or 0) != 0:
		frappe.throw("Only draft orders can be edited")
	if patient and patient != doc.patient:
		doc.patient = patient
		doc.patient_name = frappe.db.get_value("Patient", patient, "patient_name") or doc.patient_name
	if priority:
		resolved = _resolve_code_value(_PRIORITY_ALIASES, priority, priority)
		if resolved:
			doc.priority = resolved
	if title is not None:
		doc.title = title
	if clinical_history is not None and hasattr(doc, "clinical_history_text"):
		doc.clinical_history_text = clinical_history
	if occurrence_date:
		doc.occurrence_date = occurrence_date
		doc.order_date = occurrence_date
	doc.save(ignore_permissions=False)
	if int(submit or 0) and getattr(doc.meta, "is_submittable", 0):
		try:
			doc.submit()
		except Exception:
			frappe.log_error(title=f"orders.update_order: submit failed for {doc.name}")
			raise
	return {"ok": True, "name": doc.name, "docstatus": doc.docstatus}


@frappe.whitelist()
def list_for_patient(patient: str, limit: int = 50) -> list[dict]:
	if not patient:
		return []
	return frappe.get_all(
		"Service Request",
		fields=[
			"name", "status", "priority", "title", "template_dt", "template_dn",
			"occurrence_date", "creation", "practitioner",
		],
		filters={"patient": patient},
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def worklist(status: str | None = None, priority: str | None = None, limit: int = 100) -> list[dict]:
	"""Lab/Radiology operational worklist — all active orders by default.

	Service Request status is a Link to Code Value, so the filter compares
	against the full Code Value document name (e.g. "active-Request Status"),
	not the friendly alias.
	"""
	filters: dict = {}
	if status:
		filters["status"] = _resolve_code_value(_STATUS_ALIASES, status, status)
	else:
		filters["status"] = ["in", [
			"active-Request Status",
			"draft-Request Status",
			"on-hold-Request Status",
		]]
	if priority:
		filters["priority"] = _resolve_code_value(_PRIORITY_ALIASES, priority, priority)
	return frappe.get_all(
		"Service Request",
		fields=[
			"name", "patient", "patient_name", "status", "priority", "title",
			"template_dt", "template_dn", "occurrence_date", "creation", "practitioner",
			"docstatus",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def cancel(name: str, reason: str = "") -> dict:
	doc = frappe.get_doc("Service Request", name)
	doc.db_set("status", "Cancelled")
	if reason:
		doc.add_comment("Comment", text=f"<b>Order Cancelled</b><br>{frappe.utils.escape_html(reason)}")
	return {"ok": True, "name": name, "status": "Cancelled"}


@frappe.whitelist()
def test_catalog(query: str = "", limit: int = 50) -> list[dict]:
	"""Return a unified test catalog (Lab + Imaging) for the order intake search."""
	q = (query or "").strip()
	rows: list[dict] = []
	lab_filters = {"disabled": 0} if _has_field("Lab Test Template", "disabled") else {}
	if q:
		lab_filters_or = [
			["Lab Test Template", "lab_test_name", "like", f"%{q}%"],
			["Lab Test Template", "name", "like", f"%{q}%"],
		]
	else:
		lab_filters_or = None
	try:
		labs = frappe.get_all(
			"Lab Test Template",
			fields=["name", "lab_test_name", "lab_test_rate", "sample"],
			filters=lab_filters,
			or_filters=lab_filters_or,
			limit_page_length=int(limit),
			order_by="lab_test_name",
		)
	except Exception:
		labs = []
	for r in labs:
		rows.append({
			"template_dt": "Lab Test Template",
			"template_dn": r["name"],
			"label": r.get("lab_test_name") or r["name"],
			"rate": r.get("lab_test_rate"),
			"sample": r.get("sample"),
			"category": "Lab",
		})
	# Optional: imaging templates if installed (Clinical Procedure Template etc.)
	try:
		if frappe.db.exists("DocType", "Clinical Procedure Template"):
			proc = frappe.get_all(
				"Clinical Procedure Template",
				fields=["name", "template", "rate"],
				or_filters=[["Clinical Procedure Template", "template", "like", f"%{q}%"]] if q else None,
				limit_page_length=int(limit),
				order_by="template",
			)
			for r in proc:
				rows.append({
					"template_dt": "Clinical Procedure Template",
					"template_dn": r["name"],
					"label": r.get("template") or r["name"],
					"rate": r.get("rate"),
					"category": "Procedure",
				})
	except Exception:
		pass
	return rows


def _has_field(doctype: str, fieldname: str) -> bool:
	try:
		if not frappe.db.exists("DocType", doctype):
			return False
		return any(df.fieldname == fieldname for df in frappe.get_meta(doctype).fields)
	except Exception:
		return False
