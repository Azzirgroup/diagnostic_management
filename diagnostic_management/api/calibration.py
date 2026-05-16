"""Calibration Run endpoints."""

from datetime import timedelta

import frappe
from frappe.utils import getdate, today


@frappe.whitelist()
def list_runs(
	status: str | None = None,
	instrument: str | None = None,
	limit: int = 100,
) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	if instrument:
		filters["instrument"] = instrument
	return frappe.get_all(
		"Calibration Run",
		fields=[
			"name", "instrument", "calibration_type", "scheduled_date",
			"performed_date", "performed_by", "next_due", "analyte",
			"calibrator_lot", "result", "status",
		],
		filters=filters,
		order_by="performed_date desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def due_soon(days: int = 14, limit: int = 100) -> list[dict]:
	end = getdate(today()) + timedelta(days=int(days))
	return frappe.get_all(
		"Calibration Run",
		fields=["name", "instrument", "analyte", "next_due", "calibration_type", "status"],
		filters={"next_due": ["between", [today(), end]]},
		order_by="next_due asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def log(
	instrument: str,
	calibration_type: str = "Routine",
	result: str = "Pass",
	analyte: str | None = None,
	calibrator_lot: str | None = None,
	calibrator_expiry: str | None = None,
	findings: str | None = None,
	corrective_action: str | None = None,
) -> dict:
	doc = frappe.get_doc({
		"doctype": "Calibration Run",
		"instrument": instrument,
		"calibration_type": calibration_type,
		"performed_date": today(),
		"performed_by": frappe.session.user,
		"analyte": analyte,
		"calibrator_lot": calibrator_lot,
		"calibrator_expiry": calibrator_expiry,
		"result": result,
		"status": "Completed",
		"findings": findings,
		"corrective_action": corrective_action,
	}).insert(ignore_permissions=False)
	# Push last_maintenance on the instrument so the Hub reflects the run.
	try:
		frappe.db.set_value("Lab Instrument", instrument, "last_maintenance", today())
	except Exception:
		pass
	return {"ok": True, "name": doc.name, "next_due": doc.next_due}
