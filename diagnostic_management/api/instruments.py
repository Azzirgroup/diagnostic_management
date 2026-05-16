"""Lab Instrument / Analyzer Monitor endpoints."""

from datetime import datetime, timedelta

import frappe


@frappe.whitelist()
def list_instruments(section: str | None = None, state: str | None = None, limit: int = 100) -> list[dict]:
	filters: dict = {}
	if section:
		filters["section"] = section
	if state:
		filters["state"] = state
	return frappe.get_all(
		"Lab Instrument",
		fields=[
			"name", "instrument_name", "manufacturer", "model", "section",
			"location", "interface_type", "state", "last_heartbeat",
			"last_maintenance", "serial_number",
		],
		filters=filters,
		order_by="section, instrument_name",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def monitor() -> list[dict]:
	"""Compact analyzer status feed for the Analyzer Monitor page."""
	rows = frappe.get_all(
		"Lab Instrument",
		fields=[
			"name", "instrument_name", "section", "state", "last_heartbeat",
			"interface_type", "host", "port",
		],
		order_by="state, instrument_name",
		limit_page_length=200,
	)
	now = datetime.now()
	for r in rows:
		hb = r.get("last_heartbeat")
		r["stale"] = bool(hb and (now - hb) > timedelta(minutes=10))
	return rows


@frappe.whitelist()
def set_state(instrument: str, state: str, note: str = "") -> dict:
	doc = frappe.get_doc("Lab Instrument", instrument)
	doc.db_set("state", state)
	if note:
		doc.add_comment("Comment", text=f"<b>State changed</b> → {frappe.utils.escape_html(state)}<br>{frappe.utils.escape_html(note)}")
	return {"ok": True, "instrument": instrument, "state": state}


@frappe.whitelist()
def heartbeat(instrument: str) -> dict:
	"""External adapter posts heartbeat — keeps last_heartbeat fresh."""
	doc = frappe.get_doc("Lab Instrument", instrument)
	doc.db_set("last_heartbeat", frappe.utils.now_datetime())
	if doc.state == "Offline":
		doc.db_set("state", "Operational")
	return {"ok": True, "instrument": instrument}
