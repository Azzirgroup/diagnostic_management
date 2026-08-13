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
def diagnose_sample(sample: str) -> dict:
	if not frappe.db.exists("Sample Collection", sample):
		return {"error": f"Sample Collection {sample} not found"}

	sc = frappe.db.get_value(
		"Sample Collection", sample,
		["patient", "patient_name", "sample", "workflow_status", "collected_time",
		 "custom_sales_invoice"],
		as_dict=True,
	) or {}

	# --- every Lab Test on this (possibly reused) sample ---
	lab_tests = frappe.get_all(
		"Lab Test",
		filters={"sample": sample},
		fields=["name", "template", "docstatus", "creation",
		        "service_request", "custom_sales_invoice"],
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
	diagnostic_reports = []
	for n in dr_names:
		d = frappe.db.get_value(
			"Diagnostic Report", n,
			["name", "status", "custom_lab_tests_csv", "custom_sales_invoice", "creation"],
			as_dict=True,
		) or {}
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
