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
	"""A sample is urgent ONLY when the Sample Collection is explicitly
	flagged `is_urgent=1` (the "Mark as Urgent" toggle in Billing).

	We used to also scan every Service Request behind this sample for an
	Urgent/STAT priority, but that made the sample stay urgent forever if
	ANY historical order in its lifetime was ever marked urgent — even
	after re-billing without the flag. The Sample Collection's own
	`is_urgent` is the authoritative signal for the current run.
	"""
	return bool(frappe.db.get_value("Sample Collection", sample, "is_urgent"))


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


def _infer_result_type(picked: dict | None, tmpl_row: dict | None, row_normal_range: str | None) -> str:
	"""Fallback result_type when the template + reference-range picker BOTH
	leave `custom_result_type` blank.

	Rule: `Numeric` requires *some* numeric context — an ADMS picker range,
	the child template's numeric bounds, or free-text `normal_range` that
	parses. Otherwise the analyte is free-text (`Data`). Rendering a number
	spinner for an analyte with no reference range (e.g. Peripheral Blood
	Film's RBC/WBC observations, or a COMMENT field) is worse than a plain
	text box — the user has no signal that a number is even expected.

	Never returns `""` — the frontend switches its widget on this string.
	"""
	if picked and picked.get("range_text"):
		return "Numeric"
	if tmpl_row:
		if tmpl_row.get("synth_range"):
			return "Numeric"
		if tmpl_row.get("normal_range") and str(tmpl_row.get("normal_range")).strip():
			return "Numeric"
	if row_normal_range and str(row_normal_range).strip():
		return "Numeric"
	return "Data"


def _template_analyte_row(template: str | None, analyte: str | None) -> dict | None:
	"""Source `custom_result_type` / `custom_result_options` for this analyte,
	regardless of whether the template is Single or Compound. Also synthesizes
	a `synth_range` from custom_low_range / custom_upper_range when the
	template stores its bounds as separate numeric fields rather than the
	`lab_test_normal_range` text (Vitamin C-style templates do this).

	Compound templates carry per-analyte config on `normal_test_templates`
	child rows. Single templates carry it on the template DOC ITSELF.
	"""
	if not template or not analyte:
		return None
	clean = analyte.strip()
	rows = frappe.get_all(
		"Normal Test Template",
		filters={"parent": template, "parenttype": "Lab Test Template"},
		fields=["lab_test_event", "custom_result_type", "custom_result_options",
		        "custom_low_range_adult", "custom_upper_range_adult",
		        "custom_low_range_child", "custom_upper_range_child",
		        "normal_range", "lab_test_uom"],
	)
	for row in rows:
		if (row.get("lab_test_event") or "").strip() == clean:
			row["synth_range"] = _synth_range_from_bounds(
				row.get("custom_low_range_adult"),
				row.get("custom_upper_range_adult"),
			) or _synth_range_from_bounds(
				row.get("custom_low_range_child"),
				row.get("custom_upper_range_child"),
			)
			return row
	# Single template — one analyte per template, config lives on the parent.
	tmpl = frappe.db.get_value(
		"Lab Test Template", template,
		["lab_test_name", "custom_result_type", "custom_result_options",
		 "custom_low_range", "custom_upper_range",
		 "lab_test_normal_range", "lab_test_uom"],
		as_dict=True,
	)
	if not tmpl:
		return None
	synth = _synth_range_from_bounds(
		tmpl.get("custom_low_range"), tmpl.get("custom_upper_range"),
	)
	if (tmpl.get("custom_result_type") or tmpl.get("custom_result_options") or synth):
		return {
			"lab_test_event": tmpl.get("lab_test_name"),
			"custom_result_type": tmpl.get("custom_result_type"),
			"custom_result_options": tmpl.get("custom_result_options"),
			"synth_range": synth,
			"lab_test_uom": tmpl.get("lab_test_uom"),
		}
	return None


def _synth_range_from_bounds(low, high) -> str | None:
	"""Build a "low - high" range string from a template's numeric bounds.
	Returns None if neither bound is set / meaningful (0.0 counts as unset
	because that's Frappe's default for a Float when nothing was entered).
	"""
	try:
		lo = float(low) if low not in (None, "", 0) else None
		hi = float(high) if high not in (None, "", 0) else None
	except (TypeError, ValueError):
		return None
	if lo is None and hi is None:
		return None
	if lo is not None and hi is not None:
		# Trim trailing .0 for a cleaner "4 - 15" instead of "4.0 - 15.0".
		def _fmt(x): return str(int(x)) if float(x).is_integer() else str(x)
		return f"{_fmt(lo)} - {_fmt(hi)}"
	if hi is not None:
		return f"< {hi}"
	return f"> {lo}"


