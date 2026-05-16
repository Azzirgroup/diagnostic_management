"""Audit & Compliance read endpoints — reuses Frappe Activity / Comments."""

from datetime import datetime, timedelta

import frappe


@frappe.whitelist()
def activity(days: int = 7, limit: int = 200, doctype: str | None = None) -> list[dict]:
	"""Recent activity log entries."""
	start = datetime.now() - timedelta(days=int(days))
	filters: dict = {"creation": [">=", start]}
	if doctype:
		filters["reference_doctype"] = doctype
	try:
		return frappe.get_all(
			"Activity Log",
			fields=["name", "subject", "user", "operation", "reference_doctype", "reference_name", "creation"],
			filters=filters,
			order_by="creation desc",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def critical_audit(days: int = 30, limit: int = 100) -> list[dict]:
	"""Critical-result trail — combines flagged reports with their acknowledgements."""
	start = datetime.now() - timedelta(days=int(days))
	try:
		return frappe.get_all(
			"Diagnostic Report",
			fields=[
				"name", "patient", "patient_name", "status", "is_critical",
				"critical_acknowledged", "critical_acknowledged_at", "modified",
			],
			filters={"is_critical": 1, "modified": [">=", start]},
			order_by="modified desc",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def rejection_log(days: int = 30, limit: int = 100) -> list[dict]:
	"""Sample rejections — the rejection custom fields are the source of truth."""
	start = datetime.now() - timedelta(days=int(days))
	try:
		return frappe.get_all(
			"Sample Collection",
			fields=[
				"name", "patient", "patient_name", "sample", "status",
				"received_condition", "rejection_reason_text", "modified",
			],
			filters={"status": "Rejected", "modified": [">=", start]},
			order_by="modified desc",
			limit_page_length=int(limit),
		)
	except Exception:
		return []
