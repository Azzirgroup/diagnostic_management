"""Reagent inventory endpoints (Reagent Lot + Item rollup)."""

from datetime import timedelta

import frappe
from frappe.utils import getdate, today


@frappe.whitelist()
def list_lots(status: str | None = None, section: str | None = None, limit: int = 100) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	if section:
		filters["section"] = section
	return frappe.get_all(
		"Reagent Lot",
		fields=[
			"name", "reagent_item", "lot_number", "section", "manufacturer",
			"received_date", "expiry_date", "quantity_received", "quantity_on_hand",
			"unit", "status", "storage_location", "instrument", "qc_passed",
		],
		filters=filters,
		order_by="expiry_date asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def low_stock(threshold_pct: float = 20.0, limit: int = 100) -> list[dict]:
	"""Lots whose on-hand quantity is at or below threshold_pct of received."""
	rows = frappe.get_all(
		"Reagent Lot",
		fields=[
			"name", "reagent_item", "lot_number", "section", "quantity_on_hand",
			"quantity_received", "unit", "status",
		],
		filters={"status": ["!=", "Depleted"]},
		limit_page_length=int(limit) * 2,
	)
	cutoff = float(threshold_pct) / 100.0
	out = []
	for r in rows:
		recv = r.get("quantity_received") or 0
		hand = r.get("quantity_on_hand") or 0
		if recv > 0 and hand <= recv * cutoff:
			out.append(r)
	return out[: int(limit)]


@frappe.whitelist()
def expiring_soon(days: int = 30, limit: int = 100) -> list[dict]:
	end = getdate(today()) + timedelta(days=int(days))
	return frappe.get_all(
		"Reagent Lot",
		fields=[
			"name", "reagent_item", "lot_number", "expiry_date", "section",
			"quantity_on_hand", "status",
		],
		filters={
			"expiry_date": ["between", [today(), end]],
			"status": ["!=", "Depleted"],
		},
		order_by="expiry_date asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def add_lot(
	reagent_item: str,
	lot_number: str,
	section: str | None = None,
	manufacturer: str | None = None,
	received_date: str | None = None,
	expiry_date: str | None = None,
	quantity_received: float = 0,
	unit: str = "ml",
	storage_location: str | None = None,
	instrument: str | None = None,
) -> dict:
	doc = frappe.get_doc({
		"doctype": "Reagent Lot",
		"reagent_item": reagent_item,
		"lot_number": lot_number,
		"section": section,
		"manufacturer": manufacturer,
		"received_date": received_date or today(),
		"expiry_date": expiry_date,
		"quantity_received": quantity_received,
		"quantity_on_hand": quantity_received,
		"unit": unit,
		"storage_location": storage_location,
		"instrument": instrument,
		"status": "Active",
	}).insert(ignore_permissions=False)
	return {"ok": True, "name": doc.name}


@frappe.whitelist()
def log_usage(lot: str, amount: float, notes: str | None = None) -> dict:
	"""Decrement on-hand by `amount`. The before_save hook recomputes status."""
	doc = frappe.get_doc("Reagent Lot", lot)
	doc.quantity_on_hand = max(0.0, (doc.quantity_on_hand or 0) - float(amount))
	doc.save(ignore_permissions=False)
	if notes:
		doc.add_comment("Comment", text=f"<b>Usage Logged</b><br>{frappe.utils.escape_html(notes)}")
	return {"ok": True, "lot": lot, "quantity_on_hand": doc.quantity_on_hand, "status": doc.status}


@frappe.whitelist()
def reagent_items(query: str = "", limit: int = 50) -> list[dict]:
	"""Item catalog (is_stock_item, disabled=0) suitable for reagent linkage."""
	q = (query or "").strip()
	or_filters = [
		["Item", "item_name", "like", f"%{q}%"],
		["Item", "item_code", "like", f"%{q}%"],
	] if q else None
	return frappe.get_all(
		"Item",
		fields=["name", "item_name", "item_code", "description", "stock_uom"],
		filters={"is_stock_item": 1, "disabled": 0},
		or_filters=or_filters,
		limit_page_length=int(limit),
		order_by="item_name",
	)
