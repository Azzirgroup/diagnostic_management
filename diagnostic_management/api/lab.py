"""Lab Hub / Verification Queue / Peer Review endpoints.

Marley v16 doctype status fields use the SELECT options below — none of
which match the friendly names I had originally:
  Sample Collection:    Pending / Partly Collected / Collected
  Diagnostic Report:    Open / Pending Review / Partially Approved / Approved / Rejected
  Lab Test:             Draft / Completed / Approved / Rejected / Cancelled

Filters and writes throughout this module use those actual values.
"""

import frappe
from frappe.utils import now_datetime


# Diagnostic Report's "verifiable / pending" set — anything not yet Approved.
DR_PENDING = ["Open", "Pending Review", "Partially Approved"]


@frappe.whitelist()
def hub_summary() -> dict:
	"""Counts the Lab Hub home page renders as quick-glance KPIs."""
	def _count(dt: str, filters: dict | None = None) -> int:
		try:
			return frappe.db.count(dt, filters or {})
		except Exception:
			return 0

	return {
		"pending_accession": _count("Sample Collection", {"status": "Pending"}),
		"in_analysis": _count("Sample Collection", {"status": "Partly Collected"}),
		"pending_verification": _count("Diagnostic Report", {"status": ["in", DR_PENDING]}),
		"qc_open": _count("QC Run", {"status": "Pending Review"}),
		"calibration_due": _count("Calibration Run", {"status": "Scheduled"}),
		"peer_review_open": _count("Peer Review Case", {"status": ["in", ["Open", "In Review", "Discussion"]]}),
	}


@frappe.whitelist()
def verification_queue(limit: int = 100) -> list[dict]:
	"""Diagnostic Reports waiting for verification."""
	return frappe.get_all(
		"Diagnostic Report",
		fields=[
			"name", "docname", "patient", "patient_name", "practitioner",
			"status", "is_critical", "critical_acknowledged", "creation", "modified",
		],
		filters={"status": ["in", DR_PENDING]},
		order_by="modified desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def verify_report(name: str, conclusion: str | None = None) -> dict:
	"""Verify and release a Diagnostic Report — moves it to Approved."""
	doc = frappe.get_doc("Diagnostic Report", name)
	doc.db_set("status", "Approved")
	if conclusion is not None and "conclusion" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("conclusion", conclusion)
	doc.add_comment("Comment", text=f"<b>Verified & Released</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")
	return {"ok": True, "name": name, "status": "Approved"}


@frappe.whitelist()
def amend_report(name: str, reason: str) -> dict:
	"""Send a verified report back for amendment — Pending Review."""
	doc = frappe.get_doc("Diagnostic Report", name)
	doc.db_set("status", "Pending Review")
	doc.add_comment("Comment", text=f"<b>Amendment Requested</b><br>{frappe.utils.escape_html(reason)}")
	return {"ok": True, "name": name, "status": "Pending Review"}


# -- Peer Review -----------------------------------------------------------

@frappe.whitelist()
def peer_review_list(status: str | None = None, mine: int = 0, limit: int = 100) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Open", "In Review", "Discussion"]]
	if int(mine or 0):
		filters["assigned_reviewer"] = frappe.session.user
	return frappe.get_all(
		"Peer Review Case",
		fields=[
			"name", "subject_report", "patient", "patient_name", "section", "modality",
			"priority", "original_reporter", "assigned_reviewer", "due_date",
			"status", "outcome", "submitted_at",
		],
		filters=filters,
		order_by="due_date asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def submit_peer_review(
	name: str,
	outcome: str = "Agree",
	review_notes: str = "",
	discrepancy_severity: str | None = None,
	concurrence: float | None = None,
) -> dict:
	doc = frappe.get_doc("Peer Review Case", name)
	doc.outcome = outcome
	if review_notes:
		doc.review_notes = review_notes
	if discrepancy_severity:
		doc.discrepancy_severity = discrepancy_severity
	if concurrence is not None:
		doc.concurrence = float(concurrence)
	doc.status = "Closed"
	doc.completed_at = now_datetime()
	doc.save(ignore_permissions=False)
	return {"ok": True, "name": name, "status": "Closed", "outcome": outcome}