def _lab_test_rows(doc) -> dict:
	"""Shape one Lab Test's expanded result rows for the entry UI. Each
	normal-test row is overlaid with the reference range / UoM that matches
	THIS patient (via the template's ADMS Reference Range child table). Empty
	overlay → fall back to Marley's row-level normal_range / lab_test_uom."""
	from diagnostic_management.utils.reference_ranges import pick_reference_range
	normal = []
	for r in doc.normal_test_items:
		analyte = r.lab_test_name or r.lab_test_event
		# For Grouped Lab Tests, `doc.template` is the WRAPPER (e.g. "Liver
		# Function Test, Male") and has no ranges — the ranges live on the
		# CHILD template (e.g. "ALP (ALKALINE PHOSPHATASE)"). Frappe
		# Healthcare's create_normals / create_compounds stamps the sub-
		# template's name onto each `normal_test_items` row's `.template`
		# field. Prefer that; fall back to the outer template so Single /
		# Compound Lab Tests (where the two are the same) keep working.
		range_template = r.get("template") or doc.template
		picked = pick_reference_range(range_template, analyte, doc.patient)
		# result_type / result_options priority:
		#   1. Template's `normal_test_templates` row — AUTHORITATIVE for
		#      widget type (Numeric / Select / Data), because that's where
		#      the lab configures how an analyte is entered.
		#   2. Reference-range row (if it set them) — patient-scoped override.
		#   3. Default to Numeric.
		# The backfill that populated ADMS Reference Range rows stamped
		# result_type='Numeric' by default even for Select analytes like
		# Nitrite / Glucose, so trusting the ADMS row first led the SPA to
		# render a number input for a dropdown field. The template row is
		# the source of truth.
		tmpl_row = _template_analyte_row(range_template, analyte)
		rtype = None
		ropts = None
		if tmpl_row:
			rtype = tmpl_row.get("custom_result_type")
			ropts = tmpl_row.get("custom_result_options")
		if not rtype and picked:
			rtype = picked.get("result_type")
		if not ropts and picked:
			ropts = picked.get("result_options")
		# Fallback when the template AND picker both leave `custom_result_type`
		# blank: infer from whether there's ANY numeric context (a range text,
		# a numeric-bounds synth, or a picker range). If yes → Numeric. If
		# nothing numeric → Data (free text), because rendering a spinner for
		# an analyte with no range (e.g. Peripheral Blood Film's RBC/WBC/PLT
		# observations, or a COMMENT field) is worse than a plain text box.
		rtype = rtype or _infer_result_type(picked, tmpl_row, r.normal_range)
		# Status: RECOMPUTE from the current range for Numeric analytes so
		# old rows saved with a stale "Normal" (either the frontend default
		# or entered before autoUpdateStatus shipped) get corrected on
		# every read. Only override when the range parses to something
		# definitive — otherwise keep whatever the tech picked.
		stored_status = r.get("status") or "Normal"
		# Range fallback chain: ADMS picker → row-level normal_range →
		# template's custom_low_range/custom_upper_range (synth). Fixes
		# Vitamin C-style templates where bounds live as separate numeric
		# fields on the template doc instead of the range text.
		effective_range = (
			(picked["range_text"] if picked else None)
			or r.normal_range
			or (tmpl_row.get("synth_range") if tmpl_row else None)
		)
		derived_status = stored_status
		if (rtype or "Numeric") == "Numeric":
			from diagnostic_management.utils.formatters import banded_flag, result_flag
			# Banded interpretation first (HbA1c → Pre-diabetic / Diabetic;
			# ACR → Normal / Microalbuminuria / Macroalbuminuria). Uses the
			# TEMPLATE's raw multi-line `normal_range` since ADMS Reference
			# Range picker collapses it to a single-band summary.
			band_source = (tmpl_row.get("normal_range") if tmpl_row else None) or effective_range
			bflag = banded_flag(r.result_value, band_source)
			flag = bflag or result_flag(r.result_value, effective_range)
			if flag:  # ""=couldn't derive → don't touch stored value
				derived_status = flag
		normal.append({
			"name": r.name, "idx": r.idx,
			"lab_test_name": analyte,
			"result_value": r.result_value,
			"normal_range": effective_range,
			"lab_test_uom": (picked["uom"] if picked else None) or r.lab_test_uom,
			"lab_test_comment": r.lab_test_comment,
			"status": derived_status,
			"result_type": rtype or "Numeric",
			"result_options": ropts or "",
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
def get_sample(sample: str, session_id: str | None = None,
                sales_invoice: str | None = None) -> dict:
	"""Sample-centric results payload — the Sample Collection + the Lab Tests
	**of the current workflow batch** on it.

	**Filter precedence (which Lab Tests are 'this batch'):**

	1. Explicit `sales_invoice` — scope to Lab Tests stamped with this SI.
	   This is the authoritative link (every Lab Test created from billing
	   carries `custom_sales_invoice`), and the SPA passes this when it
	   knows which invoice opened the workflow.
	2. `session_id` — derive the session's Service Requests, then walk
	   those orders' Lab Tests. Equivalent scope, used when the SPA only
	   has the session handle.
	3. Otherwise — fall back to Draft (docstatus=0) Lab Tests so historical
	   submitted tests from past visits don't leak in.

	**Why this matters.** Marley reuses one Sample Collection across every
	visit for a patient + sample type — without scoping, every historical
	Lab Test from past orders shows up in the Results screen.

	`previous_tests_count` reports how many Lab Tests on this sample are
	NOT in the current scope, so the UI can show a hint like "8 previous
	tests on this sample (from earlier visits)".
	"""
	sc = frappe.db.get_value(
		"Sample Collection", sample,
		["patient", "patient_name", "sample", "custom_sales_invoice"], as_dict=True,
	) or {}
	# Fall back to the sample's own stamp when the caller didn't pass an SI.
	if not sales_invoice:
		sales_invoice = sc.get("custom_sales_invoice") or None

	from diagnostic_management.api.collection_workflow import _session_orders
	session_orders: list[str] = []
	if session_id and frappe.db.exists("Lab Workflow Session", session_id):
		session_orders = _session_orders(session_id)

	lt_filters: dict = {"sample": sample}
	if sales_invoice:
		# Authoritative: filter Lab Tests by the SI link directly.
		lt_filters["custom_sales_invoice"] = sales_invoice
	elif session_orders:
		# Equivalent scope via the session's Service Requests.
		lt_filters["service_request"] = ["in", session_orders]
	else:
		# No batch context → only Draft tests.
		lt_filters["docstatus"] = 0
	# Never surface CANCELLED (docstatus=2) Lab Tests, even when the SI
	# filter matches them. The legacy peer-review amend flow left the
	# original doc cancelled alongside a new -1 draft — showing both
	# produced the "two copies per test" duplication users reported.
	if lt_filters.get("docstatus") != 0:
		lt_filters["docstatus"] = ["<", 2]
	lab_tests = frappe.get_all(
		"Lab Test", filters=lt_filters,
		order_by="creation", pluck="name",
	)
	# Count of Lab Tests on this sample NOT in the current scope.
	total_on_sample = frappe.db.count("Lab Test", {"sample": sample})
	previous_tests_count = max(0, int(total_on_sample) - len(lab_tests))

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
		"previous_tests_count": int(previous_tests_count),
		"sales_invoice": sales_invoice or None,
		"session_id": session_id or None,
		"session_orders": session_orders,
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


def _apply_result_corrections(
	doc,
	nmap: dict,
	dmap: dict,
	smap: dict | None = None,
	omap: dict | None = None,
) -> None:
	"""Write result mutations onto an already-SUBMITTED Lab Test across ALL
	four result child tables:

	  * Normal Test Result       — numeric/range analytes (Chemistry, Haem)
	  * Descriptive Test Result  — free-text narratives (Histology)
	  * Sensitivity Test Result  — Microbiology antibiotic sensitivities
	  * Organism Test Result     — Microbiology organism ID + colony count

	Each row whose incoming payload differs from what's on disk gets a
	`db.set_value` write (bypasses docstatus lock — the mutable fields are
	allow_on_submit, see setup._allow_result_edit_after_submit) and a
	change line in a single audit Comment on the parent Lab Test. Rows
	that weren't sent, or were sent with an unchanged value, are noops.
	"""
	smap = smap or {}
	omap = omap or {}
	changes: list[str] = []

	def _esc(v):
		return frappe.utils.escape_html(str(v or ""))

	def _diff(label: str, before, after) -> str:
		return f"{_esc(label)}: <code>{_esc(before)}</code> → <code>{_esc(after)}</code>"

	# Normal Test Result — track value / status / comment.
	for row in doc.normal_test_items:
		if row.name not in nmap:
			continue
		src = nmap[row.name]
		updates: dict = {}
		for field, before in (
			("result_value",      row.result_value),
			("status",            row.status),
			("lab_test_comment",  row.lab_test_comment),
		):
			if field not in src:
				continue
			after = src.get(field)
			if (before or "") == (after or ""):
				continue
			updates[field] = after
			if field == "result_value":
				changes.append(_diff(
					row.lab_test_name or row.lab_test_event or row.name,
					before, after,
				))
		if updates:
			frappe.db.set_value("Normal Test Result", row.name, updates,
			                    update_modified=False)

	# Descriptive Test Result — track value only.
	for row in doc.descriptive_test_items:
		if row.name not in dmap:
			continue
		after = dmap[row.name].get("result_value")
		before = row.result_value
		if (before or "") == (after or ""):
			continue
		frappe.db.set_value("Descriptive Test Result", row.name,
		                    "result_value", after, update_modified=False)
		changes.append(_diff(row.lab_test_particulars or row.name, before, after))

	# Sensitivity Test Result — Microbiology (antibiotic + susceptibility).
	for row in getattr(doc, "sensitivity_test_items", []) or []:
		if row.name not in smap:
			continue
		src = smap[row.name]
		updates = {}
		for field, before in (
			("antibiotic",              row.antibiotic),
			("antibiotic_sensitivity",  row.antibiotic_sensitivity),
		):
			if field not in src:
				continue
			after = src.get(field)
			if (before or "") == (after or ""):
				continue
			updates[field] = after
			changes.append(_diff(f"{row.antibiotic or row.name} · {field}", before, after))
		if updates:
			frappe.db.set_value("Sensitivity Test Result", row.name, updates,
			                    update_modified=False)

	# Organism Test Result — Microbiology (organism + colony count).
	for row in getattr(doc, "organism_test_items", []) or []:
		if row.name not in omap:
			continue
		src = omap[row.name]
		updates = {}
		for field, before in (
			("organism",          row.organism),
			("colony_population", row.colony_population),
			("colony_uom",        row.colony_uom),
		):
			if field not in src:
				continue
			after = src.get(field)
			if (before or "") == (after or ""):
				continue
			updates[field] = after
			changes.append(_diff(f"{row.organism or row.name} · {field}", before, after))
		if updates:
			frappe.db.set_value("Organism Test Result", row.name, updates,
			                    update_modified=False)

	if changes:
		# One Comment per save carries every field change made in this call.
		# Keeps the timeline compact and matches how a reviewer would think
		# about the correction ("this save fixed X and Y").
		doc.add_comment(
			"Comment",
			text=(
				"<b>Results corrected in place</b><br>"
				f"By: {_esc(frappe.session.user)}<br>"
				+ "<br>".join(changes)
			),
		)


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
		nmap = {r["name"]: r for r in (t.get("normal") or [])}
		dmap = {r["name"]: r for r in (t.get("descriptive") or [])}
		# Microbiology payloads — optional keys; SPA doesn't send them today
		# but the plumbing is here so any future Sensitivity/Organism editor
		# (or a Desk-side save) uses the same audit-logged edit path.
		smap = {r["name"]: r for r in (t.get("sensitivity") or [])}
		omap = {r["name"]: r for r in (t.get("organism") or [])}

		# Peer-review correction path: the Lab Test may already be SUBMITTED
		# (docstatus=1) — e.g. the reviewer sent it back with "Send Back for
		# Correction" and the tech is now editing the numbers in place. The
		# result fields are allow_on_submit (see setup._allow_result_edit_after_submit),
		# so we mutate them directly via db.set_value (bypasses docstatus lock
		# on child rows) and audit-log each change as a Comment on the Lab
		# Test. `complete` is ignored on this branch — the doc stays submitted.
		if doc.docstatus == 1:
			_apply_result_corrections(doc, nmap, dmap, smap, omap)
			continue

		for row in doc.normal_test_items:
			if row.name in nmap:
				row.result_value = nmap[row.name].get("result_value")
				if "lab_test_comment" in nmap[row.name]:
					row.lab_test_comment = nmap[row.name].get("lab_test_comment")
				if "status" in nmap[row.name]:
					row.status = nmap[row.name].get("status")
		for row in doc.descriptive_test_items:
			if row.name in dmap:
				row.result_value = dmap[row.name].get("result_value")
		# Sensitivity / Organism child rows — draft path. Same optional-key
		# contract as the correction branch above; only fields present in the
		# payload get written, everything else is left alone.
		for row in getattr(doc, "sensitivity_test_items", []) or []:
			if row.name in smap:
				src = smap[row.name]
				if "antibiotic" in src:
					row.antibiotic = src.get("antibiotic")
				if "antibiotic_sensitivity" in src:
					row.antibiotic_sensitivity = src.get("antibiotic_sensitivity")
		for row in getattr(doc, "organism_test_items", []) or []:
			if row.name in omap:
				src = omap[row.name]
				if "organism" in src:
					row.organism = src.get("organism")
				if "colony_population" in src:
					row.colony_population = src.get("colony_population")
				if "colony_uom" in src:
					row.colony_uom = src.get("colony_uom")
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
		elif "is_urgent" in fields and not urgent:
			# Sample is NOT urgent — sync the DR back to non-urgent and clear any
			# stale urgent-review fields. Without this, a DR that was once flagged
			# urgent (e.g. by earlier historical-Service-Request scanning before
			# `_sample_is_urgent` was tightened) keeps triggering the URGENT gate
			# in `approve_report` even though the sample itself is routine.
			updates["is_urgent"] = 0
			if "urgent_review_status" in fields:
				updates["urgent_review_status"] = None
			if "urgent_reviewed_by" in fields:
				updates["urgent_reviewed_by"] = None
			if "urgent_reviewed_at" in fields:
				updates["urgent_reviewed_at"] = None
		# Stamp the "reporting completed" timestamp every time results are
		# saved & completed. This is the moment to use for TAT reporting —
		# `creation` is when the DR was first opened, not when results
		# actually came in.
		if "custom_reporting_completed_at" in fields:
			updates["custom_reporting_completed_at"] = frappe.utils.now_datetime()
		if updates:
			frappe.db.set_value("Diagnostic Report", existing, updates)
		# Peer review case: ensure one exists as an Open case for this DR.
		# Called on every Save & Complete because we may have created the DR
		# on an earlier partial save; the reviewer needs a case to close.
		_ensure_open_peer_review_case_for_dr(existing)
		return existing
	try:
		payload = {"doctype": "Diagnostic Report", "patient": sc.get("patient"), "status": "Pending Review"}
		if "custom_reporting_completed_at" in fields:
			payload["custom_reporting_completed_at"] = frappe.utils.now_datetime()
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
		# Peer review case attached to the freshly-created DR.
		_ensure_open_peer_review_case_for_dr(dr.name)
		return dr.name
	except Exception:
		frappe.log_error(title="results._ensure_sample_report failed")


def _ensure_open_peer_review_case_for_dr(dr_name: str) -> str | None:
	"""Shim that calls into api.lab's _ensure_open_peer_review_case. Kept
	here so results.py doesn't have to fetch the DR just to hand it back."""
	if not dr_name or not frappe.db.exists("Diagnostic Report", dr_name):
		return None
	try:
		from diagnostic_management.api.lab import _ensure_open_peer_review_case
		return _ensure_open_peer_review_case(frappe.get_doc("Diagnostic Report", dr_name))
	except Exception:
		frappe.log_error(title="results._ensure_open_peer_review_case_for_dr failed")
		return None
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
		# See _shape_test — Grouped Lab Tests need the child row's own template.
		range_template = r.get("template") or doc.template
		picked = pick_reference_range(range_template, analyte, doc.patient)
		# Same result_type fallback ladder as _shape_test — see docstring there.
		rtype = picked["result_type"] if picked else None
		ropts = picked["result_options"] if picked else None
		# Always fetch tmpl_row — banded flagging below needs its raw
		# `normal_range` text regardless of whether rtype/ropts already
		# came from the picker.
		tmpl_row = _template_analyte_row(range_template, analyte)
		if tmpl_row:
			rtype = rtype or tmpl_row.get("custom_result_type")
			ropts = ropts or tmpl_row.get("custom_result_options")
		# Same fallback rule as _lab_test_rows — no explicit type +
		# no numeric context → Data (free text), not Numeric.
		rtype = rtype or _infer_result_type(picked, tmpl_row, r.normal_range)
		# See _lab_test_rows — recompute Numeric status so stale "Normal"
		# defaults get corrected on every read.
		stored_status = r.get("status") or "Normal"
		effective_range = (picked["range_text"] if picked else None) or r.normal_range
		derived_status = stored_status
		if (rtype or "Numeric") == "Numeric":
			from diagnostic_management.utils.formatters import banded_flag, result_flag
			# See _lab_test_rows — banded first (HbA1c / ACR), numeric fallback.
			band_source = (tmpl_row.get("normal_range") if tmpl_row else None) or effective_range
			bflag = banded_flag(r.result_value, band_source)
			flag = bflag or result_flag(r.result_value, effective_range)
			if flag:
				derived_status = flag
		normal.append({
			"name": r.name, "idx": r.idx,
			"lab_test_name": analyte,
			"result_value": r.result_value,
			"normal_range": effective_range,
			"lab_test_uom": (picked["uom"] if picked else None) or r.lab_test_uom,
			"lab_test_comment": r.lab_test_comment,
			"status": derived_status,
			"allow_blank": r.allow_blank,
			"require_result_value": r.require_result_value,
			"result_type": rtype or "Numeric",
			"result_options": ropts or "",
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
	image_space_image: str | None = None,
	hide_graphs: int = 0,
	session: str | None = None,
) -> dict:
	"""Verify & release a Diagnostic Report (status → Approved) with the full
	sign-off: clinical notes / diagnosis / remarks / accreditation and both the
	technologist and pathologist signatures (data-URL PNGs).

	`session` (the workflow visit) binds the built Lab Report to this visit, so a
	returning patient on the same reused sample gets a fresh report, not the old
	one. See _build_lab_report / _existing_report_for."""
	doc = frappe.get_doc("Diagnostic Report", report)
	fns = {df.fieldname for df in doc.meta.fields}

	# Peer review gate: EVERY report (urgent or not) must have a closed peer
	# review case with an accepting outcome (Agree / Minor Disagreement) before
	# it can be released. The `custom_peer_reviewed` flag is flipped to 1 by
	# `api.lab.submit_peer_review`. The frontend hides the button, but this
	# server-side gate is the source of truth — the frontend also calls this
	# endpoint (`results.approve_report`), not `lab.verify_report`, so the
	# check must live here too.
	if "custom_peer_reviewed" in fns and not doc.get("custom_peer_reviewed"):
		frappe.throw(
			"This report can't be released yet — it's awaiting Peer Review. "
			"A reviewer must close the peer review case (Agree or Minor Disagreement) "
			"before Verify & Release becomes available.",
			title="Peer Review Required",
		)

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
			"image_space_image": image_space_image or None,
			"hide_graphs": 1 if int(hide_graphs or 0) else 0,
		}, session=session)
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
def lab_report_for_sample(sample: str, session: str | None = None) -> str | None:
	"""Existing Lab Report for the sample, (re)building it so the printable
	form reflects the CURRENT normal_test_items values. Called by both
	Verify & Release (post-approval) and Print Preliminary (pre-approval);
	either way we always rebuild so a re-edit after Save & Complete flows
	through to the next print without staleness."""
	# _build_lab_report is idempotent — reuses an existing Lab Report doc
	# when one exists and just refreshes its rows. `session` (passed by the
	# SPA's print button) scopes the report's tests to the session being
	# printed, so the print matches that screen exactly.
	return _build_lab_report(sample, {"status": "Approved"}, session=session)


def _frozen_collection_datetime(existing, sample_collected_time, ceiling):
	"""Collection time to store on a Lab Report — captured ONCE, never
	overwritten on rebuilds.

	A Sample Collection is REUSED across orders for a patient + sample type; its
	single `collected_time` is cleared and re-stamped on each new order (see the
	reset in billing_workflow). Reading it live means a *later* order's
	collection time leaks onto an *older* report — printing a collection date
	AFTER the report was generated. So we freeze the value the first time the
	report is built and leave it alone thereafter.

	  existing : value already on the report — kept as-is if present (the freeze).
	  ceiling  : latest plausible time (the report's creation, or now for a brand
	             new doc). Collection cannot happen after the report itself
	             exists, so anything past the ceiling is treated as unreliable
	             and dropped rather than stored.
	"""
	if existing:
		return existing
	ct = sample_collected_time
	if ct and ceiling:
		from frappe.utils import get_datetime
		try:
			if get_datetime(ct) > get_datetime(ceiling):
				return None
		except Exception:
			pass
	return ct


# --- Report test-selection: make the PRINT match the RESULTS SCREEN -----------
#
# The results screen (`get_sample`) scopes a reused sample's Lab Tests to the
# CURRENT workflow session's orders, so it shows exactly this visit's tests. The
# report builder historically used a different rule — a stored batch list
# (`custom_lab_tests_csv`) that gets overwritten per save — so on a sample shared
# by two orders the print and the screen disagreed (screen showed the full
# panel, print showed only the last order's tests).
#
# We now select the report's tests the SAME WAY the screen does: by the report's
# workflow session's orders. Falls back to the exact legacy batch-list logic when
# there's no session to scope by, so nothing changes for non-workflow reports.
#
# `set_report_scope('legacy')` flips back to the old behaviour at RUNTIME (no
# redeploy) if the new scoping ever misbehaves.


def _report_scope_mode():
	"""'session' (new: print matches screen) or 'legacy' (old batch list).
	Read from a private-file flag so it can be toggled without a deploy."""
	try:
		import json
		import os
		path = frappe.get_site_path("private", "files", "report_scope_mode.json")
		if os.path.exists(path):
			with open(path) as f:
				mode = (json.load(f) or {}).get("mode")
				if mode in ("session", "legacy"):
					return mode
	except Exception:
		pass
	return "session"


@frappe.whitelist()
def set_report_scope(mode: str) -> dict:
	"""Runtime switch for how a report picks its Lab Tests.

	mode='session' (default) : match the results screen (session-scoped).
	mode='legacy'            : the old stored-batch-list behaviour.

	Instant revert path — flip to 'legacy' and rebuild (Refetch) if the new
	scoping ever prints the wrong tests. No redeploy needed.
	"""
	import json
	mode = "legacy" if str(mode).lower() == "legacy" else "session"
	with open(frappe.get_site_path("private", "files", "report_scope_mode.json"), "w") as f:
		json.dump({"mode": mode}, f)
	return {"ok": True, "mode": mode}


def _session_orders(session):
	"""The service-request orders of a workflow session (empty on any problem)."""
	if not session:
		return []
	try:
		from diagnostic_management.api.collection_workflow import _session_orders as _so
		return _so(session)
	except Exception:
		return []


def _legacy_batch_lab_tests(sample):
	"""The ORIGINAL selection: the stored batch list (`custom_lab_tests_csv`),
	else a 30-minute window around the latest Lab Test. Unchanged — kept as the
	fallback and the 'legacy' mode so we can always get back to old behaviour."""
	existing_dr_for_sample = _report_for_sample(sample)
	csv_names = None
	if existing_dr_for_sample:
		csv_names = frappe.db.get_value("Diagnostic Report", existing_dr_for_sample, "custom_lab_tests_csv")
	if csv_names:
		# Skip cancelled entries (docstatus=2) — the legacy amend flow could
		# leave a cancelled Lab Test name in the CSV alongside its `-1` draft.
		raw = [n.strip() for n in csv_names.split(",") if n.strip()]
		return [n for n in raw if frappe.db.get_value("Lab Test", n, "docstatus") in (0, 1)]
	# Include Draft (0) AND Submitted (1) Lab Tests within the window.
	latest_creation = frappe.db.get_value(
		"Lab Test", {"sample": sample, "docstatus": ["<", 2]},
		"creation", order_by="creation desc",
	)
	if not latest_creation:
		return []
	threshold = frappe.utils.add_to_date(latest_creation, minutes=-30)
	return frappe.get_all(
		"Lab Test",
		filters={"sample": sample, "docstatus": ["<", 2], "creation": [">=", threshold]},
		order_by="creation asc",
		pluck="name",
	)


def _select_report_lab_tests(sample, si_link=None, session=None):
	"""Which Lab Tests belong on this report.

	When the PRINTING session is known (passed from the print action), scope to
	exactly THAT session's orders — the same set the results screen shows for the
	session the user is looking at. This is the reliable signal: a reused sample
	belongs to several sessions, and only the caller knows which one is being
	printed. With no session, or under the 'legacy' runtime flag, fall back to the
	original batch-list behaviour (unchanged).
	"""
	if _report_scope_mode() != "legacy" and session:
		orders = _session_orders(session)
		if orders:
			names = frappe.get_all(
				"Lab Test",
				filters={"sample": sample, "service_request": ["in", orders], "docstatus": ["<", 2]},
				order_by="creation asc",
				pluck="name",
			)
			if names:
				return names
	return _legacy_batch_lab_tests(sample)


def _existing_report_for(sample, session=None):
	"""The Lab Report to (re)use for this sample — scoped to the VISIT when a
	workflow session is known, so a reused sample doesn't share one report across
	visits. Only kicks in under the 'session' scope mode; legacy mode keeps the
	original per-sample lookup so behaviour is unchanged / revertible.

	Returns a Lab Report name, or None to create a fresh one for this visit.
	"""
	lr_names = frappe.get_all("Lab Report Sample", filters={"lab_sample": sample}, pluck="parent")
	lr_names = list(dict.fromkeys(lr_names))
	# The per-visit keying needs the custom_workflow_session column. If a deploy
	# hasn't migrated yet, the column is absent — fall back to per-sample instead
	# of crashing on an unknown-column SQL error.
	if (session and _report_scope_mode() != "legacy"
	        and frappe.db.has_column("Lab Report", "custom_workflow_session")):
		# The report already created for THIS visit, if any.
		for n in lr_names:
			if frappe.db.get_value("Lab Report", n, "custom_workflow_session") == session:
				return n
		# A pre-existing report on this sample that has NO session yet (built
		# before this change) — adopt it for this visit rather than orphaning it,
		# but only if it isn't already claimed by another session.
		for n in lr_names:
			if not frappe.db.get_value("Lab Report", n, "custom_workflow_session"):
				return n
		# Otherwise every existing report belongs to a DIFFERENT visit → None
		# means _build_lab_report creates a fresh report for this visit.
		return None
	# Legacy / no session: original behaviour — the sample's one report.
	return lr_names[0] if lr_names else None


def _build_lab_report(sample: str, signoff: dict | None = None, session: str | None = None) -> str | None:
	"""Create/refresh a Lab Report (genetest doctype) from a Sample Collection's
	Lab Tests + results, so the verbatim genetest print format renders.

	`session` (optional) — when the caller knows which workflow session is being
	printed, the report's tests are scoped to that session's orders so the print
	matches that screen. Without it, the legacy batch-list selection is used."""
	from frappe.utils import today

	from diagnostic_management.utils.formatters import result_flag

	signoff = signoff or {}
	if not frappe.db.exists("Sample Collection", sample):
		return None
	sc = frappe.get_doc("Sample Collection", sample)
	# Find the report for THIS VISIT. A reused Sample Collection is shared across
	# every visit for a patient + specimen type, so keying a report by sample
	# alone reuses the same LRPT record (and number) across visits — that's why a
	# returning patient's "new" report showed the old number and stale tests.
	# When the visit (workflow session) is known, look up / create the report
	# scoped to that session, so each visit gets its OWN report. Without a session
	# (non-workflow callers) fall back to the original per-sample lookup.
	existing = _existing_report_for(sample, session)
	lr = None
	if existing and frappe.db.exists("Lab Report", existing):
		candidate = frappe.get_doc("Lab Report", existing)
		docstatus = int(candidate.get("docstatus") or 0)
		if docstatus == 1:
			# SUBMITTED = released and signed. Rebuilding would rewrite
			# `collection_datetime` from the Sample Collection's CURRENT
			# collected_time and wipe/re-append every result child table —
			# which Frappe correctly refuses:
			#   "Not allowed to change Collection Date/Time after submission
			#    from 2026-07-24 13:06:20 to 2026-07-24 19:11:02"
			# That killed Print Preliminary and the Results screen's initial
			# load, because both route through here. Printing a released
			# report must never mutate it — hand the existing doc straight
			# back. (Marking the field allow_on_submit would only convert the
			# error into a silent, undetected edit of a signed report.)
			return candidate.name
		if docstatus == 2:
			# Cancelled docs can't be modified either — start a fresh report
			# rather than throwing on the first save.
			candidate = None
		lr = candidate
	if lr is None:
		lr = frappe.new_doc("Lab Report")
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
	# Age + sex are separate fields on Lab Report — the print format reads
	# `doc.patient_age` / `doc.patient_sex` directly and prints "-" when
	# blank. Compute at rebuild time from Patient.dob so the workflow
	# doesn't need age re-entered. Uses the local `format_patient_age`
	# helper which already ships with the app.
	from diagnostic_management.utils.formatters import format_patient_age
	patient_row = frappe.db.get_value(
		"Patient", sc.patient,
		["dob", "sex", "custom_age", "custom_age_type"],
		as_dict=True) or {}
	# Prefer DOB (computes exact age); fall back to `custom_age` +
	# `custom_age_type` for restored genetest patients that never had a DOB
	# on file (e.g. Caroline Gitonga — custom_age=37 Years).
	if patient_row.get("dob"):
		setf("patient_age", format_patient_age(patient_row["dob"]))
	elif patient_row.get("custom_age") not in (None, ""):
		unit = (patient_row.get("custom_age_type") or "Years").strip()
		setf("patient_age", f"{patient_row['custom_age']} {unit}")
	setf("patient_sex", patient_row.get("sex"))
	# Freeze the collection time — capture once, never overwrite on rebuild, and
	# never store a value later than the report itself. See
	# _frozen_collection_datetime for why (reused Sample Collection).
	from frappe.utils import now_datetime
	_coll_ceiling = lr.get("creation") or now_datetime()
	_frozen_coll = _frozen_collection_datetime(
		lr.get("collection_datetime"), sc.get("collected_time"), _coll_ceiling
	)
	setf("collection_datetime", _frozen_coll)
	# Carry the Sales Invoice forward — either from the Sample Collection's
	# stamp, or by taking it from the first Lab Test linked to this sample.
	si_link = sc.get("custom_sales_invoice") or frappe.db.get_value(
		"Lab Test", {"sample": sample, "custom_sales_invoice": ["!=", ""]},
		"custom_sales_invoice",
	)
	setf("custom_sales_invoice", si_link)
	# Stamp the visit so this report stays bound to this session — a later visit
	# reusing the same sample then gets its own fresh report instead of this one.
	if session:
		setf("custom_workflow_session", session)

	# Referring Doctor — picked at Billing (stored on Sales Invoice.custom_doctor)
	# needs to propagate onto the Lab Report so the print format's
	# `doc.referring_doctor_name` cell isn't blank. Prefer the SI's
	# custom_doctor; fall back to the Service Request's practitioner
	# when there's no SI yet (rare — direct clinical orders).
	referring_practitioner = None
	if si_link:
		referring_practitioner = frappe.db.get_value("Sales Invoice", si_link, "custom_doctor")
	if not referring_practitioner:
		# Fall back to the Service Request behind any Lab Test on this sample
		sr_name = frappe.db.get_value(
			"Lab Test", {"sample": sample, "service_request": ["!=", ""]}, "service_request",
		)
		if sr_name:
			referring_practitioner = frappe.db.get_value("Service Request", sr_name, "practitioner")
	if referring_practitioner and frappe.db.exists("Healthcare Practitioner", referring_practitioner):
		setf("referring_doctor", referring_practitioner)
		setf("referring_doctor_name",
		     frappe.db.get_value("Healthcare Practitioner", referring_practitioner, "practitioner_name")
		     or referring_practitioner)

	for tbl in ["lab_report_tests", "numeric_results", "descriptive_results", "grouped_results", "qualitative_results", "samples"]:
		if tbl in fns:
			lr.set(tbl, [])
	if "samples" in fns:
		# Child row mirrors the FROZEN parent value (not the live sample time) so
		# the samples table and the printed collection date always agree.
		lr.append("samples", {"lab_sample": sample, "sample_type": sc.get("sample"), "collection_datetime": lr.get("collection_datetime")})

	# Which Lab Tests go on this report — scoped to match the results screen
	# (session-scoped), with the legacy batch list as fallback / runtime revert.
	# See _select_report_lab_tests above.
	current_lt_names = _select_report_lab_tests(sample, si_link, session=session)
	for lt_name in current_lt_names:
		lt = frappe.get_doc("Lab Test", lt_name)
		ttype = frappe.db.get_value("Lab Test Template", lt.template, "lab_test_template_type") or "Single"
		# Panel headings for the print. Without this every row of a package
		# carried `group_name = <the package>`, so the print format's
		# group-by produced a SINGLE section holding all 70+ analytes. Map each
		# leaf template to the package member that owns it so FBC / Lipid /
		# Liver / Urinalysis / TFT each print under their own heading.
		from diagnostic_management.overrides.lab_test_expansion import section_map
		sections = section_map(lt.template) if ttype == "Grouped" else {}
		from diagnostic_management.utils.reference_ranges import pick_reference_range
		for r in lt.normal_test_items:
			analyte = r.lab_test_name or r.lab_test_event
			# See _shape_test — Grouped Lab Tests store the ranges on the child template.
			range_template = r.get("template") or lt.template
			picked = pick_reference_range(range_template, analyte, lt.patient)
			# Range fallback: ADMS picker → row normal_range → template's
			# custom_low_range / custom_upper_range synth. Same ladder as
			# _lab_test_rows so print / read agree.
			tmpl_row = _template_analyte_row(range_template, analyte)
			rng = (
				(picked["range_text"] if picked else None)
				or r.normal_range
				or (tmpl_row.get("synth_range") if tmpl_row else None)
			)
			uom = (
				(picked["uom"] if picked else None)
				or r.lab_test_uom
				or (tmpl_row.get("lab_test_uom") if tmpl_row else None)
			)
			# Flagging respects the analyte's result_type. Numeric uses the
			# bounds parser → High/Low/Normal. For Select and Data types we
			# treat any value that doesn't case-insensitively match the configured
			# "normal" range as Abnormal (e.g. result Positive vs reference Negative).
			# Fallback rule shared with the read paths: no explicit type + no
			# numeric context → Data, never a bare Numeric assumption.
			rtype = (picked["result_type"] if picked else None) or \
			        (tmpl_row.get("custom_result_type") if tmpl_row else None) or \
			        _infer_result_type(picked, tmpl_row, r.normal_range)
			flag = ""
			abnormal = 0
			val = (r.result_value or "").strip()
			ref = (rng or "").strip()
			# Placeholder ranges — "-", "—", "N/A" — mean "no reference range
			# configured" (Marley's templates use "-" as the sentinel). Don't
			# flag a valid qualitative result just because it doesn't literally
			# equal a placeholder character.
			ref_effective = "" if ref.lower() in ("", "-", "—", "n/a", "na") else ref
			if val:
				if rtype == "Numeric":
					from diagnostic_management.utils.formatters import banded_flag
					# Banded interpretation wins (HbA1c → Pre-diabetic / Diabetic).
					# Source the raw multi-line text from the child template — the
					# ADMS Reference Range picker collapses it to a single band.
					band_source = (tmpl_row.get("normal_range") if tmpl_row else None) or rng
					flag = banded_flag(val, band_source) or result_flag(val, rng)
					# "Normal" is not abnormal; anything else derived from a band
					# (High / Low / Pre-diabetic / Diabetic / …) is.
					abnormal = 1 if flag and flag != "Normal" else 0
				elif rtype in ("Select", "Data"):
					# `status` is a strict Select on the child (Normal/High/Low/Critical),
					# so we leave it blank for qualitative mismatches and rely on
					# `is_abnormal` for row highlighting on the printed report.
					if ref_effective and val.lower() != ref_effective.lower():
						abnormal = 1
					elif ref_effective:
						flag = "Normal"
			# Preserve the status the tech SELECTED during result entry when the
			# range-based recompute can't produce a definitive flag. Previously
			# `status` was set to `flag` outright, so an analyte whose reference
			# is a single value ("5.0") or otherwise doesn't parse as a numeric
			# range came out BLANK on the report — the manually-picked status was
			# silently deleted during review (e.g. Microalbumin 58.7 vs "5.0"
			# printed with no status). Fall back to the entered `r.status`, and
			# only let the auto-derived flag win when it actually resolved.
			entered = (r.get("status") or "").strip()
			status = flag or entered
			if not flag and entered and entered != "Normal":
				# The tech flagged it abnormal; honour that for row highlighting
				# even though the range couldn't confirm it numerically.
				abnormal = 1
			row = {
				"lab_test": lt.name,
				"test_name": analyte,
				"test_category": lt.template,
				"result_value": r.result_value,
				"uom": uom,
				"reference_range": rng,
				"status": status,
				"is_abnormal": abnormal,
			}
			if ttype == "Grouped" and "grouped_results" in fns:
				# Panel heading for this analyte; standalone Singles fall back to
				# the package itself so they still print under one section.
				heading = sections.get(range_template) or lt.template
				lr.append("grouped_results", {**row, "group_name": heading})
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
	# Carry the print-time toggles + optional uploaded image onto the Lab
	# Report doc so the print HTML renders accordingly.
	setf("custom_has_image_space", 1 if signoff.get("has_image_space") else 0)
	setf("custom_hide_graphs", 1 if signoff.get("hide_graphs") else 0)
	if signoff.get("image_space_image"):
		# Save the binary as a File and store only its URL — data URLs are
		# too large for the Attach Image varchar column.
		from diagnostic_management.api.lab import _save_image_to_files
		# Need a doc name to attach to — save the LR first if it's brand new.
		if not lr.name:
			lr.flags.ignore_permissions = True
			lr.save()
		try:
			url = _save_image_to_files(signoff["image_space_image"], lr.name)
			setf("custom_image_space_image", url)
		except Exception:
			frappe.log_error(title="_build_lab_report: image_space_image save failed")

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
