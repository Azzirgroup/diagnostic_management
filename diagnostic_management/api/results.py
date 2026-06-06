"""Lab Test result entry — read a Lab Test's expanded result rows and save values.

ADMS uses Marley's native Lab Test result expansion: when a Lab Test is created
from a template, Marley fans the template into child rows by type — Single/
Compound → `normal_test_items`, Descriptive → `descriptive_test_items`, Grouped
→ the grouped sub-tests. This module just reads those rows for entry and writes
the values back, then (on complete) submits the test and ensures a Diagnostic
Report exists for verification.
"""

import json

import frappe

# Role that must authorize an URGENT case before it can be Verified & Released.
URGENT_REVIEW_ROLE = "Urgent Review Officer"


def _sample_is_urgent(sample: str) -> bool:
	"""A sample is urgent if the Sample Collection is flagged `is_urgent`, or any
	of its lab tests' Service Requests has Urgent/STAT priority (a Code Value like
	"Urgent-Priority"/"STAT-Priority")."""
	if frappe.db.get_value("Sample Collection", sample, "is_urgent"):
		return True
	srs = [s for s in frappe.get_all("Lab Test", filters={"sample": sample}, pluck="service_request") if s]
	if srs:
		for p in frappe.get_all("Service Request", filters={"name": ["in", srs]}, pluck="priority"):
			low = (p or "").lower()
			if "urgent" in low or "stat" in low:
				return True
	return False


def _allow_blanks(doc) -> None:
	"""Let a test complete even if some required result rows are left empty —
	Marley's validate_result_values throws otherwise (HTTP 417). Empty rows get
	allow_blank so the report can be finalised with partial entry."""
	for row in doc.normal_test_items:
		if not row.result_value and not row.allow_blank:
			row.allow_blank = 1
	for row in doc.descriptive_test_items:
		if not row.result_value and not row.allow_blank:
			row.allow_blank = 1


def _lab_test_rows(doc) -> dict:
	"""Shape one Lab Test's expanded result rows for the entry UI. Each
	normal-test row is overlaid with the reference range / UoM that matches
	THIS patient (via the template's ADMS Reference Range child table). Empty
	overlay → fall back to Marley's row-level normal_range / lab_test_uom."""
	from diagnostic_management.utils.reference_ranges import pick_reference_range
	normal = []
	for r in doc.normal_test_items:
		analyte = r.lab_test_name or r.lab_test_event
		picked = pick_reference_range(doc.template, analyte, doc.patient)
		normal.append({
			"name": r.name, "idx": r.idx,
			"lab_test_name": analyte,
			"result_value": r.result_value,
			"normal_range": (picked["range_text"] if picked else None) or r.normal_range,
			"lab_test_uom": (picked["uom"] if picked else None) or r.lab_test_uom,
			"lab_test_comment": r.lab_test_comment,
			"result_type": (picked["result_type"] if picked else None) or "Numeric",
			"result_options": (picked["result_options"] if picked else None) or "",
		})
	return {
		"name": doc.name,
		"template": doc.template,
		"status": doc.status,
		"docstatus": doc.docstatus,
		"normal_test_items": normal,
		"descriptive_test_items": [
			{
				"name": r.name, "idx": r.idx,
				"lab_test_particulars": r.lab_test_particulars,
				"result_value": r.result_value,
			}
			for r in doc.descriptive_test_items
		],
	}


@frappe.whitelist()
def get_sample(sample: str) -> dict:
	"""Sample-centric results payload — the Sample Collection + every Lab Test on
	it with its expanded result rows. Mirrors genetest's per-sample Lab Report.
	"""
	sc = frappe.db.get_value("Sample Collection", sample, ["patient", "patient_name", "sample"], as_dict=True) or {}
	lab_tests = frappe.get_all("Lab Test", filters={"sample": sample}, order_by="creation", pluck="name")

	# Urgent-review state: an urgent sample needs an Urgent Review Officer to
	# authorize the report before it can be Verified & Released.
	is_urgent = _sample_is_urgent(sample)
	report = _report_for_sample(sample)
	urgent_authorized = 0
	if report:
		urgent_authorized = 1 if frappe.db.get_value("Diagnostic Report", report, "urgent_review_status") == "Authorized" else 0

	return {
		"sample": sample,
		"patient": sc.get("patient"),
		"patient_name": sc.get("patient_name"),
		"sample_type": sc.get("sample"),
		"lab_tests": [_lab_test_rows(frappe.get_doc("Lab Test", n)) for n in lab_tests],
		"is_urgent": 1 if is_urgent else 0,
		"report": report,
		"urgent_authorized": urgent_authorized,
		"can_authorize_urgent": 1 if URGENT_REVIEW_ROLE in frappe.get_roles() else 0,
	}


