"""Lab Hub / Verification Queue / Peer Review endpoints.

Marley v16 doctype status fields use the SELECT options below — none of
which match the friendly names I had originally:
  Sample Collection:    Pending / Partly Collected / Collected
  Diagnostic Report:    Open / Pending Review / Partially Approved / Approved / Rejected
  Lab Test:             Draft / Completed / Approved / Rejected / Cancelled

Filters and writes throughout this module use those actual values.
"""

import frappe
from frappe.utils import now_datetime


# Diagnostic Report's "verifiable / pending" set — anything not yet Approved.
DR_PENDING = ["Open", "Pending Review", "Partially Approved"]


@frappe.whitelist()
def hub_summary() -> dict:
	"""Counts the Lab Hub home page renders as quick-glance KPIs."""
	def _count(dt: str, filters: dict | None = None) -> int:
		try:
			return frappe.db.count(dt, filters or {})
		except Exception:
			return 0

	return {
		"pending_accession": _count("Sample Collection", {"status": "Pending"}),
		"in_analysis": _count("Sample Collection", {"status": "Partly Collected"}),
		"pending_verification": _count("Diagnostic Report", {"status": ["in", DR_PENDING]}),
		"qc_open": _count("QC Run", {"status": "Pending Review"}),
		"calibration_due": _count("Calibration Run", {"status": "Scheduled"}),
		"peer_review_open": _count("Peer Review Case", {"status": ["in", ["Open", "In Review", "Discussion"]]}),
	}


