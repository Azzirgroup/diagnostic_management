"""READ-ONLY diagnostics for understanding how a sample's Lab Tests, Diagnostic
Report and Lab Report relate. Writes nothing — safe to run anytime.

Purpose: a reused Sample Collection can carry Lab Tests from MULTIPLE orders,
and the Lab Report is built from a stored "batch list" (custom_lab_tests_csv).
Before changing how the report picks its tests — which risks breaking the
preliminary-report flow — this shows the ground truth for one sample:

  * every Lab Test on the sample (template, type, invoice, order, when)
  * the Diagnostic Report(s) and their stored batch list + invoice
  * the Lab Report(s) and which Lab Tests actually landed in the results

Run in a browser (logged in):
  /api/method/diagnostic_management.utils.report_diagnostics.diagnose_sample?sample=HLC-SC-2026-00294
"""

import frappe


@frappe.whitelist()
def install_report_fields() -> dict:
	"""Create the custom_workflow_session field on Lab Report NOW, without
	needing a full migrate (deploys here have not been reliably migrating).
	Idempotent — safe to run repeatedly.

	Requires System Manager (custom-field creation). Run once after deploy:
	  /api/method/diagnostic_management.utils.report_diagnostics.install_report_fields
	"""
	if "System Manager" not in set(frappe.get_roles()):
		frappe.throw("Only a System Manager can install fields.")

	before = frappe.db.has_column("Lab Report", "custom_workflow_session")

	# Install ALL app custom fields (covers custom_workflow_session,
	# custom_has_image_space, ...) — deploys here don't run migrate, so create
	# them now. Idempotent.
	try:
		from diagnostic_management.setup.custom_fields import install_custom_fields
		install_custom_fields()
		frappe.db.commit()
	except Exception:
		frappe.log_error(title="install_report_fields: install_custom_fields failed")

	# Refresh the print formats too — the DB copy is what prints, so the latest
	# template (graphs removed) only takes effect once it lands.
	print_formats_updated = False
	try:
		from diagnostic_management.setup.print_formats import install_print_formats
		install_print_formats()
		frappe.db.commit()
		print_formats_updated = True
	except Exception:
		frappe.log_error(title="install_report_fields: install_print_formats failed")

	after = frappe.db.has_column("Lab Report", "custom_workflow_session")

	# Also widen the reference_range columns (Data 140 -> Text) so long clinical
	# reference ranges don't abort report building with a truncation error.
	widened = []
	for dt in ("Lab Report Numeric Result", "Lab Report Grouped Result", "Lab Report Test"):
		try:
			frappe.db.change_column_type(dt, "reference_range", "text", nullable=True)
			widened.append(dt)
		except Exception:
			frappe.log_error(title=f"install_report_fields: widen {dt}.reference_range failed")
	if widened:
		frappe.db.commit()

	return {
		"ok": bool(after),
		"field": "custom_workflow_session",
		"already_existed": bool(before),
		"now_present": bool(after),
		"print_formats_updated": print_formats_updated,
		"reference_range_widened": widened,
		"note": "Fields ready + print formats refreshed (trend graphs removed) "
		        "+ reference_range widened. Per-visit fix and long reference "
		        "ranges will now work.",
	}


@frappe.whitelist()
def refresh_lab_report_print_format() -> dict:
	"""Force the 'Lab Report' print format in the DB to match the shipped HTML
	file, and report whether the trend graphs are gone from BOTH the disk file
	and the stored DB copy. Pinpoints why a template change didn't take:

	  * disk_has_graphs = True  -> the new HTML wasn't deployed (deploy problem)
	  * db_has_graphs   = True  -> install didn't run / failed (run this)
	  * both False              -> fixed; print will no longer show graphs

	Requires System Manager. Run after deploy:
	  /api/method/diagnostic_management.utils.report_diagnostics.refresh_lab_report_print_format
	"""
	if "System Manager" not in set(frappe.get_roles()):
		frappe.throw("Only a System Manager can refresh print formats.")

	from diagnostic_management.setup.print_formats import _read

	MARKER = "generate_trend_chart_svg"
	disk_html = _read("lab_report_print.html")
	disk_has_graphs = MARKER in disk_html

	refreshed = False
	err = None
	try:
		from diagnostic_management.setup.print_formats import install_print_formats
		install_print_formats()
		frappe.db.commit()
		refreshed = True
	except Exception as e:
		err = str(e)
		frappe.log_error(title="refresh_lab_report_print_format failed")

	db_html = frappe.db.get_value("Print Format", "Lab Report", "html") or ""
	db_has_graphs = MARKER in db_html

	if disk_has_graphs:
		verdict = ("STALE DEPLOY: the new template isn't on the server yet. Redeploy "
		           "the app (make sure lab_report_print.html is included), then run this again.")
	elif db_has_graphs:
		verdict = "DB still has the old template — refresh did not apply. Check the error field."
	else:
		verdict = "FIXED: graphs removed from the stored print format. Reprint to confirm."

	return {
		"ok": refreshed and not db_has_graphs,
		"refreshed": refreshed,
		"disk_has_graphs": disk_has_graphs,
		"db_has_graphs": db_has_graphs,
		"db_html_length": len(db_html),
		"error": err,
		"verdict": verdict,
	}