def reset_sample_report_state(sample: str) -> None:
	"""Reset a sample's Diagnostic Report so a fresh workflow starts from a
	clean slate. Clears verification + urgent authorization + reporter sign-off
	so the gate fires again on the next Save & Complete. No-op when no DR exists
	for this sample yet.

	Why this matters: Marley reuses the same Sample Collection across orders
	for a patient + sample type, so a re-billing flow lands on the SAME DR as
	the previous clinical event. Without this reset the prior `Approved` /
	`Authorized` state would leak in and the gate would silently skip itself.
	"""
	existing = _report_for_sample(sample)
	if not existing:
		return
	fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	updates: dict = {}
	if "status" in fields:
		updates["status"] = "Pending Review"
	# Nullable fields → None; Check fields are NOT NULL so must use 0.
	for f in (
		"urgent_review_status", "urgent_reviewed_by", "urgent_reviewed_at",
		"report_signature", "pathologist_signature", "signed_by",
		"diagnosis", "clinical_notes", "pathologist_remarks", "pathologist_name",
		"critical_acknowledged_at", "conclusion",
	):
		if f in fields:
			updates[f] = None
	if "critical_acknowledged" in fields:
		updates["critical_acknowledged"] = 0
	frappe.db.set_value("Diagnostic Report", existing, updates)


def _report_for_sample(sample: str) -> str | None:
	"""The Diagnostic Report for a Sample Collection, if one exists yet."""
	if not frappe.db.exists("DocType", "Diagnostic Report"):
		return None
	fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	if "sample_collection" in fields:
		found = frappe.db.get_value("Diagnostic Report", {"sample_collection": sample}, "name")
		if found:
			return found
	return frappe.db.get_value("Diagnostic Report", {"ref_doctype": "Sample Collection", "docname": sample}, "name")


@frappe.whitelist()
def save_sample(
	sample: str,
	tests: list | str | None = None,
	complete: int = 0,
	is_critical: int = 0,
	conclusion: str | None = None,
) -> dict:
	"""Write results across ALL of a sample's lab tests, and (on complete)
	submit each and ensure ONE Diagnostic Report for the sample.
	"""
	tests = json.loads(tests) if isinstance(tests, str) else (tests or [])
	for t in tests:
		doc = frappe.get_doc("Lab Test", t["name"])
		if doc.docstatus == 1:
			continue
		nmap = {r["name"]: r for r in (t.get("normal") or [])}
		dmap = {r["name"]: r for r in (t.get("descriptive") or [])}
		for row in doc.normal_test_items:
			if row.name in nmap:
				row.result_value = nmap[row.name].get("result_value")
				if "lab_test_comment" in nmap[row.name]:
					row.lab_test_comment = nmap[row.name].get("lab_test_comment")
		for row in doc.descriptive_test_items:
			if row.name in dmap:
				row.result_value = dmap[row.name].get("result_value")
		if int(complete or 0):
			_allow_blanks(doc)
		doc.save(ignore_permissions=False)
		if int(complete or 0):
			doc.submit()

	report = None
	if int(complete or 0):
		report = _ensure_sample_report(sample, is_critical=int(is_critical or 0), conclusion=conclusion)
		# Stamp THIS submission's Lab Test names onto the DR so the Lab Report
		# builder pulls exactly this batch (and not stale Lab Tests left on the
		# reused Sample Collection from previous workflows).
		if report and tests:
			submitted = ",".join(t["name"] for t in tests if t.get("name"))
			fns = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
			if "custom_lab_tests_csv" in fns:
				frappe.db.set_value("Diagnostic Report", report, "custom_lab_tests_csv", submitted)
	return {"ok": True, "sample": sample, "report": report}