@frappe.whitelist()
def verification_queue(limit: int = 100) -> list[dict]:
	"""Diagnostic Reports waiting for verification."""
	return frappe.get_all(
		"Diagnostic Report",
		fields=[
			"name", "docname", "patient", "patient_name", "practitioner",
			"status", "is_critical", "critical_acknowledged", "creation", "modified",
		],
		filters={"status": ["in", DR_PENDING]},
		order_by="modified desc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def verify_report(name: str, conclusion: str | None = None) -> dict:
	"""Verify and release a Diagnostic Report — moves it to Approved."""
	doc = frappe.get_doc("Diagnostic Report", name)
	doc.db_set("status", "Approved")
	if conclusion is not None and "conclusion" in {df.fieldname for df in doc.meta.fields}:
		doc.db_set("conclusion", conclusion)
	doc.add_comment("Comment", text=f"<b>Verified & Released</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")
	return {"ok": True, "name": name, "status": "Approved"}


@frappe.whitelist()
def amend_report(name: str, reason: str) -> dict:
	"""Send a verified report back for amendment — Pending Review."""
	doc = frappe.get_doc("Diagnostic Report", name)
	doc.db_set("status", "Pending Review")
	doc.add_comment("Comment", text=f"<b>Amendment Requested</b><br>{frappe.utils.escape_html(reason)}")
	return {"ok": True, "name": name, "status": "Pending Review"}


# -- Peer Review -----------------------------------------------------------

@frappe.whitelist()
def peer_review_list(status: str | None = None, mine: int = 0, limit: int = 100) -> list[dict]:
	filters: dict = {}
	if status:
		filters["status"] = status
	else:
		filters["status"] = ["in", ["Open", "In Review", "Discussion"]]
	if int(mine or 0):
		filters["assigned_reviewer"] = frappe.session.user
	return frappe.get_all(
		"Peer Review Case",
		fields=[
			"name", "subject_report", "patient", "patient_name", "section", "modality",
			"priority", "original_reporter", "assigned_reviewer", "due_date",
			"status", "outcome", "submitted_at",
		],
		filters=filters,
		order_by="due_date asc",
		limit_page_length=int(limit),
	)


@frappe.whitelist()
def submit_peer_review(
	name: str,
	outcome: str = "Agree",
	review_notes: str = "",
	discrepancy_severity: str | None = None,
	concurrence: float | None = None,
) -> dict:
	doc = frappe.get_doc("Peer Review Case", name)
	doc.outcome = outcome
	if review_notes:
		doc.review_notes = review_notes
	if discrepancy_severity:
		doc.discrepancy_severity = discrepancy_severity
	if concurrence is not None:
		doc.concurrence = float(concurrence)
	doc.status = "Closed"
	doc.completed_at = now_datetime()
	doc.save(ignore_permissions=False)
	return {"ok": True, "name": name, "status": "Closed", "outcome": outcome}


# -- Lab Reports browser ---------------------------------------------------

@frappe.whitelist()
def list_lab_reports(
	query: str = "",
	status: str | None = None,
	date_from: str | None = None,
	date_to: str | None = None,
	limit: int = 100,
) -> list[dict]:
	"""Browseable list of Lab Reports — what the SPA's Lab Reports page shows.

	Filters:
	  - `query`: substring match against report name OR patient_name (case-insensitive).
	  - `status`: exact match on Lab Report.status (e.g. 'Approved', 'Pending').
	  - `date_from` / `date_to`: inclusive bounds on report_date (YYYY-MM-DD).
	"""
	if not frappe.db.exists("DocType", "Lab Report"):
		return []
	filters: dict = {}
	or_filters = None
	if status:
		filters["status"] = status
	if date_from:
		filters["report_date"] = [">=", date_from]
	if date_to:
		# When both bounds given, merge into a between filter.
		if "report_date" in filters:
			filters["report_date"] = ["between", [date_from, date_to]]
		else:
			filters["report_date"] = ["<=", date_to]
	if query:
		q = f"%{query.strip()}%"
		or_filters = [
			["Lab Report", "name", "like", q],
			["Lab Report", "patient_name", "like", q],
			["Lab Report", "patient", "like", q],
		]
	fields = [
		"name", "report_date", "patient", "patient_name", "patient_sex",
		"status", "referring_doctor", "referring_doctor_name", "department",
		"pathologist_name", "approved_by", "creation", "modified",
	]
	# Only fetch fields that exist on the doctype (Lab Report has lots of
	# optional custom fields the user may not have set up).
	available = {df.fieldname for df in frappe.get_meta("Lab Report").fields}
	fields = [f for f in fields if f in available or f in {"name", "creation", "modified"}]
	rows = frappe.get_all(
		"Lab Report",
		fields=fields,
		filters=filters,
		or_filters=or_filters,
		order_by="report_date desc, modified desc",
		limit_page_length=int(limit),
	)
	# Attach the linked Sample Collection (so the UI can deep-link back).
	if rows and "samples" in {df.fieldname for df in frappe.get_meta("Lab Report").fields}:
		report_names = [r["name"] for r in rows]
		samples_by_parent: dict[str, list[str]] = {}
		for lr_sample in frappe.get_all(
			"Lab Report Sample",
			fields=["parent", "lab_sample", "sample_type"],
			filters={"parent": ["in", report_names]},
		):
			samples_by_parent.setdefault(lr_sample.parent, []).append(lr_sample.lab_sample)
		for r in rows:
			r["samples"] = samples_by_parent.get(r["name"], [])
	return rows


@frappe.whitelist()
def lab_report_summary() -> dict:
	"""KPIs for the Lab Reports page header (total / approved / pending counts)."""
	if not frappe.db.exists("DocType", "Lab Report"):
		return {"total": 0, "approved": 0, "pending": 0, "today": 0}
	total = frappe.db.count("Lab Report")
	approved = frappe.db.count("Lab Report", {"status": "Approved"})
	pending = total - approved
	today = frappe.db.count("Lab Report", {"report_date": frappe.utils.today()})
	return {"total": total, "approved": approved, "pending": pending, "today": today}


@frappe.whitelist()
def lab_report_detail(name: str) -> dict:
	"""Full Lab Report payload for the SPA detail page — patient header, every
	result child table (numeric / lab_report_tests / grouped / descriptive /
	qualitative), reporter sign-off, and the linked samples."""
	if not name or not frappe.db.exists("Lab Report", name):
		frappe.throw(f"Lab Report {name} not found", frappe.DoesNotExistError)
	doc = frappe.get_doc("Lab Report", name)

	def _row(r, *fields):
		out = {}
		for f in fields:
			out[f] = getattr(r, f, None)
		return out

	# Compute patient age + age band for the header
	patient_info = {}
	if doc.patient and frappe.db.exists("Patient", doc.patient):
		p = frappe.db.get_value("Patient", doc.patient,
			["patient_name", "sex", "dob", "mobile", "email"], as_dict=True) or {}
		patient_info = dict(p)
		patient_info["name"] = doc.patient

	# Linked samples (Lab Report Sample child)
	samples = []
	if "samples" in {df.fieldname for df in frappe.get_meta("Lab Report").fields}:
		for s in (doc.get("samples") or []):
			samples.append(_row(s, "lab_sample", "sample_type", "collection_datetime"))

	# Build a section-comments dict so the SPA can show the same callouts the
	# printed report shows.
	try:
		comments = doc.get_section_comments_dict() or {}
	except Exception:
		comments = {}

	return {
		"name": doc.name,
		"report_date": str(doc.report_date or ""),
		"status": doc.status,
		"patient": patient_info,
		"patient_name": doc.patient_name,
		"patient_sex": doc.patient_sex,
		"referring_doctor": getattr(doc, "referring_doctor", None),
		"referring_doctor_name": getattr(doc, "referring_doctor_name", None),
		"department": getattr(doc, "department", None),
		"pathologist": getattr(doc, "pathologist", None),
		"pathologist_name": getattr(doc, "pathologist_name", None),
		"pathologist_qualification": getattr(doc, "pathologist_qualification", None),
		"accreditation_type": getattr(doc, "accreditation_type", None),
		"diagnosis": getattr(doc, "diagnosis", None),
		"clinical_notes": getattr(doc, "clinical_notes", None),
		"pathologist_remarks": getattr(doc, "pathologist_remarks", None),
		"lab_technician_signature": getattr(doc, "lab_technician_signature", None),
		"pathologist_signature": getattr(doc, "pathologist_signature", None),
		"custom_has_image_space": int(getattr(doc, "custom_has_image_space", 0) or 0),
		"samples": samples,
		"section_comments": comments,
		"numeric_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "uom",
			     "reference_range", "reference_min", "reference_max", "status", "is_abnormal",
			     "is_critical", "interpretation", "method", "instrument", "previous_value", "previous_date")
			for r in (doc.get("numeric_results") or [])
		],
		"lab_report_tests": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "uom",
			     "reference_range", "reference_min", "reference_max", "status", "is_abnormal",
			     "is_critical", "interpretation", "method", "instrument")
			for r in (doc.get("lab_report_tests") or [])
		],
		"grouped_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "group_name", "result_value", "uom",
			     "reference_range", "reference_min", "reference_max", "status", "is_abnormal", "is_critical")
			for r in (doc.get("grouped_results") or [])
		],
		"descriptive_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "interpretation")
			for r in (doc.get("descriptive_results") or [])
		],
		"qualitative_results": [
			_row(r, "name", "lab_test", "test_name", "test_category", "result_value", "result_type", "result_options", "is_abnormal")
			for r in (doc.get("qualitative_results") or [])
		],
	}


@frappe.whitelist()
def set_image_space(name: str, has_image_space: int = 0) -> dict:
	"""Toggle the 'Has image space' flag on a Lab Report so the next print
	either reserves a blank box above the signatures or skips it."""
	if not frappe.db.exists("Lab Report", name):
		frappe.throw(f"Lab Report {name} not found", frappe.DoesNotExistError)
	val = 1 if int(has_image_space or 0) else 0
	frappe.db.set_value("Lab Report", name, "custom_has_image_space", val)
	return {"ok": True, "name": name, "custom_has_image_space": val}
