"""Doctor portal endpoints — scoped to the logged-in referring practitioner."""

from datetime import datetime, timedelta

import frappe


def _practitioner() -> str | None:
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)
	return frappe.db.get_value("Healthcare Practitioner", {"user_id": user}, "name")


@frappe.whitelist()
def results_inbox(status: str | None = None, limit: int = 100) -> list[dict]:
	"""Reports addressed to the logged-in practitioner."""
	pr = _practitioner()
	filters: dict = {}
	if pr:
		filters["practitioner"] = pr
	if status:
		filters["status"] = status
	return frappe.get_all(
		"Diagnostic Report",
		fields=[
			"name", "docname", "patient", "patient_name", "status",
			"is_critical", "critical_acknowledged", "creation", "modified",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def my_patients(limit: int = 100) -> list[dict]:
	"""Distinct patients this practitioner has ordered for in the last 180 days."""
	pr = _practitioner()
	if not pr:
		return []
	cutoff = datetime.now() - timedelta(days=180)
	try:
		rows = frappe.db.sql(
			"""
			SELECT DISTINCT p.name, p.patient_name, p.sex, p.dob, p.mobile, p.email, p.status
			FROM `tabPatient` p
			JOIN `tabService Request` sr ON sr.patient = p.name
			WHERE sr.practitioner = %s AND sr.creation >= %s
			ORDER BY p.patient_name
			LIMIT %s
			""",
			(pr, cutoff, int(limit)),
			as_dict=True,
		)
		return rows or []
	except Exception:
		return []


@frappe.whitelist()
def my_orders(limit: int = 100) -> list[dict]:
	"""Orders this practitioner created (or whose practitioner field references them)."""
	pr = _practitioner()
	filters: dict = {}
	if pr:
		filters["practitioner"] = pr
	else:
		filters["owner"] = frappe.session.user
	return frappe.get_all(
		"Service Request",
		fields=[
			"name", "patient", "patient_name", "priority", "title",
			"template_dt", "template_dn", "status", "occurrence_date", "creation",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def statements(status: str | None = None, limit: int = 50) -> list[dict]:
	"""Commission / statement records for the doctor portal Statements page."""
	pr = _practitioner()
	filters: dict = {}
	if pr:
		filters["practitioner"] = pr
	if status:
		filters["status"] = status
	try:
		return frappe.get_all(
			"Doctor Statement",
			fields=[
				"name", "period_start", "period_end", "issued_date",
				"referral_count", "total_billed", "commission_pct",
				"commission_amount", "net_payable", "status", "paid_date",
			],
			filters=filters,
			order_by="period_end desc",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def critical_to_ack(limit: int = 50) -> list[dict]:
	"""Critical reports addressed to this doctor that still need acknowledgement."""
	pr = _practitioner()
	filters: dict = {"is_critical": 1, "critical_acknowledged": 0}
	if pr:
		filters["practitioner"] = pr
	return frappe.get_all(
		"Diagnostic Report",
		fields=[
			"name", "docname", "patient", "patient_name", "status", "creation",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)