def _ensure_sample_report(sample: str, is_critical: int = 0, conclusion: str | None = None) -> str | None:
	"""One Diagnostic Report per Sample Collection (genetest's per-sample report)."""
	if not frappe.db.exists("DocType", "Diagnostic Report"):
		return None
	fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	existing = None
	if "sample_collection" in fields:
		existing = frappe.db.get_value("Diagnostic Report", {"sample_collection": sample}, "name")
	if not existing:
		existing = frappe.db.get_value("Diagnostic Report", {"ref_doctype": "Sample Collection", "docname": sample}, "name")
	sc = frappe.db.get_value("Sample Collection", sample, ["patient", "company", "referring_practitioner"], as_dict=True) or {}
	urgent = _sample_is_urgent(sample)
	if existing:
		updates = {}
		if "is_critical" in fields and is_critical:
			updates["is_critical"] = 1
		if "conclusion" in fields and conclusion:
			updates["conclusion"] = conclusion
		# A fresh Save & Complete on a sample whose DR was previously Approved
		# means the user has entered NEW results — those need fresh verification,
		# so reset the report to Pending Review and clear the prior sign-off /
		# urgent authorization. (Without this, reusing a sample across workflows
		# would keep the gate "Authorized" from the previous clinical event.)
		current_status = frappe.db.get_value("Diagnostic Report", existing, "status")
		if current_status == "Approved":
			updates["status"] = "Pending Review"
			for f in ("report_signature", "pathologist_signature", "signed_by", "diagnosis",
			          "clinical_notes", "pathologist_remarks", "pathologist_name"):
				if f in fields:
					updates[f] = None
		if "is_urgent" in fields and urgent:
			updates["is_urgent"] = 1
			# Re-set Pending (overwriting any prior Authorized) — fresh results need
			# fresh authorization. Also wipe who/when so the audit shows the new cycle.
			if "urgent_review_status" in fields:
				updates["urgent_review_status"] = "Pending"
			if "urgent_reviewed_by" in fields:
				updates["urgent_reviewed_by"] = None
			if "urgent_reviewed_at" in fields:
				updates["urgent_reviewed_at"] = None
		if updates:
			frappe.db.set_value("Diagnostic Report", existing, updates)
		return existing
	try:
		payload = {"doctype": "Diagnostic Report", "patient": sc.get("patient"), "status": "Pending Review"}
		if "sample_collection" in fields:
			payload["sample_collection"] = sample
		if "ref_doctype" in fields:
			payload["ref_doctype"] = "Sample Collection"
		if "docname" in fields:
			payload["docname"] = sample
		if "company" in fields:
			payload["company"] = sc.get("company")
		if "is_critical" in fields and is_critical:
			payload["is_critical"] = 1
		if "conclusion" in fields and conclusion:
			payload["conclusion"] = conclusion
		if "is_urgent" in fields and urgent:
			payload["is_urgent"] = 1
			if "urgent_review_status" in fields:
				payload["urgent_review_status"] = "Pending"
		dr = frappe.get_doc(payload)
		dr.insert(ignore_permissions=True)
		return dr.name
	except Exception:
		frappe.log_error(title="results._ensure_sample_report failed")
		return None


@frappe.whitelist()
def get_lab_test(name: str) -> dict:
	"""Return a Lab Test with its expanded result rows for the entry screen.
	Each normal-test row's `normal_range` / `lab_test_uom` is overlaid with the
	patient-matched ADMS Reference Range row when one is configured."""
	from diagnostic_management.utils.reference_ranges import pick_reference_range
	doc = frappe.get_doc("Lab Test", name)
	normal = []
	for r in doc.normal_test_items:
		analyte = r.lab_test_name or r.lab_test_event
		picked = pick_reference_range(doc.template, analyte, doc.patient)
		normal.append({
			"name": r.name, "idx": r.idx,
			"lab_test_name": analyte,
			"result_value": r.result_value,
			"normal_range": (picked["range_text"] if picked else None) or r.normal_range,
			"lab_test_uom": (picked["uom"] if picked else None) or r.lab_test_uom,
			"lab_test_comment": r.lab_test_comment,
			"allow_blank": r.allow_blank,
			"require_result_value": r.require_result_value,
			"result_type": (picked["result_type"] if picked else None) or "Numeric",
			"result_options": (picked["result_options"] if picked else None) or "",
		})
	return {
		"name": doc.name,
		"patient": doc.patient,
		"patient_name": doc.get("patient_name"),
		"template": doc.template,
		"status": doc.status,
		"docstatus": doc.docstatus,
		"practitioner": doc.get("practitioner"),
		"normal_test_items": normal,
		"descriptive_test_items": [
			{
				"name": r.name, "idx": r.idx,
				"lab_test_particulars": r.lab_test_particulars,
				"result_value": r.result_value,
				"allow_blank": r.allow_blank,
				"require_result_value": r.require_result_value,
			}
			for r in doc.descriptive_test_items
		],
	}


