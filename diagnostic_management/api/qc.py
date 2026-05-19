"""QC Station endpoints."""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def list_runs(
	status: str | None = None,
	result: str | None = None,
	instrument: str | None = None,
	section: str | None = None,
	limit: int = 100,
) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	if result:
		filters["result"] = result
	if instrument:
		filters["instrument"] = instrument
	if section:
		filters["section"] = section
	return frappe.get_all(
		"QC Run",
		fields=[
			"name", "instrument", "section", "analyte", "control_level", "lot_number",
			"run_datetime", "expected_value", "observed_value", "unit", "sd",
			"z_score", "westgard_flag", "result", "status", "performed_by",
		],
		filters=filters,
		order_by="run_datetime desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def submit_run(
	instrument: str,
	analyte: str,
	control_level: str,
	observed_value: float,
	expected_value: float | None = None,
	sd: float | None = None,
	lot_number: str | None = None,
	unit: str | None = None,
	westgard_flag: str | None = None,
	notes: str | None = None,
) -> dict:
	doc = frappe.get_doc({
		"doctype": "QC Run",
		"instrument": instrument,
		"section": _instrument_section(instrument),
		"analyte": analyte,
		"control_level": control_level,
		"observed_value": float(observed_value),
		"expected_value": float(expected_value) if expected_value is not None else None,
		"sd": float(sd) if sd is not None else None,
		"lot_number": lot_number,
		"unit": unit,
		"westgard_flag": westgard_flag,
		"run_datetime": now_datetime(),
		"performed_by": frappe.session.user,
		"notes": notes,
	}).insert(ignore_permissions=False)
	return {"ok": True, "name": doc.name, "result": doc.result, "z_score": doc.z_score}


@frappe.whitelist()
def approve(name: str, notes: str = "") -> dict:
	doc = frappe.get_doc("QC Run", name)
	doc.db_set("status", "Approved")
	doc.add_comment("Comment", text=f"<b>QC Approved</b><br>By: {frappe.utils.escape_html(frappe.session.user)}" + (f"<br>{frappe.utils.escape_html(notes)}" if notes else ""))
	return {"ok": True, "name": name, "status": "Approved"}


@frappe.whitelist()
def reject(name: str, corrective_action: str = "") -> dict:
	doc = frappe.get_doc("QC Run", name)
	doc.db_set("status", "Rejected")
	if corrective_action:
		doc.db_set("corrective_action", corrective_action)
	doc.add_comment("Comment", text=f"<b>QC Rejected</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")
	return {"ok": True, "name": name, "status": "Rejected"}


def _instrument_section(instrument: str) -> str | None:
	try:
		return frappe.db.get_value("Lab Instrument", instrument, "section")
	except Exception:
		return None
