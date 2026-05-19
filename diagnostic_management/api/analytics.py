"""Analytics page endpoints — counts, trends, mix breakdowns."""

from datetime import datetime, timedelta

import frappe


def _count(dt: str, filters: dict | None = None) -> int:
	try:
		return frappe.db.count(dt, filters or {})
	except Exception:
		return 0


@frappe.whitelist()
def kpis(days: int = 7) -> dict:
	"""Volume / quality KPIs for the analytics dashboard."""
	end = datetime.now()
	start = end - timedelta(days=int(days))
	return {
		"orders": _count("Service Request", {"creation": [">=", start]}),
		"samples": _count("Sample Collection", {"creation": [">=", start]}),
		"reports_completed": _count("Diagnostic Report", {"status": ["in", ["Approved", "Partially Approved"]], "modified": [">=", start]}),
		"critical_results": _count("Diagnostic Report", {"is_critical": 1, "creation": [">=", start]}),
		"pre_auth_approved": _count("Radiology Pre-Auth", {"status": "Approved", "decision_date": [">=", start]}),
		"qc_failed": _count("QC Run", {"result": "Fail", "run_datetime": [">=", start]}),
	}


@frappe.whitelist()
def volume_trend(days: int = 14) -> list[dict]:
	"""Per-day order/sample/report counts for the trend chart."""
	out = []
	now = datetime.now().date()
	for i in range(int(days) - 1, -1, -1):
		day = now - timedelta(days=i)
		next_day = day + timedelta(days=1)
		out.append({
			"date": day.isoformat(),
			"orders": _count("Service Request", {"creation": ["between", [day, next_day]]}),
			"samples": _count("Sample Collection", {"creation": ["between", [day, next_day]]}),
			"reports": _count("Diagnostic Report", {"creation": ["between", [day, next_day]]}),
		})
	return out


@frappe.whitelist()
def section_mix(days: int = 30) -> list[dict]:
	"""Sample counts grouped by lab section (from Lab Instrument heuristic)."""
	start = datetime.now() - timedelta(days=int(days))
	try:
		rows = frappe.db.sql(
			"""
			SELECT lt.lab_test_group AS section, COUNT(*) AS cnt
			FROM `tabLab Test` t
			LEFT JOIN `tabLab Test Template` lt ON lt.name = t.template
			WHERE t.creation >= %s
			GROUP BY lt.lab_test_group
			ORDER BY cnt DESC
			""",
			(start,),
			as_dict=True,
		)
		return [{"section": (r["section"] or "Unspecified"), "count": int(r["cnt"])} for r in (rows or [])]
	except Exception:
		return []
