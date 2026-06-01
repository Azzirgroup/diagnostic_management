"""Work Order auto-creation from a tested Sample Collection.

Ported verbatim from genetest's `overrides/work_order_hooks.py`. Adapted only for
the ADMS data model:
  - genetest "Lab Sample" → Marley **Sample Collection**.
  - Walks Lab Tests linked to the sample via `Lab Test.sample = <sample>` instead
    of a child table on the parent.
  - SI is resolved from `Lab Test.custom_sales_invoice` (stamped by
    billing_workflow when the Sales Invoice is created).

Flow (unchanged from genetest):
  1. From a sample, collect unique Sales Invoices via its Lab Tests.
  2. For each SI item that's a stock item with an active default BOM, aggregate qty.
  3. Create + submit a Work Order (`skip_transfer=1`).
  4. Auto-start + auto-complete every Job Card with a 1-minute time log.
  5. Create + submit a Manufacture stock entry — allowing negative stock temporarily
     so consumables without prior purchase receipts can still be deducted.
"""

import frappe
from frappe.utils import add_to_date, now_datetime, today


def create_work_orders_from_sample_by_name(sample_name: str) -> None:
	"""Background-queue entry point — load doc and process."""
	sample_doc = frappe.get_doc("Sample Collection", sample_name)
	create_work_orders_from_sample(sample_doc)


