import frappe


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
	"""Mark a Sample Collection as rejected and write an audit comment.

	The doctype itself stays as standard Marley `Sample Collection`; the
	rejection metadata is stored as a structured Comment so we don't
	require new fields in v1. When the dedicated rejection custom fields
	ship in install.py, this method will populate them too.
	"""
	doc = frappe.get_doc("Sample Collection", sample)

	# Soft-cancel the sample by setting workflow_state — actual cancel keeps
	# audit data intact while removing the sample from downstream worklists.
	if "status" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("status", "Rejected")

	# Audit comment captures all rejection metadata in one searchable record.
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
		# Hook for the notification engine — placeholder, the real impl ships
		# in a later phase alongside the SMS/WhatsApp adapter.
		frappe.publish_realtime(
			"sample_rejected",
			{"sample": sample, "reason": reason, "severity": severity},
			doctype="Sample Collection",
			docname=sample,
		)

	return {"ok": True, "sample": sample, "status": "Rejected"}


@frappe.whitelist()
def accept(sample: str, destination: str | None = None, notes: str = "") -> dict:
	"""Accept a sample into the lab and route it to the destination bench."""
	doc = frappe.get_doc("Sample Collection", sample)
	if "status" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("status", "Received")
	if notes:
		doc.add_comment("Comment", text=f"<b>Accessioned</b><br>{frappe.utils.escape_html(notes)}")
	if destination:
		doc.add_comment("Info", text=f"Routed to: {destination}")
	return {"ok": True, "sample": sample, "status": "Received"}
