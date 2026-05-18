"""Phlebotomy / Sample Collection worklist endpoints.

Frappe's Sample Collection doctype keeps the date+time of collection on a
single `collected_time` Datetime column (not separate date/time fields),
and has no `container` column. The endpoints below match those actual
field names; the frontend renders `collected_time` directly.
"""

import frappe
from frappe.utils import now_datetime


_LIST_FIELDS = [
	"name", "patient", "patient_name", "sample", "sample_qty", "sample_uom",
	"collected_time", "status", "barcode", "received_condition",
	"collection_point", "collected_by", "service_request", "docstatus",
	"rejection_reason_text",
]


@frappe.whitelist()
def worklist(status: str | None = None, limit: int = 100) -> list[dict]:
	"""Pending and recently-collected samples for the collection station."""
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Pending", "Partly Collected", "Collected"]]
	return frappe.get_all(
		"Sample Collection",
		fields=_LIST_FIELDS,
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def mark_collected(sample: str, collection_point: str | None = None, barcode: str | None = None) -> dict:
	doc = frappe.get_doc("Sample Collection", sample)
	field_names = {df.fieldname for df in doc.meta.fields}
	if "status" in field_names:
		doc.db_set("status", "Collected")
	if "collected_time" in field_names:
		doc.db_set("collected_time", now_datetime())
	if "collected_by" in field_names:
		doc.db_set("collected_by", frappe.session.user)
	if collection_point and "collection_point" in field_names:
		doc.db_set("collection_point", collection_point)
	if barcode and "barcode" in field_names:
		doc.db_set("barcode", barcode)
	doc.add_comment("Comment", text=f"<b>Sample Collected</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")
	return {"ok": True, "sample": sample, "status": "Collected"}


@frappe.whitelist()
def accession_queue(limit: int = 200) -> list[dict]:
	"""All samples relevant to the accession workflow — front-end filters
	into Pending / Accepted / Rejected tabs by looking at `received_condition`.

	Returns rows in all three states so the SPA tab counts stay accurate
	without firing three round-trips.
	"""
	return frappe.get_all(
		"Sample Collection",
		fields=_LIST_FIELDS,
		filters={"status": ["in", ["Pending", "Partly Collected", "Collected"]]},
		order_by="creation desc",
		limit_page_length=int(limit),
	)
