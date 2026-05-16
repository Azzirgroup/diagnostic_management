"""Phlebotomy / Sample Collection worklist endpoints."""

import frappe
from frappe.utils import now_datetime


@frappe.whitelist()
def worklist(status: str | None = None, limit: int = 100) -> list[dict]:
	"""Pending and recently-collected samples for the collection station."""
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Draft", "Collected"]]
	return frappe.get_all(
		"Sample Collection",
		fields=[
			"name", "patient", "patient_name", "sample", "sample_qty",
			"collection_date", "collection_time", "status", "container",
			"barcode", "received_condition",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def mark_collected(sample: str, container: str | None = None, barcode: str | None = None) -> dict:
	doc = frappe.get_doc("Sample Collection", sample)
	if "status" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("status", "Collected")
	now = now_datetime()
	if "collection_date" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("collection_date", now.date())
	if "collection_time" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("collection_time", now.time())
	if container:
		doc.db_set("container", container)
	if barcode:
		try:
			doc.db_set("barcode", barcode)
		except Exception:
			pass
	doc.add_comment("Comment", text=f"<b>Sample Collected</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")
	return {"ok": True, "sample": sample, "status": "Collected"}


@frappe.whitelist()
def accession_queue(limit: int = 100) -> list[dict]:
	"""Samples awaiting accession into the lab."""
	return frappe.get_all(
		"Sample Collection",
		fields=[
			"name", "patient", "patient_name", "sample", "sample_qty",
			"collection_date", "collection_time", "status", "barcode",
		],
		filters={"status": ["in", ["Collected", "Draft"]]},
		order_by="creation asc",
		limit_page_length=int(limit),
	)
