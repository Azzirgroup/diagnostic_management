"""Order intake (Service Request) helpers.

Frontend uses /api/resource/Service Request for list/detail; this module
exposes a "create_order" that bundles multiple lab tests / imaging studies
into a single intake action.
"""

from typing import Any

import frappe
from frappe.utils import nowdate


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
) -> dict:
	"""Create one Service Request per test/imaging entry. Returns the
	created order IDs so the SPA can navigate to the first one."""
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
	created: list[str] = []
	for t in tests:
		template_dt = t.get("template_dt") if isinstance(t, dict) else "Lab Test Template"
		template_dn = t.get("template_dn") if isinstance(t, dict) else t
		subject = t.get("subject") if isinstance(t, dict) else None
		if not template_dn:
			continue
		req: dict[str, Any] = {
			"doctype": "Service Request",
			"patient": patient,
			"patient_name": patient_name,
			"practitioner": practitioner,
			"priority": priority,
			"subject": subject or template_dn,
			"template_dt": template_dt,
			"template_dn": template_dn,
			"status": "Active",
			"occurrence_date": occurrence_date or nowdate(),
		}
		if imaging_modality:
			req["imaging_modality"] = imaging_modality
		if imaging_body_part:
			req["imaging_body_part"] = imaging_body_part
		if contrast_required:
			req["contrast_required"] = 1
		if clinical_history:
			req["clinical_history_text"] = clinical_history
		doc = frappe.get_doc(req).insert(ignore_permissions=False)
		created.append(doc.name)

	return {"ok": True, "orders": created, "count": len(created)}


@frappe.whitelist()
def list_for_patient(patient: str, limit: int = 50) -> list[dict]:
	if not patient:
		return []
	return frappe.get_all(
		"Service Request",
		fields=[
			"name", "status", "priority", "subject", "template_dt", "template_dn",
			"occurrence_date", "creation", "practitioner",
		],
		filters={"patient": patient},
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def worklist(status: str | None = None, priority: str | None = None, limit: int = 100) -> list[dict]:
	"""Lab/Radiology operational worklist — all active orders by default."""
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Active", "Draft", "On Hold"]]
	if priority:
		filters["priority"] = priority
	return frappe.get_all(
		"Service Request",
		fields=[
			"name", "patient", "patient_name", "status", "priority", "subject",
			"template_dt", "template_dn", "occurrence_date", "creation", "practitioner",
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
