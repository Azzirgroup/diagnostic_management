"""Phlebotomy / Sample Collection worklist endpoints.

Frappe's Sample Collection doctype keeps the date+time of collection on a
single `collected_time` Datetime column (not separate date/time fields).
`collection_point` is a Link to Healthcare Service Unit; `barcode`,
`container` and `received_condition` are ADMS custom fields (see
setup/custom_fields.py). The endpoints below match those actual field
names; the frontend renders `collected_time` directly.
"""

import frappe
from frappe.utils import cint, flt, get_datetime, now_datetime


# Specimen lifecycle (genetest-style), in order. `workflow_status` advances
# along this; "Rejected" is an off-ramp reachable from any stage.
STATUS_ORDER = [
	"To Be Collected", "Collected", "In Transit", "Received",
	"In Processing", "Tested", "Stored",
]


def next_statuses(current: str | None) -> list[str]:
	"""Statuses reachable forward from `current`, plus Rejected."""
	try:
		idx = STATUS_ORDER.index(current)
	except ValueError:
		idx = -1
	nxt = STATUS_ORDER[idx + 1:]
	return [*nxt, "Rejected"]


_LIST_FIELDS = [
	"name", "patient", "patient_name", "sample", "sample_qty", "sample_uom",
	"collected_time", "collected_by", "num_print", "sample_details",
	"referring_practitioner", "status", "workflow_status", "barcode", "container",
	"received_condition", "collection_point", "service_request", "docstatus",
	"rejection_reason_text", "is_urgent",
]