@frappe.whitelist()
def save_results(
	name: str,
	normal: list | str | None = None,
	descriptive: list | str | None = None,
	complete: int = 0,
	is_critical: int = 0,
	conclusion: str | None = None,
) -> dict:
	"""Write result values into the Lab Test child rows.

	`complete=1` submits the test (Marley validates required results and sets
	status → Completed) and ensures a Diagnostic Report exists to verify.
	`is_critical`/`conclusion` are carried onto that Diagnostic Report.
	"""
	doc = frappe.get_doc("Lab Test", name)
	if doc.docstatus == 1:
		frappe.throw("Results are already finalised for this test.")

	nmap = {r["name"]: r for r in (json.loads(normal) if isinstance(normal, str) else (normal or []))}
	dmap = {r["name"]: r for r in (json.loads(descriptive) if isinstance(descriptive, str) else (descriptive or []))}

	for row in doc.normal_test_items:
		if row.name in nmap:
			row.result_value = nmap[row.name].get("result_value")
			if "lab_test_comment" in nmap[row.name]:
				row.lab_test_comment = nmap[row.name].get("lab_test_comment")
	for row in doc.descriptive_test_items:
		if row.name in dmap:
			row.result_value = dmap[row.name].get("result_value")

	if int(complete or 0):
		_allow_blanks(doc)
	doc.save(ignore_permissions=False)

	report = None
	if int(complete or 0):
		doc.submit()  # Marley on_submit: validate results + status → Completed
		report = _ensure_diagnostic_report(doc, is_critical=int(is_critical or 0), conclusion=conclusion)

	return {"ok": True, "name": doc.name, "status": doc.status, "docstatus": doc.docstatus, "report": report}


@frappe.whitelist()
def approve_report(
	report: str,
	conclusion: str | None = None,
	signature: str | None = None,
	diagnosis: str | None = None,
	clinical_notes: str | None = None,
	pathologist_remarks: str | None = None,
	accreditation_type: str | None = None,
	pathologist_signature: str | None = None,
	pathologist_name: str | None = None,
	has_image_space: int = 0,
) -> dict:
	"""Verify & release a Diagnostic Report (status → Approved) with the full
	sign-off: clinical notes / diagnosis / remarks / accreditation and both the
	technologist and pathologist signatures (data-URL PNGs)."""
	doc = frappe.get_doc("Diagnostic Report", report)
	fns = {df.fieldname for df in doc.meta.fields}

	# Urgent gate: an urgent report can't be released until an Urgent Review
	# Officer has authorized it. Enforced server-side (not just hidden in the UI).
	if "is_urgent" in fns and doc.get("is_urgent") and doc.get("urgent_review_status") != "Authorized":
		frappe.throw(
			"This is an URGENT case. An Urgent Review Officer must authorize it before it can be Verified & Released.",
			title="Urgent Review Required",
		)

	doc.db_set("status", "Approved")

	def setf(field, value):
		if value is not None and field in fns:
			doc.db_set(field, value)

	if conclusion is not None and "conclusion" in fns:
		doc.db_set("conclusion", conclusion)
	setf("diagnosis", diagnosis)
	setf("clinical_notes", clinical_notes)
	setf("pathologist_remarks", pathologist_remarks)
	setf("accreditation_type", accreditation_type)
	setf("report_signature", signature)
	setf("pathologist_signature", pathologist_signature)
	setf("pathologist_name", pathologist_name)
	if "signed_by" in fns:
		doc.db_set("signed_by", frappe.session.user)
	doc.add_comment("Comment", text=f"<b>Verified &amp; Released</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")

	# Build the printable Lab Report (genetest doctype) for this sample.
	lab_report = None
	sample = doc.get("sample_collection")
	if sample:
		lab_report = _build_lab_report(sample, {
			"status": "Approved",
			"diagnosis": diagnosis,
			"clinical_notes": clinical_notes,
			"pathologist_remarks": pathologist_remarks,
			"accreditation_type": accreditation_type,
			"pathologist_name": pathologist_name,
			"signature": signature,
			"pathologist_signature": pathologist_signature,
			"has_image_space": 1 if int(has_image_space or 0) else 0,
		})
	return {"ok": True, "report": report, "status": "Approved", "lab_report": lab_report}


