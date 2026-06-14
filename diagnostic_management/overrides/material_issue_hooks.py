"""Consumable issue pipeline — direct Material Issue, no Work Order chain.

When a Sample Collection transitions to "Tested", we used to spin up a Work
Order per stock item, auto-complete its Job Cards, then submit a Manufacture
Stock Entry. That's ERPNext-correct for actual manufacturing but heavy for a
lab: a CBC doesn't "produce" anything — it just *issues* a few consumables out
of the reagent warehouse.

New flow (this module):
  1. From a sample, collect unique Sales Invoices via its Lab Tests.
  2. For each SI item that's a stock item with an active default BOM, expand
     the BOM into its raw-material rows × invoice qty → required consumption.
  3. Check stock in the configured source warehouse for each item:
       - shortfall → log a `ADMS Stock Alert` (Open / severity by gap)
       - also emit `frappe.publish_realtime('adms:stock_alert', ...)` so any
         logged-in Desk session pops a toast, and log a Notification Log
         entry for the Lab Manager bell.
  4. Build ONE Material Issue Stock Entry per SI with all consumable rows
     (s_warehouse set, no t_warehouse → pure issue), tag it with
     `custom_sales_invoice` + `custom_sample_collection`, submit it.

Stock shortage does NOT block the issue — the lab needs to record consumption
even when stock is short; the alert is the call-to-action for restock. We do
flip `Stock Settings.allow_negative_stock=1` for the submit window so the SLE
validation accepts negative quantities, then flip it back.
"""
from __future__ import annotations

import frappe
from frappe.utils import flt, now_datetime, today


def create_material_issues_from_sample_by_name(sample_name: str) -> None:
	"""Background-queue entry point — load doc and process."""
	sample_doc = frappe.get_doc("Sample Collection", sample_name)
	create_material_issues_from_sample(sample_doc)


def create_material_issues_from_sample(sample_doc) -> None:
	"""Called when a Sample Collection transitions to 'Tested'.

	Walks every Lab Test linked to this sample, collects each unique Sales
	Invoice, and creates a Material Issue stock entry per SI consuming the
	BOM raw materials of each stock-item-with-BOM on that invoice.
	"""
	lab_tests = frappe.get_all("Lab Test", filters={"sample": sample_doc.name}, pluck="name")
	if not lab_tests:
		return

	sales_invoices: set[str] = set()
	for lt_name in lab_tests:
		si = frappe.db.get_value("Lab Test", lt_name, "custom_sales_invoice")
		if si:
			sales_invoices.add(si)

	for si_name in sales_invoices:
		try:
			_process_sales_invoice_material_issue(si_name, sample_doc.name)
		except Exception as e:
			frappe.log_error(
				f"Material Issue creation failed for Sales Invoice {si_name}: {str(e)}",
				"Material Issue Auto-Creation",
			)


def _process_sales_invoice_material_issue(si_name: str, sample_name: str) -> str | None:
	"""Expand SI items → BOM → consumption rows, check stock, create Material Issue."""
	# Idempotency — only one Material Issue per (SI, sample).
	already = frappe.db.exists(
		"Stock Entry",
		{
			"stock_entry_type": "Material Issue",
			"custom_sales_invoice": si_name,
			"custom_sample_collection": sample_name,
			"docstatus": ["!=", 2],
		},
	)
	if already:
		return None

	si = frappe.get_doc("Sales Invoice", si_name)
	abbr = frappe.db.get_value("Company", si.company, "abbr") or ""
	default_warehouse = (
		frappe.db.get_value("Warehouse", {"company": si.company, "warehouse_name": "Stores"}, "name")
		or f"Stores - {abbr}"
	)

	# Aggregate {item_code: {qty, warehouse, uom, available, source_si_item}}
	rows: dict[tuple[str, str], dict] = {}

	for si_row in si.items:
		if not si_row.item_code:
			continue

		# Only stock items can be issued from a warehouse.
		if not frappe.db.get_value("Item", si_row.item_code, "is_stock_item"):
			continue

		bom_name = frappe.db.get_value(
			"BOM",
			{"item": si_row.item_code, "is_default": 1, "is_active": 1, "docstatus": 1},
			"name",
		)
		if not bom_name:
			continue

		bom = frappe.get_doc("BOM", bom_name)
		# BOM qty represents the "batch size" the BOM was costed against.
		# When a real invoice asks for `si_row.qty` of the finished item, each
		# raw row scales by si_row.qty / bom.quantity.
		scale = flt(si_row.qty) / flt(bom.quantity or 1)

		for raw in bom.items:
			required = flt(raw.qty) * scale
			if required <= 0:
				continue
			source = si_row.warehouse or raw.source_warehouse or default_warehouse
			key = (raw.item_code, source)
			if key not in rows:
				rows[key] = {
					"item_code": raw.item_code,
					"qty": 0.0,
					"warehouse": source,
					"uom": raw.stock_uom or raw.uom,
				}
			rows[key]["qty"] += required

	if not rows:
		return None

	# Stock check + alerts.
	patient = si.get("patient")
	patient_name = si.get("patient_name") or si.get("customer_name")
	alerts: list[str] = []
	for (item_code, warehouse), info in rows.items():
		available = flt(
			frappe.db.get_value("Bin", {"item_code": item_code, "warehouse": warehouse}, "actual_qty")
			or 0
		)
		info["available"] = available
		shortage = flt(info["qty"]) - available
		if shortage > 0:
			alert_name = _raise_stock_alert(
				item_code=item_code,
				warehouse=warehouse,
				required=info["qty"],
				available=available,
				shortage=shortage,
				stock_uom=info["uom"],
				sales_invoice=si_name,
				sample_collection=sample_name,
				patient=patient,
				patient_name=patient_name,
			)
			alerts.append(alert_name)

	se_name = _create_material_issue(rows, si_name, sample_name, si.company)

	# Back-link the SE onto each alert so the frontend can jump to the issue.
	for a in alerts:
		try:
			frappe.db.set_value("ADMS Stock Alert", a, "stock_entry", se_name)
		except Exception:
			pass

	return se_name