def create_work_orders_from_sample(sample_doc) -> None:
	"""Called when a Sample Collection transitions to 'Tested'.

	Walks every Lab Test linked to this sample, collects each unique
	Sales Invoice, and creates a Work Order for every invoice item that has an
	active default BOM (genetest's exact pipeline).
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
			_process_sales_invoice_work_orders(si_name)
		except Exception as e:
			frappe.log_error(
				f"Work Order creation failed for Sales Invoice {si_name}: {str(e)}",
				"Work Order Auto-Creation",
			)


def _process_sales_invoice_work_orders(si_name: str) -> None:
	"""Aggregate BOM items from a Sales Invoice and create Work Orders."""
	si = frappe.get_doc("Sales Invoice", si_name)

	# {item_code: {"qty": X, "bom": Y, "source_warehouse": Z}}
	items_to_process: dict[str, dict] = {}

	for row in si.items:
		if not row.item_code:
			continue

		# Only create Work Orders for stock items — non-stock items cannot
		# have Manufacture stock entries so the WO would never complete.
		is_stock_item = frappe.db.get_value("Item", row.item_code, "is_stock_item")
		if not is_stock_item:
			continue

		# Check if item has an active default BOM
		bom_name = frappe.db.get_value(
			"BOM",
			{"item": row.item_code, "is_default": 1, "is_active": 1, "docstatus": 1},
			"name",
		)
		if not bom_name:
			continue

		# Skip if a Work Order was already created for this SI + item
		existing_wo = frappe.db.exists(
			"Work Order",
			{
				"production_item": row.item_code,
				"sales_order": ["is", "not set"],
				"status": ["not in", ["Stopped", "Cancelled"]],
				"custom_sales_invoice": si_name,
			},
		)
		if existing_wo:
			continue

		if row.item_code not in items_to_process:
			items_to_process[row.item_code] = {
				"qty": 0,
				"bom": bom_name,
				"source_warehouse": row.warehouse or "",
			}
		items_to_process[row.item_code]["qty"] += row.qty

	for item_code, info in items_to_process.items():
		try:
			_create_and_complete_work_order(
				item_code=item_code,
				qty=info["qty"],
				bom_name=info["bom"],
				source_warehouse=info["source_warehouse"],
				company=si.company,
				si_name=si_name,
			)
		except Exception as e:
			frappe.log_error(
				f"Failed to create Work Order for {item_code} (SI: {si_name}): {str(e)}",
				"Work Order Auto-Creation",
			)


def _create_and_complete_work_order(item_code, qty, bom_name, source_warehouse, company, si_name) -> None:
	"""Create, submit, complete Job Cards, and finish a Work Order."""
	abbr = frappe.db.get_value("Company", company, "abbr") or ""

	# Resolve FG and WIP warehouses by name match, fall back to standard names
	fg_warehouse = (
		frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Finished Goods"}, "name")
		or f"Finished Goods - {abbr}"
	)
	wip_warehouse = (
		frappe.db.get_value("Warehouse", {"company": company, "warehouse_name": "Work In Progress"}, "name")
		or f"Work In Progress - {abbr}"
	)

	# --- Create Work Order ---
	wo = frappe.new_doc("Work Order")
	wo.production_item = item_code
	wo.bom_no = bom_name
	wo.qty = qty
	wo.company = company
	wo.fg_warehouse = fg_warehouse
	wo.wip_warehouse = wip_warehouse
	wo.source_warehouse = source_warehouse or fg_warehouse
	wo.planned_start_date = today()
	wo.skip_transfer = 1  # Skip material transfer, go straight to manufacture
	# Store SI reference in description for traceability
	wo.description = f"Auto-created from Sales Invoice {si_name}"
	wo.flags.ignore_permissions = True
	wo.insert()

	# Store custom SI link (the custom field added by setup/custom_fields.py)
	if frappe.db.has_column("Work Order", "custom_sales_invoice"):
		wo.db_set("custom_sales_invoice", si_name)

	wo.submit()
	frappe.db.commit()

	frappe.logger().info(f"Work Order {wo.name} created for {item_code} qty={qty} (SI: {si_name})")

	# --- Complete Job Cards ---
	_complete_job_cards(wo.name, qty)

	# --- Create Manufacture Stock Entry ---
	_create_manufacture_entry(wo.name, qty)


def _complete_job_cards(wo_name: str, qty) -> None:
	"""Start and complete all Job Cards for a Work Order."""
	job_cards = frappe.get_all(
		"Job Card",
		filters={"work_order": wo_name, "docstatus": 0},
		fields=["name", "for_quantity"],
	)

	if not job_cards:
		frappe.logger().info(f"No Job Cards found for Work Order {wo_name} - BOM may have no operations")
		return

	now = now_datetime()
	from_time = add_to_date(now, minutes=-1)

	for jc_info in job_cards:
		jc = frappe.get_doc("Job Card", jc_info.name)
		jc_qty = jc_info.for_quantity or qty

		# Add a time log entry to record the work
		jc.append("time_logs", {
			"from_time": from_time,
			"to_time": now,
			"completed_qty": jc_qty,
		})
		jc.total_completed_qty = jc_qty
		jc.flags.ignore_permissions = True
		jc.save()
		jc.submit()
		frappe.db.commit()

		frappe.logger().info(f"Job Card {jc_info.name} completed for Work Order {wo_name}")


def _create_manufacture_entry(wo_name: str, qty) -> None:
	"""Create and submit a Manufacture stock entry to finish the Work Order."""
	from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

	wo = frappe.get_doc("Work Order", wo_name)
	se_dict = make_stock_entry(wo_name, "Manufacture", qty)
	se = frappe.get_doc(se_dict)
	se.posting_date = today()
	se.posting_time = frappe.utils.nowtime()

	# Ensure each consumed row has a source warehouse so stock is actually
	# deducted, and allow zero valuation rate for items without a prior receipt.
	for row in se.items:
		if not row.s_warehouse and not row.t_warehouse:
			row.s_warehouse = wo.source_warehouse or wo.wip_warehouse
		elif not row.s_warehouse and row.t_warehouse and row.item_code != wo.production_item:
			row.s_warehouse = wo.source_warehouse or wo.wip_warehouse

		if not row.get("basic_rate") and not row.get("valuation_rate"):
			row.allow_zero_valuation_rate = 1

	se.flags.ignore_permissions = True

	# Allow negative stock — lab consumables may not have purchase receipts yet
	# but consumption must still be recorded when tests are completed.
	# Temporarily enable in Stock Settings so the SLE validation allows it.
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

	frappe.logger().info(f"Manufacture Stock Entry {se.name} created for Work Order {wo_name}")


def complete_stuck_work_orders(site=None) -> None:
	"""One-time utility to process all submitted Work Orders stuck at
	'Not Started'. Completes Job Cards (if any) and creates Manufacture stock
	entries. Skips non-stock items. Safe to run multiple times.

	Usage:
	  bench --site <site> execute diagnostic_management.overrides.work_order_hooks.complete_stuck_work_orders
	"""
	stuck_wos = frappe.get_all(
		"Work Order",
		filters={"status": "Not Started", "docstatus": 1},
		fields=["name", "production_item", "qty"],
		order_by="creation asc",
	)

	if not stuck_wos:
		print("No stuck Work Orders found.")
		return

	print(f"Found {len(stuck_wos)} stuck Work Orders. Processing...")

	succeeded = 0
	skipped = 0
	failed: list[dict] = []

	for wo_info in stuck_wos:
		wo_name = wo_info.name
		item = wo_info.production_item
		qty = wo_info.qty

		# Skip non-stock items — they can't have Manufacture stock entries
		is_stock_item = frappe.db.get_value("Item", item, "is_stock_item")
		if not is_stock_item:
			print(f"  SKIP {wo_name} - {item} is not a stock item")
			skipped += 1
			continue

		try:
			_complete_job_cards(wo_name, qty)
			_create_manufacture_entry(wo_name, qty)
			succeeded += 1
			print(f"  OK   {wo_name} - {item} x {qty}")
		except Exception as e:
			failed.append({"wo": wo_name, "item": item, "error": str(e)})
			print(f"  FAIL {wo_name} - {item}: {e}")
			frappe.db.rollback()

	print(f"\nDone: {succeeded} completed, {skipped} skipped (non-stock), {len(failed)} failed")
	for f in failed:
		print(f"  - {f['wo']} ({f['item']}): {f['error']}")