@frappe.whitelist()
def authorize_urgent_review(sample: str) -> dict:
	"""An Urgent Review Officer authorizes an urgent sample's report so it can be
	Verified & Released. Only that role may call this; enforced server-side."""
	if URGENT_REVIEW_ROLE not in frappe.get_roles():
		frappe.throw(
			f"Only an {URGENT_REVIEW_ROLE} can authorize urgent reviews.",
			frappe.PermissionError,
			title="Not Permitted",
		)
	report = _report_for_sample(sample)
	if not report:
		frappe.throw("No report exists for this sample yet. Complete the results first.")
	fns = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	updates = {}
	if "urgent_review_status" in fns:
		updates["urgent_review_status"] = "Authorized"
	if "urgent_reviewed_by" in fns:
		updates["urgent_reviewed_by"] = frappe.session.user
	if "urgent_reviewed_at" in fns:
		updates["urgent_reviewed_at"] = frappe.utils.now_datetime()
	if updates:
		frappe.db.set_value("Diagnostic Report", report, updates)
	doc = frappe.get_doc("Diagnostic Report", report)
	doc.add_comment("Comment", text=f"<b>Urgent Review Authorized</b><br>By: {frappe.utils.escape_html(frappe.session.user)}")
	return {"ok": True, "report": report, "urgent_review_status": "Authorized", "urgent_reviewed_by": frappe.session.user}


@frappe.whitelist()
def lab_report_for_sample(sample: str) -> str | None:
	"""Existing Lab Report for the sample, building one if needed (for printing)."""
	existing = frappe.db.get_value("Lab Report Sample", {"lab_sample": sample}, "parent")
	if existing and frappe.db.exists("Lab Report", existing):
		return existing
	return _build_lab_report(sample, {"status": "Approved"})