def _create_material_issue(rows: dict, si_name: str, sample_name: str, company: str) -> str:
	"""Build + submit the Material Issue Stock Entry."""
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = "Material Issue"
	se.purpose = "Material Issue"
	se.company = company
	se.posting_date = today()
	se.posting_time = frappe.utils.nowtime()
	se.custom_sales_invoice = si_name
	se.custom_sample_collection = sample_name

	for (item_code, warehouse), info in rows.items():
		row = {
			"item_code": item_code,
			"qty": flt(info["qty"]),
			"s_warehouse": warehouse,
			"uom": info["uom"],
			"stock_uom": info["uom"],
		}
		se.append("items", row)

	# Many items have no purchase receipts in a fresh install — allow zero
	# valuation rate so the SE still submits.
	for row in se.items:
		if not row.get("basic_rate") and not row.get("valuation_rate"):
			row.allow_zero_valuation_rate = 1

	se.flags.ignore_permissions = True

	stock_settings = frappe.get_single("Stock Settings")
	original_allow_negative = stock_settings.allow_negative_stock
	if not original_allow_negative:
		frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 1)
		frappe.clear_document_cache("Stock Settings", "Stock Settings")
	try:
		se.insert()
		se.submit()
	finally:
		if not original_allow_negative:
			frappe.db.set_single_value("Stock Settings", "allow_negative_stock", 0)
			frappe.clear_document_cache("Stock Settings", "Stock Settings")
	frappe.db.commit()

	frappe.logger().info(
		f"Material Issue {se.name} submitted for SI={si_name} sample={sample_name} ({len(se.items)} rows)"
	)
	return se.name


def _raise_stock_alert(*, item_code, warehouse, required, available, shortage, stock_uom,
                       sales_invoice, sample_collection, patient, patient_name) -> str:
	"""Persist an ADMS Stock Alert + Notification Log + realtime ping."""
	# Severity ramps with the shortfall ratio.
	ratio = (shortage / required) if required else 1.0
	if available <= 0:                            severity = "Critical"
	elif ratio >= 0.5:                            severity = "High"
	elif ratio >= 0.2:                            severity = "Medium"
	else:                                         severity = "Low"

	item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
	warehouse_label = warehouse or "(unset warehouse)"
	msg = (
		f"Stock shortage: {item_name} ({item_code}) in {warehouse_label}. "
		f"Required {required:g}, available {available:g} (short {shortage:g})."
	)

	alert = frappe.get_doc({
		"doctype": "ADMS Stock Alert",
		"alert_date": now_datetime(),
		"status": "Open",
		"severity": severity,
		"item_code": item_code,
		"item_name": item_name,
		"warehouse": warehouse,
		"required_qty": required,
		"available_qty": available,
		"shortage_qty": shortage,
		"stock_uom": stock_uom,
		"sales_invoice": sales_invoice,
		"sample_collection": sample_collection,
		"patient": patient,
		"patient_name": patient_name,
		"message": msg,
	})
	alert.flags.ignore_permissions = True
	alert.insert()

	# ERPNext bell — drop into the Lab Manager's notification bar.
	try:
		recipients = frappe.get_all(
			"Has Role",
			filters={"role": ["in", ["Lab Manager", "Billing Officer", "Diagnostic Director"]], "parenttype": "User"},
			pluck="parent",
		)
		for user in set(recipients):
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"Lab stock alert — {item_name}",
				"email_content": msg,
				"for_user": user,
				"type": "Alert",
				"document_type": "ADMS Stock Alert",
				"document_name": alert.name,
			}).insert(ignore_permissions=True)
	except Exception:
		pass  # Notification Log isn't load-bearing — never let it abort the issue.

	# Realtime ping for any open Desk session.
	try:
		frappe.publish_realtime(
			event="adms:stock_alert",
			message={
				"name": alert.name, "item_code": item_code, "item_name": item_name,
				"warehouse": warehouse, "shortage": shortage, "severity": severity,
				"sales_invoice": sales_invoice, "sample_collection": sample_collection,
			},
			user="*", after_commit=True,
		)
	except Exception:
		pass

	return alert.name
