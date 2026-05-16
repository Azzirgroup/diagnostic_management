"""Billing & invoicing endpoints."""

import frappe


@frappe.whitelist()
def queue(status: str | None = None, limit: int = 100) -> list[dict]:
	"""Active billing queue. Defaults to all open (Draft / unpaid)."""
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Draft", "Overdue", "Unpaid", "Partly Paid", "Submitted"]]
	return frappe.get_all(
		"Sales Invoice",
		fields=[
			"name", "customer", "customer_name", "grand_total", "outstanding_amount",
			"status", "posting_date", "due_date", "currency",
		],
		filters=filters,
		order_by="posting_date desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def for_patient(patient: str, limit: int = 50) -> list[dict]:
	fields = [
		"name", "customer", "customer_name", "grand_total", "outstanding_amount",
		"status", "posting_date", "due_date",
	]
	try:
		meta = frappe.get_meta("Sales Invoice")
		if any(df.fieldname == "patient" for df in meta.fields):
			return frappe.get_all(
				"Sales Invoice",
				fields=fields,
				filters={"patient": patient},
				order_by="posting_date desc",
				limit_page_length=int(limit),
			)
	except Exception:
		pass
	# Fallback: match by patient_name → customer_name
	patient_name = frappe.db.get_value("Patient", patient, "patient_name") or ""
	if not patient_name:
		return []
	return frappe.get_all(
		"Sales Invoice",
		fields=fields,
		filters={"customer_name": ["like", f"%{patient_name}%"]},
		order_by="posting_date desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def summary() -> dict:
	"""Quick KPIs for the billing dashboard card."""
	def _agg(filters: dict) -> dict:
		try:
			rows = frappe.db.sql(
				"""
				SELECT COUNT(*) AS cnt, COALESCE(SUM(outstanding_amount),0) AS total
				FROM `tabSales Invoice`
				WHERE status IN %(statuses)s
				""",
				{"statuses": tuple(filters["statuses"])},
				as_dict=True,
			)
			r = rows[0] if rows else {}
			return {"count": int(r.get("cnt") or 0), "total": float(r.get("total") or 0)}
		except Exception:
			return {"count": 0, "total": 0}
	return {
		"draft": _agg({"statuses": ["Draft"]}),
		"unpaid": _agg({"statuses": ["Unpaid", "Partly Paid", "Overdue"]}),
		"paid": _agg({"statuses": ["Paid"]}),
	}
