from datetime import datetime, timedelta

import frappe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_count(doctype: str, filters: dict | None = None) -> int:
	"""Counts but returns 0 if the doctype isn't installed yet — keeps the
	SPA running even when optional Marley/Healthcare doctypes are absent."""
	try:
		return frappe.db.count(doctype, filters or {})
	except Exception:
		return 0


def _has_field(doctype: str, fieldname: str) -> bool:
	try:
		if not frappe.db.exists("DocType", doctype):
			return False
		return any(df.fieldname == fieldname for df in frappe.get_meta(doctype).fields)
	except Exception:
		return False


# ---------------------------------------------------------------------------
# Lab Manager dashboard KPIs
# ---------------------------------------------------------------------------

@frappe.whitelist()
def lab_manager() -> dict:
	today = datetime.now().date()
	yesterday = today - timedelta(days=1)

	pending_today = _safe_count(
		"Sample Collection",
		{"status": ["in", ["Pending", "Partly Collected", "Collected"]], "collected_time": [">=", today]},
	)
	pending_yest = _safe_count(
		"Sample Collection",
		{"status": ["in", ["Pending", "Partly Collected", "Collected"]], "collected_time": ["between", [yesterday, today]]},
	)

	critical_today = (
		_safe_count("Diagnostic Report", {"creation": [">=", today], "is_critical": 1})
		if _has_field("Diagnostic Report", "is_critical")
		else 0
	)

	# Reagent low-stock: Items with a reorder rule. Best-effort.
	low_stock = 0
	try:
		row = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabItem` i
			WHERE i.is_stock_item = 1 AND i.disabled = 0
			  AND EXISTS (SELECT 1 FROM `tabItem Reorder` r WHERE r.parent = i.name)
			""",
		)
		low_stock = (row and row[0][0]) or 0
	except Exception:
		low_stock = 0

	return {
		"pending_samples": pending_today,
		"pending_delta": pending_today - pending_yest,
		# Live TAT computation is roadmap; report 0 instead of a placeholder.
		"avg_tat_minutes": 0,
		"critical_results": critical_today,
		"reagent_alerts": low_stock,
	}


@frappe.whitelist()
def workflow_overview() -> dict:
	"""Counts of samples by workflow stage for the Sample Workflow Overview card.

	Each stage maps to the Sample Collection status (when available). Falls back
	to zeros when the doctype isn't installed.
	"""
	# Map workflow stages to actual Sample Collection / Lab Test status values.
	# Sample Collection options:  Pending / Partly Collected / Collected
	# Lab Test options:           Draft / Completed / Approved / Rejected / Cancelled
	stage_map = {
		"collected": ["Collected"],
		"in_processing": ["Partly Collected"],
		"in_analysis": ["Pending"],
		"result_ready": [],
		"completed": [],
	}
	out: dict[str, int] = {}
	for key, statuses in stage_map.items():
		out[key] = _safe_count("Sample Collection", {"status": ["in", statuses]})
	return out


@frappe.whitelist()
def alerts() -> list[dict]:
	"""Non-fatal operational alerts shown on the lab manager dashboard.

	Each item: {key, title, sub, count, tone}.
	Counts are computed on demand and clipped to zero if a query fails.
	"""
	today = datetime.now().date()
	expiry_cutoff = today + timedelta(days=30)

	# Low stock reagents (items with a reorder rule).
	low_stock = 0
	try:
		row = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabItem` i
			WHERE i.is_stock_item = 1 AND i.disabled = 0
			  AND EXISTS (SELECT 1 FROM `tabItem Reorder` r WHERE r.parent = i.name)
			""",
		)
		low_stock = (row and row[0][0]) or 0
	except Exception:
		low_stock = 0

	# Reports awaiting verification for > 24h.
	overdue_cutoff = datetime.now() - timedelta(hours=24)
	overdue = _safe_count(
		"Diagnostic Report",
		{"status": ["in", ["Open", "Pending Review", "Partially Approved"]], "modified": ["<=", overdue_cutoff]},
	)

	# Expiring stock (Batch.expiry_date within 30 days). Best-effort.
	expiring = 0
	try:
		row = frappe.db.sql(
			"""
			SELECT COUNT(*) FROM `tabBatch`
			WHERE expiry_date BETWEEN %s AND %s
			""",
			(today, expiry_cutoff),
		)
		expiring = (row and row[0][0]) or 0
	except Exception:
		expiring = 0

	return [
		{"key": "low_stock", "title": "Low Stock Reagents", "sub": "Items below reorder level", "count": low_stock, "tone": "warning"},
		{"key": "overdue", "title": "Overdue Verifications", "sub": "Results pending verification > 24h", "count": overdue, "tone": "danger"},
		{"key": "expiring", "title": "Reagents Expiring Soon", "sub": "Items expiring within 30 days", "count": expiring, "tone": "neutral"},
	]


@frappe.whitelist()
def analyzers() -> list[dict]:
	"""Lab instruments / analyzers.

	Prefers the app-owned `Lab Instrument` doctype when present; falls back
	to `Asset` rows so the Home page keeps rendering on bare installs.
	"""
	try:
		if frappe.db.exists("DocType", "Lab Instrument"):
			rows = frappe.get_all(
				"Lab Instrument",
				fields=["name", "instrument_name", "section", "state", "last_heartbeat"],
				order_by="state, instrument_name",
				limit_page_length=12,
			)
			return [
				{
					"name": r.get("instrument_name") or r["name"],
					"status": r.get("state") or "Unknown",
					"section": r.get("section"),
					"last_heartbeat": r.get("last_heartbeat"),
				}
				for r in (rows or [])
			]
	except Exception:
		pass
	try:
		rows = frappe.db.sql(
			"""
			SELECT a.name, a.asset_name, a.status
			FROM `tabAsset` a
			WHERE a.docstatus < 2
			ORDER BY a.asset_name
			LIMIT 8
			""",
			as_dict=True,
		)
		return [{"name": r.asset_name or r.name, "status": r.status or "Unknown"} for r in (rows or [])]
	except Exception:
		return []


@frappe.whitelist()
def branch_performance() -> dict:
	"""Branch performance summary for today. Defaults to zeros when the
	underlying doctypes / fields aren't populated yet."""
	today = datetime.now().date()
	samples_processed = _safe_count(
		"Sample Collection",
		{"collected_time": [">=", today]},
	)
	reports_released = _safe_count(
		"Diagnostic Report",
		{"creation": [">=", today], "status": ["in", ["Approved", "Partially Approved"]]},
	)
	rejected = _safe_count(
		"Sample Collection",
		{"collected_time": [">=", today], "received_condition": ["not in", ["", "Acceptable"]]},
	) if _has_field("Sample Collection", "received_condition") else 0

	rejection_rate = round((rejected / samples_processed) * 100, 1) if samples_processed else 0.0

	return {
		"samples_processed": samples_processed,
		"reports_released": reports_released,
		"avg_tat_minutes": 0,
		"rejection_rate_pct": rejection_rate,
	}


