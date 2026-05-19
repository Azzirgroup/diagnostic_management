"""Sample Collection lifecycle endpoints.

Marley's Sample Collection.status Select is restricted to
`Pending / Partly Collected / Collected`. To track *what happened after
collection* (accepted into the lab, rejected for unsuitable specimen) we
use the `received_condition` custom field added in setup/custom_fields.py:

  Acceptable                                → accepted into the lab
  Haemolysed | Clotted | Insufficient |
  Wrong Tube | Other                        → rejected

`status` itself stays in its native Select range; downstream queries filter
on `received_condition` + `status` together to derive the "accepted" and
"rejected" views the SPA needs.
"""

import frappe

# Subset of `received_condition` values that count as "rejected".
REJECT_CONDITIONS = ["Haemolysed", "Clotted", "Insufficient", "Wrong Tube", "Other"]


@frappe.whitelist()
def reject(
	sample: str,
	reason: str,
	severity: str = "Medium",
	notes: str = "",
	recollection_required: bool = False,
	target_date: str | None = None,
	target_time: str | None = None,
	notify_caller: bool = False,
) -> dict:
	"""Mark a Sample Collection as rejected.

	Persists the rejection metadata in the `received_condition` Select and
	the free-text `rejection_reason_text` field, and writes an audit
	Comment with the full context. `status` is left in its native value so
	Marley validation doesn't reject the save.
	"""
	doc = frappe.get_doc("Sample Collection", sample)
	field_names = {df.fieldname for df in doc.meta.fields}

	if "received_condition" in field_names:
		# Map the form's friendly reason to the doctype's Select options.
		condition = reason if reason in REJECT_CONDITIONS else "Other"
		doc.db_set("received_condition", condition)
	if "rejection_reason_text" in field_names:
		doc.db_set("rejection_reason_text", f"{reason} (severity: {severity}){' — ' + notes if notes else ''}")

	doc.add_comment(
		"Comment",
		text=(
			f"<b>Sample Rejected</b><br>"
			f"Reason: {frappe.utils.escape_html(reason)}<br>"
			f"Severity: {frappe.utils.escape_html(severity)}<br>"
			f"Recollection: {'Yes' if recollection_required else 'No'}"
			+ (f" — {target_date} {target_time}" if recollection_required and target_date else "")
			+ (f"<br>Notes: {frappe.utils.escape_html(notes)}" if notes else "")
		),
	)

	if notify_caller:
		# Wired up by the SMS/WhatsApp adapter in a later phase.
		frappe.publish_realtime(
			"sample_rejected",
			{"sample": sample, "reason": reason, "severity": severity},
			doctype="Sample Collection",
			docname=sample,
		)

	return {"ok": True, "sample": sample, "received_condition": condition if "received_condition" in field_names else None}


@frappe.whitelist()
def accept(sample: str, destination: str | None = None, notes: str = "") -> dict:
	"""Accept a sample into the lab. Sets `received_condition = "Acceptable"`."""
	doc = frappe.get_doc("Sample Collection", sample)
	field_names = {df.fieldname for df in doc.meta.fields}
	if "received_condition" in field_names:
		doc.db_set("received_condition", "Acceptable")
	if "rejection_reason_text" in field_names and doc.rejection_reason_text:
		# Clear any prior rejection note since the sample is now accepted.
		doc.db_set("rejection_reason_text", "")
	if notes:
		doc.add_comment("Comment", text=f"<b>Accepted</b><br>{frappe.utils.escape_html(notes)}")
	if destination:
		doc.add_comment("Info", text=f"Routed to: {frappe.utils.escape_html(destination)}")
	return {"ok": True, "sample": sample, "received_condition": "Acceptable"}
