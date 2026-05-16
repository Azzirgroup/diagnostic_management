import frappe


@frappe.whitelist()
def acknowledge(report: str, notes: str = "") -> dict:
	"""Record a referring doctor's acknowledgement of a critical result.

	Marks the underlying Diagnostic Report as acknowledged AND closes any
	open Critical Finding Log entries that target the same report, so the
	Critical Findings dashboard reflects the new state immediately.
	"""
	doc = frappe.get_doc("Diagnostic Report", report)
	doc.add_comment(
		"Comment",
		text=(
			f"<b>Critical Result Acknowledged</b><br>"
			f"By: {frappe.utils.escape_html(frappe.session.user)}<br>"
			+ (f"Notes: {frappe.utils.escape_html(notes)}" if notes else "")
		),
	)
	try:
		doc.db_set("critical_acknowledged", 1)
		doc.db_set("critical_acknowledged_at", frappe.utils.now_datetime())
	except Exception:
		pass

	# Close any open Critical Finding Log rows targeting this report.
	try:
		logs = frappe.get_all(
			"Critical Finding Log",
			filters={"report": report, "status": ["in", ["Detected", "Notified", "Escalated"]]},
			pluck="name",
		)
		for log_name in logs:
			log = frappe.get_doc("Critical Finding Log", log_name)
			log.status = "Acknowledged"
			log.acknowledged_by = frappe.session.user
			log.acknowledged_at = frappe.utils.now_datetime()
			if notes:
				log.ack_notes = notes
			log.save(ignore_permissions=True)
	except Exception:
		# Critical Finding Log is optional — never block the ack.
		frappe.log_error(title="critical.acknowledge: failed to close CFL")

	return {"ok": True, "report": report}


@frappe.whitelist()
def list_open(severity: str | None = None, limit: int = 100) -> list[dict]:
	"""Return all critical findings that still need attention."""
	filters: dict = {"is_critical": 1, "critical_acknowledged": 0}
	rows = frappe.get_all(
		"Diagnostic Report",
		fields=[
			"name", "docname", "patient", "patient_name", "status",
			"is_critical", "critical_acknowledged", "creation", "modified",
		],
		filters=filters,
		order_by="creation desc",
		limit_page_length=int(limit),
	)
	# Layer in log records when available so the timeline can render.
	logs = {}
	try:
		log_rows = frappe.get_all(
			"Critical Finding Log",
			fields=["name", "report", "severity", "status", "detected_at", "notified_at", "acknowledged_at", "escalation_level"],
			filters={"report": ["in", [r["name"] for r in rows]]} if rows else None,
		)
		for lr in log_rows or []:
			logs.setdefault(lr["report"], []).append(lr)
	except Exception:
		pass
	for r in rows:
		r["log"] = logs.get(r["name"], [])
		if severity and not any(lr.get("severity") == severity for lr in r["log"]):
			r["_filter_out"] = True
	if severity:
		rows = [r for r in rows if not r.get("_filter_out")]
	return rows


@frappe.whitelist()
def log_finding(
	report: str,
	severity: str = "High",
	test_or_modality: str | None = None,
	summary: str | None = None,
	notification_channel: str | None = None,
) -> dict:
	"""Create a Critical Finding Log row when a result is flagged."""
	rpt = frappe.get_doc("Diagnostic Report", report)
	doc = frappe.get_doc({
		"doctype": "Critical Finding Log",
		"report": report,
		"patient": rpt.get("patient"),
		"test_or_modality": test_or_modality,
		"severity": severity,
		"detected_at": frappe.utils.now_datetime(),
		"referring_practitioner": rpt.get("practitioner"),
		"notification_channel": notification_channel,
		"status": "Detected",
		"summary": summary,
	}).insert(ignore_permissions=True)
	return {"ok": True, "name": doc.name}
