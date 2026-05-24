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
	"""Shape one Lab Test's expanded result rows for the entry UI."""
	return {
		"name": doc.name,
		"template": doc.template,
		"status": doc.status,
		"docstatus": doc.docstatus,
		"normal_test_items": [
			{
				"name": r.name, "idx": r.idx,
				"lab_test_name": r.lab_test_name or r.lab_test_event,
				"result_value": r.result_value,
				"normal_range": r.normal_range,
				"lab_test_uom": r.lab_test_uom,
				"lab_test_comment": r.lab_test_comment,
			}
			for r in doc.normal_test_items
		],
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
	return {
		"sample": sample,
		"patient": sc.get("patient"),
		"patient_name": sc.get("patient_name"),
		"sample_type": sc.get("sample"),
		"lab_tests": [_lab_test_rows(frappe.get_doc("Lab Test", n)) for n in lab_tests],
	}


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
	if existing:
		updates = {}
		if "is_critical" in fields and is_critical:
			updates["is_critical"] = 1
		if "conclusion" in fields and conclusion:
			updates["conclusion"] = conclusion
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
		dr = frappe.get_doc(payload)
		dr.insert(ignore_permissions=True)
		return dr.name
	except Exception:
		frappe.log_error(title="results._ensure_sample_report failed")
		return None


@frappe.whitelist()
def get_lab_test(name: str) -> dict:
	"""Return a Lab Test with its expanded result rows for the entry screen."""
	doc = frappe.get_doc("Lab Test", name)
	return {
		"name": doc.name,
		"patient": doc.patient,
		"patient_name": doc.get("patient_name"),
		"template": doc.template,
		"status": doc.status,
		"docstatus": doc.docstatus,
		"practitioner": doc.get("practitioner"),
		"normal_test_items": [
			{
				"name": r.name, "idx": r.idx,
				"lab_test_name": r.lab_test_name or r.lab_test_event,
				"result_value": r.result_value,
				"normal_range": r.normal_range,
				"lab_test_uom": r.lab_test_uom,
				"lab_test_comment": r.lab_test_comment,
				"allow_blank": r.allow_blank,
				"require_result_value": r.require_result_value,
			}
			for r in doc.normal_test_items
		],
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
) -> dict:
	"""Verify & release a Diagnostic Report (status → Approved) with the full
	sign-off: clinical notes / diagnosis / remarks / accreditation and both the
	technologist and pathologist signatures (data-URL PNGs)."""
	doc = frappe.get_doc("Diagnostic Report", report)
	fns = {df.fieldname for df in doc.meta.fields}
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
		})
	return {"ok": True, "report": report, "status": "Approved", "lab_report": lab_report}


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

	for lt_name in frappe.get_all("Lab Test", filters={"sample": sample}, order_by="creation", pluck="name"):
		lt = frappe.get_doc("Lab Test", lt_name)
		ttype = frappe.db.get_value("Lab Test Template", lt.template, "lab_test_template_type") or "Single"
		for r in lt.normal_test_items:
			flag = result_flag(r.result_value, r.normal_range)
			row = {
				"lab_test": lt.name,
				"test_name": r.lab_test_name or r.lab_test_event,
				"test_category": lt.template,
				"result_value": r.result_value,
				"uom": r.lab_test_uom,
				"reference_range": r.normal_range,
				"status": flag,
				"is_abnormal": 1 if flag in ("High", "Low") else 0,
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