def _build_lab_report(sample: str, signoff: dict | None = None) -> str | None:
	"""Create/refresh a Lab Report (genetest doctype) from a Sample Collection's
	Lab Tests + results, so the verbatim genetest print format renders."""
	from frappe.utils import today

	from diagnostic_management.utils.formatters import result_flag

	signoff = signoff or {}
	if not frappe.db.exists("Sample Collection", sample):
		return None
	sc = frappe.get_doc("Sample Collection", sample)
	existing = frappe.db.get_value("Lab Report Sample", {"lab_sample": sample}, "parent")
	lr = frappe.get_doc("Lab Report", existing) if existing and frappe.db.exists("Lab Report", existing) else frappe.new_doc("Lab Report")
	fns = {df.fieldname for df in lr.meta.fields}

	def setf(field, value):
		if field in fns and value is not None:
			lr.set(field, value)

	lr.report_date = today()
	status_opts = (lr.meta.get_field("status").options or "").split("\n") if lr.meta.get_field("status") else []
	desired = signoff.get("status") or "Approved"
	lr.status = desired if desired in status_opts else (status_opts[0] if status_opts else desired)
	lr.patient = sc.patient
	setf("patient_name", sc.get("patient_name"))
	setf("collection_datetime", sc.get("collected_time"))

	for tbl in ["lab_report_tests", "numeric_results", "descriptive_results", "grouped_results", "qualitative_results", "samples"]:
		if tbl in fns:
			lr.set(tbl, [])
	if "samples" in fns:
		lr.append("samples", {"lab_sample": sample, "sample_type": sc.get("sample"), "collection_datetime": sc.get("collected_time")})

	# Build the report from the CURRENT batch only. Prefer the explicit list
	# stored on the DR by save_sample (`custom_lab_tests_csv` — this workflow's
	# submissions); fall back to a 30-minute window around the most recent
	# Lab Test on the sample if the field isn't populated.
	existing_dr_for_sample = _report_for_sample(sample)
	csv_names = None
	if existing_dr_for_sample:
		csv_names = frappe.db.get_value("Diagnostic Report", existing_dr_for_sample, "custom_lab_tests_csv")
	if csv_names:
		current_lt_names = [n.strip() for n in csv_names.split(",") if n.strip() and frappe.db.exists("Lab Test", n.strip())]
	else:
		latest_creation = frappe.db.get_value(
			"Lab Test", {"sample": sample, "docstatus": 1},
			"creation", order_by="creation desc",
		)
		if not latest_creation:
			current_lt_names = []
		else:
			threshold = frappe.utils.add_to_date(latest_creation, minutes=-30)
			current_lt_names = frappe.get_all(
				"Lab Test",
				filters={"sample": sample, "docstatus": 1, "creation": [">=", threshold]},
				order_by="creation asc",
				pluck="name",
			)
	for lt_name in current_lt_names:
		lt = frappe.get_doc("Lab Test", lt_name)
		ttype = frappe.db.get_value("Lab Test Template", lt.template, "lab_test_template_type") or "Single"
		from diagnostic_management.utils.reference_ranges import pick_reference_range
		for r in lt.normal_test_items:
			analyte = r.lab_test_name or r.lab_test_event
			picked = pick_reference_range(lt.template, analyte, lt.patient)
			rng = (picked["range_text"] if picked else None) or r.normal_range
			uom = (picked["uom"] if picked else None) or r.lab_test_uom
			# Flagging respects the analyte's result_type. Numeric (default) uses
			# the bounds parser → High/Low/Normal. For Select and Data types we
			# treat any value that doesn't case-insensitively match the configured
			# "normal" range as Abnormal (e.g. result Positive vs reference Negative).
			rtype = (picked["result_type"] if picked else None) or "Numeric"
			flag = ""
			abnormal = 0
			val = (r.result_value or "").strip()
			ref = (rng or "").strip()
			if val:
				if rtype == "Numeric":
					flag = result_flag(val, rng)
					abnormal = 1 if flag in ("High", "Low") else 0
				elif rtype in ("Select", "Data"):
					# `status` is a strict Select on the child (Normal/High/Low/Critical),
					# so we leave it blank for qualitative mismatches and rely on
					# `is_abnormal` for row highlighting on the printed report.
					if ref and val.lower() != ref.lower():
						abnormal = 1
					elif ref:
						flag = "Normal"
			row = {
				"lab_test": lt.name,
				"test_name": analyte,
				"test_category": lt.template,
				"result_value": r.result_value,
				"uom": uom,
				"reference_range": rng,
				"status": flag,
				"is_abnormal": abnormal,
			}
			if ttype == "Grouped" and "grouped_results" in fns:
				lr.append("grouped_results", {**row, "group_name": lt.template})
			elif ttype == "Compound" and "numeric_results" in fns:
				lr.append("numeric_results", row)
			elif "lab_report_tests" in fns:
				lr.append("lab_report_tests", row)
		for r in lt.descriptive_test_items:
			if "descriptive_results" in fns:
				lr.append("descriptive_results", {"lab_test": lt.name, "test_name": r.lab_test_particulars, "test_category": lt.template, "result_value": r.result_value})

	setf("diagnosis", signoff.get("diagnosis"))
	setf("clinical_notes", signoff.get("clinical_notes"))
	setf("pathologist_remarks", signoff.get("pathologist_remarks"))
	setf("accreditation_type", signoff.get("accreditation_type"))
	setf("pathologist_name", signoff.get("pathologist_name"))
	setf("lab_technician_signature", signoff.get("signature"))
	setf("pathologist_signature", signoff.get("pathologist_signature"))
	# Carry the "include blank box on print" decision onto the Lab Report doc
	# so the print HTML conditional fires the way the user picked at release.
	setf("custom_has_image_space", 1 if signoff.get("has_image_space") else 0)

	lr.flags.ignore_permissions = True
	lr.save()
	return lr.name


def _ensure_diagnostic_report(lab_test, is_critical: int = 0, conclusion: str | None = None) -> str | None:
	"""Best-effort: a Diagnostic Report for this test so it lands in verification."""
	if not frappe.db.exists("DocType", "Diagnostic Report"):
		return None
	existing = frappe.db.get_value(
		"Diagnostic Report", {"ref_doctype": "Lab Test", "docname": lab_test.name}, "name"
	)
	if existing:
		fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
		updates = {}
		if "is_critical" in fields and is_critical:
			updates["is_critical"] = 1
		if "conclusion" in fields and conclusion:
			updates["conclusion"] = conclusion
		if updates:
			frappe.db.set_value("Diagnostic Report", existing, updates)
		return existing
	try:
		payload = {
			"doctype": "Diagnostic Report",
			"patient": lab_test.patient,
			"ref_doctype": "Lab Test",
			"docname": lab_test.name,
			"company": lab_test.get("company"),
			"practitioner": lab_test.get("practitioner"),
			"status": "Pending Review",
		}
		meta_fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
		if "is_critical" in meta_fields and is_critical:
			payload["is_critical"] = 1
		if "conclusion" in meta_fields and conclusion:
			payload["conclusion"] = conclusion
		dr = frappe.get_doc(payload)
		dr.insert(ignore_permissions=True)
		return dr.name
	except Exception:
		frappe.log_error(title="results._ensure_diagnostic_report failed")
		return None