@frappe.whitelist()
def worklist(status: str | None = None, limit: int = 100) -> list[dict]:
	"""Samples awaiting collection.

	Marley's Sample Collection.validate() forces status → "Collected" on
	insert whenever the doc has no observation rows (which is the case for
	every sample spun up from a Lab Test), so `status` can't distinguish
	"to collect" from "collected". We key the worklist off `collected_time`
	instead: a row needs collecting until a collector stamps it (via
	mark_collected). An explicit `status` filter is still honoured for
	callers that want it.
	"""
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["collected_time"] = ["is", "not set"]
	return frappe.get_all(
		"Sample Collection",
		fields=_LIST_FIELDS,
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def mark_collected(
	sample: str,
	specimen: str | None = None,
	sample_qty: float | None = None,
	sample_uom: str | None = None,
	collected_by: str | None = None,
	collected_time: str | None = None,
	num_print: int | None = None,
	collection_point: str | None = None,
	referring_practitioner: str | None = None,
	barcode: str | None = None,
	container: str | None = None,
	received_condition: str | None = None,
	sample_details: str | None = None,
) -> dict:
	"""Record a sample as collected, capturing the full Sample Collection detail.

	Mirrors the Healthcare `Sample Collection` doctype's collection fields:
	Sample (`specimen` → doc.sample), Quantity, UOM, Collected By/On,
	No. of prints, Collection Details, Collection Point, Referring
	Practitioner — plus the ADMS custom fields barcode / container /
	received_condition. `sample` is the Sample Collection document name.

	Each value is persisted only when the field exists on the doctype and a
	value was supplied, so the call degrades gracefully on sites missing the
	ADMS custom fields. Link values are validated before writing to avoid
	dangling links. `collected_time` defaults to now and `collected_by` to
	the current user when not provided.
	"""
	doc = frappe.get_doc("Sample Collection", sample)
	fns = {df.fieldname for df in doc.meta.fields}

	if "status" in fns:
		doc.db_set("status", "Collected")
	if "workflow_status" in fns and (doc.get("workflow_status") or "To Be Collected") == "To Be Collected":
		doc.db_set("workflow_status", "Collected")
	if "collected_time" in fns:
		doc.db_set("collected_time", get_datetime(collected_time) if collected_time else now_datetime())
	if "collected_by" in fns:
		who = collected_by if (collected_by and frappe.db.exists("User", collected_by)) else frappe.session.user
		doc.db_set("collected_by", who)
	if specimen and "sample" in fns and frappe.db.exists("Lab Test Sample", specimen):
		doc.db_set("sample", specimen)
	if sample_qty is not None and "sample_qty" in fns:
		doc.db_set("sample_qty", flt(sample_qty))
	if sample_uom is not None and "sample_uom" in fns:
		doc.db_set("sample_uom", sample_uom)
	if num_print is not None and "num_print" in fns:
		doc.db_set("num_print", cint(num_print))
	if collection_point and "collection_point" in fns and frappe.db.exists("Healthcare Service Unit", collection_point):
		doc.db_set("collection_point", collection_point)
	if referring_practitioner and "referring_practitioner" in fns and frappe.db.exists("Healthcare Practitioner", referring_practitioner):
		doc.db_set("referring_practitioner", referring_practitioner)
	if barcode and "barcode" in fns:
		doc.db_set("barcode", barcode)
	if container and "container" in fns:
		doc.db_set("container", container)
	if received_condition and "received_condition" in fns:
		doc.db_set("received_condition", received_condition)
	if sample_details is not None and "sample_details" in fns:
		doc.db_set("sample_details", sample_details)

	details = []
	if barcode:
		details.append(f"Barcode: {frappe.utils.escape_html(barcode)}")
	if container:
		details.append(f"Container: {frappe.utils.escape_html(container)}")
	if collection_point:
		details.append(f"Collection point: {frappe.utils.escape_html(collection_point)}")
	doc.add_comment(
		"Comment",
		text=(
			f"<b>Sample Collected</b><br>By: {frappe.utils.escape_html(doc.get('collected_by') or frappe.session.user)}"
			+ ("<br>" + "<br>".join(details) if details else "")
		),
	)
	return {"ok": True, "sample": sample, "status": "Collected"}


def resolve_order_samples(service_request: str) -> list[dict]:
	"""Sample Collections belonging to an order, resolved the Marley way.

	Marley aggregates samples by patient + specimen type and links them via
	`Lab Test.sample` — it does NOT stamp `Sample Collection.service_request`.
	So we walk Service Request → Lab Test (`service_request`) → Sample
	Collection (`lab_test.sample`), and also pick up any sample directly
	tagged with the service_request (belt-and-braces for imaging or
	manually-linked rows). De-duplicated, oldest first.
	"""
	if not service_request:
		return []
	lab_tests = frappe.get_all(
		"Lab Test",
		filters={"service_request": service_request, "docstatus": ["!=", 2]},
		pluck="sample",
	)
	direct = frappe.get_all(
		"Sample Collection",
		filters={"service_request": service_request},
		pluck="name",
	)
	names = list(dict.fromkeys([s for s in lab_tests if s] + direct))
	if not names:
		return []
	return frappe.get_all(
		"Sample Collection",
		fields=_LIST_FIELDS,
		filters={"name": ["in", names]},
		order_by="creation asc",
	)


@frappe.whitelist()
def for_order(service_request: str, limit: int = 50) -> list[dict]:
	"""Sample Collections raised for a given Service Request (order)."""
	return resolve_order_samples(service_request)[: int(limit)]


@frappe.whitelist()
def advance_status(sample: str, new_status: str, note: str | None = None) -> dict:
	"""Move a sample to `new_status` along the specimen lifecycle.

	Updates `workflow_status` and keeps Marley's native fields consistent:
	stamps collected_time/by on first forward move, sets received_condition
	to Acceptable on "Received". "Rejected" is the off-ramp.
	"""
	if new_status not in (*STATUS_ORDER, "Rejected"):
		frappe.throw(f"Invalid status: {new_status}")
	doc = frappe.get_doc("Sample Collection", sample)
	fns = {df.fieldname for df in doc.meta.fields}

	if "workflow_status" in fns:
		doc.db_set("workflow_status", new_status)
	if new_status not in ("To Be Collected", "Rejected"):
		if "collected_time" in fns and not doc.get("collected_time"):
			doc.db_set("collected_time", now_datetime())
		if "collected_by" in fns and not doc.get("collected_by"):
			doc.db_set("collected_by", frappe.session.user)
		if "status" in fns:
			doc.db_set("status", "Collected")
	if new_status == "Received" and "received_condition" in fns and not doc.get("received_condition"):
		doc.db_set("received_condition", "Acceptable")

	doc.add_comment(
		"Comment",
		text=(
			f"<b>Status → {frappe.utils.escape_html(new_status)}</b>"
			+ (f"<br>{frappe.utils.escape_html(note)}" if note else "")
		),
	)
	return {"ok": True, "sample": sample, "workflow_status": new_status}


@frappe.whitelist()
def service_units(limit: int = 100) -> list[dict]:
	"""Leaf Healthcare Service Units, for the collection-point picker.

	Excludes group nodes (they're folders, not real collection points).
	Returns an empty list on sites where the doctype isn't present.
	"""
	try:
		return frappe.get_all(
			"Healthcare Service Unit",
			fields=["name"],
			filters={"is_group": 0},
			order_by="name",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def sample_types(limit: int = 100) -> list[dict]:
	"""Lab Test Sample rows, for the specimen picker (Sample Collection.sample)."""
	try:
		return frappe.get_all(
			"Lab Test Sample",
			fields=["name"],
			order_by="name",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def collectors(limit: int = 200) -> list[dict]:
	"""Enabled users, for the 'Collected By' picker."""
	try:
		return frappe.get_all(
			"User",
			fields=["name", "full_name"],
			filters={"enabled": 1, "name": ["not in", ["Guest"]]},
			order_by="full_name",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def practitioners(limit: int = 200) -> list[dict]:
	"""Healthcare Practitioners, for the 'Referring Practitioner' picker."""
	try:
		return frappe.get_all(
			"Healthcare Practitioner",
			fields=["name", "practitioner_name"],
			order_by="practitioner_name",
			limit_page_length=int(limit),
		)
	except Exception:
		return []


@frappe.whitelist()
def companies(limit: int = 100) -> list[dict]:
	"""Companies, for the Sample Collection 'Company' picker."""
	try:
		return frappe.get_all("Company", fields=["name"], order_by="name", limit_page_length=int(limit))
	except Exception:
		return []


@frappe.whitelist()
def observation_templates(limit: int = 500) -> list[dict]:
	"""Observation Templates, for the 'Samples' child grid."""
	try:
		return frappe.get_all(
			"Observation Template", fields=["name"], order_by="name", limit_page_length=int(limit)
		)
	except Exception:
		return []


# Scalar fields the Sample Collection page may write (status is excluded —
# Marley's validate() owns it).
_SAVE_FIELDS = {
	"barcode", "container", "sample", "sample_uom", "sample_qty", "collected_by",
	"collected_time", "num_print", "collection_point", "referring_practitioner",
	"company", "appointment", "sample_details", "received_condition",
	"rejection_reason_text",
}
# Editable columns on the observation_sample_collection child table.
_CHILD_FIELDS = {
	"observation_template", "sample", "sample_qty", "collection_point",
	"collection_date_time",
}


@frappe.whitelist()
def save_collection(
	name: str,
	values: dict | str | None = None,
	rows: list | str | None = None,
	collect: int = 0,
) -> dict:
	"""Save the full Sample Collection record from the dedicated SPA page.

	Writes the allowed scalar fields and replaces the
	`observation_sample_collection` child rows, then saves through the doc
	model so Marley's validation (link checks, status derivation) runs
	properly. With `collect=1`, stamps collected_time/by if not already set.
	"""
	import json

	doc = frappe.get_doc("Sample Collection", name)
	fns = {df.fieldname for df in doc.meta.fields}

	vals = json.loads(values) if isinstance(values, str) else (values or {})
	for k, v in vals.items():
		if k in _SAVE_FIELDS and k in fns:
			doc.set(k, v if v != "" else None)

	if rows is not None and "observation_sample_collection" in fns:
		rowlist = json.loads(rows) if isinstance(rows, str) else rows
		doc.set("observation_sample_collection", [])
		for r in rowlist or []:
			child = {k: r.get(k) for k in _CHILD_FIELDS if r.get(k) not in (None, "")}
			# status is reqd on the child row; Marley uses Open/Collected.
			child["status"] = r.get("status") or "Open"
			doc.append("observation_sample_collection", child)

	if int(collect or 0) and "collected_time" in fns and not doc.get("collected_time"):
		doc.set("collected_time", now_datetime())
		if "collected_by" in fns and not doc.get("collected_by"):
			doc.set("collected_by", frappe.session.user)

	doc.save(ignore_permissions=False)
	return {
		"ok": True,
		"name": doc.name,
		"status": doc.get("status"),
		"collected_time": str(doc.get("collected_time") or ""),
	}


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