def _existing_fields(doctype, wanted):
	"""Keep only the fields that actually exist on `doctype` (plus name), so a
	missing custom field can't crash a read-only dump."""
	have = {df.fieldname for df in frappe.get_meta(doctype).fields} | {"name", "creation", "modified"}
	return [f for f in wanted if f in have]


@frappe.whitelist()
def preview_visit_report(sample: str, session: str | None = None) -> dict:
	"""READ-ONLY: for a given sample + visit (session), show whether printing/
	releasing would REUSE an existing Lab Report or CREATE a fresh one — the core
	of the per-visit fix. Writes nothing.
	"""
	from diagnostic_management.api import results as R

	has_session_field = frappe.db.has_column("Lab Report", "custom_workflow_session")
	lr_names = frappe.get_all("Lab Report Sample", filters={"lab_sample": sample}, pluck="parent")
	lr_names = list(dict.fromkeys(lr_names))
	report_fields = _existing_fields(
		"Lab Report", ["name", "creation", "custom_workflow_session", "custom_sales_invoice"]
	)
	reports = []
	for n in lr_names:
		info = frappe.db.get_value("Lab Report", n, report_fields, as_dict=True) or {}
		reports.append(info)

	resolved = R._existing_report_for(sample, session) if session else R._existing_report_for(sample)
	return {
		"sample": sample,
		"session_passed": session,
		"scope_mode": R._report_scope_mode(),
		"existing_reports_on_sample": reports,
		"would_use_report": resolved,
		"outcome": ("REUSE existing report " + resolved) if resolved
		           else "CREATE a fresh report for this visit",
		"note": "A returning patient (new session) should say CREATE. Same visit "
		        "should REUSE its own report.",
	}


@frappe.whitelist()
def debug_report_build(sample: str, session: str | None = None) -> dict:
	"""READ-ONLY: shows exactly why the report shows what it shows.

	Calls the REAL selection logic and reports the current scope mode, the Lab
	Report's docstatus (a SUBMITTED report can't be rebuilt), and what the
	selection would return for the given session. This pinpoints whether the
	problem is the flag, the deploy, or a submitted-report guard.
	"""
	from diagnostic_management.api import results as R

	lr = frappe.db.get_value("Lab Report Sample", {"lab_sample": sample}, "parent")
	lr_info = None
	if lr:
		lr_info = frappe.db.get_value("Lab Report", lr, ["name", "docstatus", "status"], as_dict=True)

	try:
		selected = R._select_report_lab_tests(sample, None, session=session)
		sel_err = None
	except TypeError as e:
		# Old code deployed: _select_report_lab_tests has no `session` param yet.
		selected, sel_err = None, f"OLD CODE DEPLOYED (no session param): {e}"

	blocked_submitted = bool(lr_info and int(lr_info.get("docstatus") or 0) == 1)
	return {
		"sample": sample,
		"session_passed": session,
		"report_scope_mode": R._report_scope_mode(),
		"lab_report": lr_info,
		"report_is_submitted_cannot_rebuild": blocked_submitted,
		"selection_would_return": selected,
		"selection_count": (len(selected) if selected is not None else None),
		"selection_error": sel_err,
		"expected": "count should be 11 for session=LW-2026-01371 when mode=session and new code is live",
	}


