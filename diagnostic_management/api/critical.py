import frappe


@frappe.whitelist()
def acknowledge(report: str, notes: str = "") -> dict:
	"""Record a referring doctor's acknowledgement of a critical result."""
	doc = frappe.get_doc("Diagnostic Report", report)
	doc.add_comment(
		"Comment",
		text=(
			f"<b>Critical Result Acknowledged</b><br>"
			f"By: {frappe.utils.escape_html(frappe.session.user)}<br>"
			+ (f"Notes: {frappe.utils.escape_html(notes)}" if notes else "")
		),
	)
	# Mark the report as acknowledged via custom field if present; harmless if absent.
	try:
		doc.db_set("critical_acknowledged", 1)
		doc.db_set("critical_acknowledged_at", frappe.utils.now_datetime())
	except Exception:
		pass
	return {"ok": True, "report": report}
