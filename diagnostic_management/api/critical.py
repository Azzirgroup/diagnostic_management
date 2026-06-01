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
def detail(report: str) -> dict:
	"""Full critical-finding detail payload: the Diagnostic Report plus
	all Critical Finding Log rows that reference it, ordered oldest-first.

	We read the report fields directly via `frappe.db.get_value` rather
	than `as_dict()` because Marley's Diagnostic Report controller has a
	`sales_invoice_status` property that hits `frappe.get_meta(None)`
	when `ref_doctype` is unset, raising `DocType None not found`.
	"""
	if not report:
		frappe.throw("report is required")
	if not frappe.db.exists("Diagnostic Report", report):
		frappe.throw(f"Diagnostic Report {report} not found", frappe.DoesNotExistError)

	fields = [
		"name", "patient", "patient_name", "practitioner", "practitioner_name",
		"status", "is_critical", "critical_acknowledged", "critical_acknowledged_at",
		"creation", "modified", "docname", "ref_doctype", "title", "company",
	]
	row = frappe.db.get_value("Diagnostic Report", report, fields, as_dict=True) or {}
	row["log"] = frappe.get_all(
		"Critical Finding Log",
		fields=[
			"name", "severity", "status", "detected_at", "notified_at",
			"acknowledged_at", "acknowledged_by", "ack_notes",
			"notification_channel", "escalation_level", "test_or_modality",
			"summary",
		],
		filters={"report": report},
		order_by="creation asc",
	)
	return row


@frappe.whitelist()
def result_payload(report: str) -> dict:
	"""Full result body behind a critical finding — the lab tests + every result
	row (numeric with reference ranges, descriptive) on the linked sample or
	test, plus the report's sign-off fields (diagnosis/clinical notes/etc.).

	Resolves the right shape from the Diagnostic Report's `sample_collection`
	(per-sample, the modern ADMS shape) or its legacy `docname`/`ref_doctype`
	(per-Lab Test). Returns `{shape, sample?|lab_test?, report_fields}` so the
	UI can render the full result instead of just metadata.
	"""
	if not frappe.db.exists("Diagnostic Report", report):
		frappe.throw(f"Diagnostic Report {report} not found", frappe.DoesNotExistError)

	fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	report_fields = ["status", "is_critical", "critical_acknowledged"]
	for f in ("diagnosis", "clinical_notes", "pathologist_remarks", "accreditation_type",
	          "pathologist_name", "is_urgent", "urgent_review_status",
	          "ref_doctype", "docname", "sample_collection"):
		if f in fields:
			report_fields.append(f)
	rpt = frappe.db.get_value("Diagnostic Report", report, report_fields, as_dict=True) or {}

	# Prefer the per-Sample shape (current ADMS model) when present.
	sample = rpt.get("sample_collection")
	if not sample and rpt.get("ref_doctype") == "Sample Collection":
		sample = rpt.get("docname")
	if sample and frappe.db.exists("Sample Collection", sample):
		from diagnostic_management.api.results import get_sample
		return {
			"shape": "sample",
			"sample": get_sample(sample),
			"report": rpt,
		}

	# Fallback: per-Lab Test (legacy shape — early ADMS reports).
	lt = rpt.get("docname") if rpt.get("ref_doctype") == "Lab Test" else None
	if lt and frappe.db.exists("Lab Test", lt):
		from diagnostic_management.api.results import get_lab_test
		return {
			"shape": "lab_test",
			"lab_test": get_lab_test(lt),
			"report": rpt,
		}

	return {"shape": "none", "report": rpt}


@frappe.whitelist()
def submit_peer_review(
	report: str,
	outcome: str = "Agree",
	review_notes: str = "",
	discrepancy_severity: str | None = None,
	concurrence: float | None = None,
) -> dict:
	"""Submit a real Peer Review Case for a critical Diagnostic Report.

	If no Peer Review Case exists yet for this report, we create one on the fly
	(linked to the report + patient) and immediately close it with the
	reviewer's outcome — that's the natural workflow when a clinician reviews
	a critical result from the dashboard. Also marks the critical finding as
	acknowledged so it leaves the Pending Review tab.
	"""
	if not frappe.db.exists("Diagnostic Report", report):
		frappe.throw(f"Diagnostic Report {report} not found", frappe.DoesNotExistError)
	rpt = frappe.db.get_value(
		"Diagnostic Report", report,
		["patient", "patient_name", "practitioner", "owner"],
		as_dict=True,
	) or {}

	existing = frappe.db.get_value("Peer Review Case", {"subject_report": report}, "name")
	if existing:
		case_name = existing
	else:
		case = frappe.get_doc({
			"doctype": "Peer Review Case",
			"subject_report": report,
			"patient": rpt.get("patient"),
			"patient_name": rpt.get("patient_name"),
			"section": "Lab",
			"priority": "Urgent",
			"original_reporter": rpt.get("owner") or rpt.get("practitioner"),
			"assigned_reviewer": frappe.session.user,
			"status": "In Review",
		})
		case.insert(ignore_permissions=True)
		case_name = case.name

	from diagnostic_management.api.lab import submit_peer_review as lab_submit
	res = lab_submit(
		name=case_name,
		outcome=outcome,
		review_notes=review_notes,
		discrepancy_severity=discrepancy_severity,
		concurrence=concurrence,
	)

	# Also close out the critical-finding side so this leaves the "Pending Review" tab.
	try:
		acknowledge(report, notes=f"Peer review — {outcome}" + (f": {review_notes}" if review_notes else ""))
	except Exception:
		frappe.log_error(title="critical.submit_peer_review: acknowledge failed")

	return {"ok": True, "report": report, "case": case_name, "outcome": res.get("outcome", outcome)}


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