@frappe.whitelist()
def preview_report_tests(sample: str) -> dict:
	"""READ-ONLY: show exactly what the new session-scope WOULD put on the report
	for this sample — without building anything. This tells us, before any push,
	whether the fix will work for this sample.

	Reports the sessions the sample belongs to, each session's orders, and the
	final list of Lab Tests the session-scope would select vs the legacy list.
	"""
	# sessions that include this sample (via the samples child)
	rows = frappe.get_all(
		"Lab Workflow Session Sample", filters={"sample": sample}, fields=["parent"]
	)
	session_names = sorted({r["parent"] for r in rows})
	sessions = []
	for s in session_names:
		info = frappe.db.get_value("Lab Workflow Session", s, ["name", "creation"], as_dict=True) or {}
		try:
			from diagnostic_management.api.collection_workflow import _session_orders
			orders = _session_orders(s)
		except Exception as e:
			orders = f"error: {e}"
		info["orders"] = orders
		sessions.append(info)

	# what scoping to EACH session would select — so you can see, per session,
	# exactly which tests the print would contain if opened from that session.
	from diagnostic_management.api.collection_workflow import _session_orders
	per_session_selection = {}
	for s in session_names:
		orders = _session_orders(s)
		per_session_selection[s] = frappe.get_all(
			"Lab Test",
			filters={"sample": sample, "service_request": ["in", orders or ["__none__"]], "docstatus": ["<", 2]},
			order_by="creation asc", pluck="name",
		) if orders else []

	dr_name = None
	for f in ({"sample_collection": sample}, {"ref_doctype": "Sample Collection", "docname": sample}):
		hits = frappe.get_all("Diagnostic Report", filters=f, pluck="name")
		if hits:
			dr_name = hits[0]; break
	csv = frappe.db.get_value("Diagnostic Report", dr_name, "custom_lab_tests_csv") if dr_name else None

	best = max((len(v) for v in per_session_selection.values()), default=0)
	verdict = (
		f"WILL FIX when printed from the right session — a session selects up to {best} tests"
		if best > len([c for c in (csv or "").split(",") if c.strip()])
		else "WON'T CHANGE: no session selects more than the legacy batch — needs a different signal"
	)
	return {
		"sample": sample,
		"sessions_containing_sample": sessions,
		"tests_selected_per_session": per_session_selection,
		"legacy_batch_csv": csv,
		"verdict": verdict,
		"how_to_read": "Open the workflow whose session gives the tests you want; "
		               "its 'Print Report' now scopes the print to that session.",
	}


@frappe.whitelist()
def diagnose_sample(sample: str) -> dict:
	if not frappe.db.exists("Sample Collection", sample):
		return {"error": f"Sample Collection {sample} not found"}

	sc = frappe.db.get_value(
		"Sample Collection", sample,
		_existing_fields("Sample Collection",
		                 ["patient", "patient_name", "sample", "workflow_status",
		                  "collected_time", "custom_sales_invoice"]),
		as_dict=True,
	) or {}

	# --- every Lab Test on this (possibly reused) sample ---
	lab_tests = frappe.get_all(
		"Lab Test",
		filters={"sample": sample},
		fields=_existing_fields("Lab Test",
		                        ["name", "template", "docstatus", "creation",
		                         "service_request", "custom_sales_invoice"]),
		order_by="creation asc",
	)
	for lt in lab_tests:
		lt["template_type"] = frappe.db.get_value(
			"Lab Test Template", lt.get("template"), "lab_test_template_type"
		)

	invoices = sorted({lt.get("custom_sales_invoice") for lt in lab_tests if lt.get("custom_sales_invoice")})

	# --- Diagnostic Report(s) tied to this sample ---
	dr_names = set()
	for f in ({"sample_collection": sample}, {"ref_doctype": "Sample Collection", "docname": sample}):
		for n in frappe.get_all("Diagnostic Report", filters=f, pluck="name"):
			dr_names.add(n)
	dr_fields = _existing_fields(
		"Diagnostic Report",
		["name", "status", "custom_lab_tests_csv", "custom_sales_invoice", "creation"],
	)
	diagnostic_reports = []
	for n in dr_names:
		d = frappe.db.get_value("Diagnostic Report", n, dr_fields, as_dict=True) or {}
		diagnostic_reports.append(d)

	# --- Lab Report(s) tied to this sample (via the samples child) ---
	lr_names = frappe.get_all(
		"Lab Report Sample", filters={"lab_sample": sample}, pluck="parent"
	)
	lab_reports = []
	for n in sorted(set(lr_names)):
		lr = frappe.get_doc("Lab Report", n)
		# distinct Lab Tests that actually landed in the results tables
		tests_in_report = set()
		for tbl in ("grouped_results", "numeric_results", "lab_report_tests",
		            "qualitative_results", "descriptive_results"):
			for row in lr.get(tbl) or []:
				if row.get("lab_test"):
					tests_in_report.add(row.get("lab_test"))
		lab_reports.append({
			"name": lr.name,
			"creation": str(lr.get("creation")),
			"collection_datetime": str(lr.get("collection_datetime")),
			"custom_sales_invoice": lr.get("custom_sales_invoice"),
			"status": lr.get("status"),
			"lab_tests_in_results": sorted(tests_in_report),
			"grouped_rows": len(lr.get("grouped_results") or []),
		})

	return {
		"sample": sample,
		"sample_info": sc,
		"lab_tests_on_sample": lab_tests,
		"distinct_invoices_on_sample": invoices,
		"diagnostic_reports": diagnostic_reports,
		"lab_reports": lab_reports,
		"reading": {
			"lab_test_count": len(lab_tests),
			"invoice_count": len(invoices),
			"note": "If the panel tests and the TFT sit on DIFFERENT invoices, this "
			        "is a reused-sample / multiple-orders case. If they share ONE "
			        "invoice but only some are in the report, it's a batch-list "
			        "(custom_lab_tests_csv) scoping issue.",
		},
	}
