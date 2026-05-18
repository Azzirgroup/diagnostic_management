"""Radiology workflow endpoints — reading worklist, pre-authorization, reports."""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def reading_worklist(
	modality: str | None = None,
	priority: str | None = None,
	status: str | None = None,
	limit: int = 100,
) -> list[dict]:
	"""Imaging Service Requests pending interpretation."""
	filters: dict = {}
	if modality:
		filters["imaging_modality"] = modality
	if priority:
		filters["priority"] = priority
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["active-Request Status", "on-hold-Request Status"]]
	# Imaging orders carry an imaging_modality custom field
	or_filters = None
	try:
		meta = frappe.get_meta("Service Request")
		if any(df.fieldname == "imaging_modality" for df in meta.fields):
			filters["imaging_modality"] = filters.get("imaging_modality") or ["!=", ""]
	except Exception:
		pass
	return frappe.get_all(
		"Service Request",
		fields=[
			"name", "patient", "patient_name", "priority", "title",
			"imaging_modality", "imaging_body_part", "contrast_required",
			"clinical_history_text", "occurrence_date", "status", "creation",
			"practitioner",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def dashboard() -> dict:
	def _count(dt: str, filters: dict | None = None) -> int:
		try:
			return frappe.db.count(dt, filters or {})
		except Exception:
			return 0
	return {
		"pending_studies": _count("Service Request", {"imaging_modality": ["!=", ""], "status": "active-Request Status"}),
		"pending_pre_auth": _count("Radiology Pre-Auth", {"status": ["in", ["Draft", "Submitted", "In Review"]]}),
		"approved_pre_auth": _count("Radiology Pre-Auth", {"status": "Approved"}),
		"reports_pending": _count("Diagnostic Report", {"status": ["in", ["Open", "Pending Review", "Partially Approved"]]}),
		"critical": _count("Diagnostic Report", {"is_critical": 1, "critical_acknowledged": 0}),
	}


# -- Pre-Authorization ------------------------------------------------------

@frappe.whitelist()
def preauth_queue(status: str | None = None, limit: int = 100) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Draft", "Submitted", "In Review"]]
	return frappe.get_all(
		"Radiology Pre-Auth",
		fields=[
			"name", "patient", "patient_name", "modality", "body_part",
			"urgency", "payor", "policy_number", "estimated_amount",
			"status", "submitted_date", "approved_amount", "approval_reference",
		],
		filters=filters,
		order_by="submitted_date desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def create_preauth(
	patient: str,
	modality: str | None = None,
	body_part: str | None = None,
	urgency: str = "Routine",
	payor: str | None = None,
	policy: str | None = None,
	policy_number: str | None = None,
	estimated_amount: float = 0,
	clinical_justification: str | None = None,
	service_request: str | None = None,
) -> dict:
	doc = frappe.get_doc({
		"doctype": "Radiology Pre-Auth",
		"patient": patient,
		"modality": modality,
		"body_part": body_part,
		"urgency": urgency,
		"payor": payor,
		"policy": policy,
		"policy_number": policy_number,
		"estimated_amount": estimated_amount,
		"clinical_justification": clinical_justification,
		"service_request": service_request,
		"status": "Open",
	}).insert(ignore_permissions=False)
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def submit_preauth(name: str) -> dict:
	doc = frappe.get_doc("Radiology Pre-Auth", name)
	doc.status = "Submitted"
	doc.submitted_date = now_datetime()
	doc.save(ignore_permissions=False)
	return {"ok": True, "name": name, "status": "Submitted"}


@frappe.whitelist()
def decide_preauth(
	name: str,
	decision: str,
	approved_amount: float | None = None,
	approval_reference: str | None = None,
	denial_reason: str | None = None,
) -> dict:
	if decision not in ("Approved", "Denied", "Expired", "Cancelled"):
		frappe.throw("Invalid decision")
	doc = frappe.get_doc("Radiology Pre-Auth", name)
	doc.status = decision
	doc.decision_date = now_datetime()
	if approved_amount is not None:
		doc.approved_amount = float(approved_amount)
	if approval_reference:
		doc.approval_reference = approval_reference
	if denial_reason:
		doc.denial_reason = denial_reason
	doc.save(ignore_permissions=False)
	return {"ok": True, "name": name, "status": decision}


# -- Report Editor ----------------------------------------------------------

@frappe.whitelist()
def save_report(
	name: str | None = None,
	patient: str | None = None,
	service_request: str | None = None,
	practitioner: str | None = None,
	findings: str | None = None,
	impression: str | None = None,
	recommendations: str | None = None,
	is_critical: int = 0,
	status: str = "Open",
) -> dict:
	"""Create or update a Diagnostic Report tied to an imaging order."""
	doc = (
		frappe.get_doc("Diagnostic Report", name)
		if name and frappe.db.exists("Diagnostic Report", name)
		else frappe.new_doc("Diagnostic Report")
	)
	if patient:
		doc.patient = patient
	if practitioner:
		doc.practitioner = practitioner
	# Free-text fields stored in conclusion / longtext columns when present
	conclusion_parts = []
	if findings:
		conclusion_parts.append(f"FINDINGS:\n{findings}")
	if impression:
		conclusion_parts.append(f"IMPRESSION:\n{impression}")
	if recommendations:
		conclusion_parts.append(f"RECOMMENDATIONS:\n{recommendations}")
	if conclusion_parts and "conclusion" in {df.fieldname for df in doc.meta.fields}:
		doc.conclusion = "\n\n".join(conclusion_parts)
	if "is_critical" in {df.fieldname for df in doc.meta.fields}:
		doc.is_critical = 1 if int(is_critical or 0) else 0
	if "status" in {df.fieldname for df in doc.meta.fields}:
		doc.status = status
	if doc.is_new():
		doc.insert(ignore_permissions=False)
	else:
		doc.save(ignore_permissions=False)
	return {"ok": True, "name": doc.name, "status": doc.status}