# ---------------------------------------------------------------------------
# Doctor portal KPIs
# ---------------------------------------------------------------------------

@frappe.whitelist()
def doctor() -> dict:
	"""KPIs scoped to the logged-in referring doctor.

	Resolves the Healthcare Practitioner linked to the current User and
	filters orders/results to those that name them as referring/ordering
	practitioner.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw("Not logged in", frappe.AuthenticationError)

	practitioner = frappe.db.get_value("Healthcare Practitioner", {"user_id": user}, "name")

	if not practitioner:
		# Fall back to global counts; the SPA will degrade gracefully.
		return {
			"pending_results": _safe_count("Diagnostic Report", {"status": ["in", ["Open", "Pending Review", "Partially Approved"]]}),
			"recent_patients": _safe_count("Patient", {}),
			"new_orders": _safe_count("Service Request", {"status": "active-Request Status"}),
			"unpaid_amount": 0,
		}

	pending_results = _safe_count(
		"Diagnostic Report",
		{"practitioner": practitioner, "status": ["in", ["Open", "Pending Review", "Partially Approved"]]},
	)
	new_orders = _safe_count(
		"Service Request",
		{"practitioner": practitioner, "status": "active-Request Status"},
	)

	# Distinct patient count from Service Requests this practitioner ordered
	# (last 90 days), capped to keep query cheap.
	cutoff = (datetime.now() - timedelta(days=90)).date()
	try:
		row = frappe.db.sql(
			"""
			SELECT COUNT(DISTINCT patient) FROM `tabService Request`
			WHERE practitioner=%s AND creation >= %s
			""",
			(practitioner, cutoff),
		)
		recent = (row and row[0][0]) or 0
	except Exception:
		recent = 0

	# Unpaid invoice total addressed to this practitioner (commission/statements view)
	unpaid = 0
	try:
		row = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(outstanding_amount), 0) FROM `tabSales Invoice`
			WHERE ref_practitioner=%s AND outstanding_amount > 0
			""",
			(practitioner,),
		)
		unpaid = (row and row[0][0]) or 0
	except Exception:
		unpaid = 0

	return {
		"pending_results": pending_results,
		"recent_patients": recent,
		"new_orders": new_orders,
		"unpaid_amount": float(unpaid),
	}
