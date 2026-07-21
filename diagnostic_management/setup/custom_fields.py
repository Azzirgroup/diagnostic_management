"""Custom Field overlays added by ADMS.

The intent here matches the System Design Document section 7.2: we extend
Marley/ERPNext doctypes via additive Custom Fields installed by THIS app,
so that Marley source files stay clean and ADMS upgrades safely with new
Marley releases.

This function is idempotent — running it twice does not create duplicates.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def install_custom_fields() -> None:
	create_custom_fields(_field_map(), ignore_validate=True, update=True)


def _field_map() -> dict[str, list[dict]]:
	# Keyed by target doctype; each value is a list of Custom Field dicts.
	#
	# NOTE: every dict needs `fieldname`, `fieldtype`, `label`, and either
	# `insert_after` or it is appended to the doctype.
	return {
		"Patient": [
			{
				"fieldname": "mrn_group",
				"label": "MRN (Group)",
				"fieldtype": "Data",
				"insert_after": "uid",
				"description": "Group-level Medical Record Number for hospital groups with a shared MRN.",
			},
			{
				"fieldname": "preferred_result_channel",
				"label": "Preferred Result Channel",
				"fieldtype": "Select",
				"options": "Portal\nEmail\nWhatsApp\nSMS\nPrint",
				"insert_after": "mrn_group",
			},
			{
				"fieldname": "preferred_language_for_reports",
				"label": "Preferred Language (Reports)",
				"fieldtype": "Link",
				"options": "Language",
				"insert_after": "preferred_result_channel",
			},
			{
				"fieldname": "consent_radiation",
				"label": "Standing Consent: Radiation",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "preferred_language_for_reports",
			},
			{
				"fieldname": "consent_contrast",
				"label": "Standing Consent: Contrast",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "consent_radiation",
			},
		],
		"Healthcare Practitioner": [
			{
				"fieldname": "practitioner_role",
				"label": "ADMS Role",
				"fieldtype": "Select",
				"options": "\nLab Technician\nPathologist\nRadiology Tech\nRadiologist\nLab Manager\nRadiology Manager\nPhlebotomist\nExternal Referrer\nOther",
				"insert_after": "department",
			},
			{
				"fieldname": "is_external_referrer",
				"label": "External Referrer",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "practitioner_role",
			},
			{
				"fieldname": "external_practice_name",
				"label": "External Practice Name",
				"fieldtype": "Data",
				"insert_after": "is_external_referrer",
				"depends_on": "eval:doc.is_external_referrer",
			},
			{
				"fieldname": "referrer_commission_pct",
				"label": "Referrer Commission %",
				"fieldtype": "Percent",
				"insert_after": "external_practice_name",
				"depends_on": "eval:doc.is_external_referrer",
			},
			{
				"fieldname": "e_signature_image",
				"label": "Signature Image",
				"fieldtype": "Attach Image",
				"insert_after": "image",
			},
		],
		"Lab Test Template": [
			{
				"fieldname": "loinc_code",
				"label": "LOINC Code",
				"fieldtype": "Data",
				"insert_after": "lab_test_code",
			},
			{
				"fieldname": "tat_routine_minutes",
				"label": "TAT Routine (min)",
				"fieldtype": "Int",
				"insert_after": "lab_test_group",
			},
			{
				"fieldname": "tat_urgent_minutes",
				"label": "TAT Urgent (min)",
				"fieldtype": "Int",
				"insert_after": "tat_routine_minutes",
			},
			{
				"fieldname": "tat_stat_minutes",
				"label": "TAT STAT (min)",
				"fieldtype": "Int",
				"insert_after": "tat_urgent_minutes",
			},
			{
				"fieldname": "critical_value_low",
				"label": "Critical Low",
				"fieldtype": "Float",
				"insert_after": "lab_test_normal_range",
			},
			{
				"fieldname": "critical_value_high",
				"label": "Critical High",
				"fieldtype": "Float",
				"insert_after": "critical_value_low",
			},
			# Free-form clinical comment per analyte — rendered in the Lab
			# Report print under "Section Comments" (genetest parity).
			{
				"fieldname": "custom_comment",
				"label": "Comment / Interpretation",
				"fieldtype": "Long Text",
				"insert_after": "critical_value_high",
				"description": "Interpretive comment to print under the test results.",
			},
			# Per-(gender × age) reference ranges. Replaces / supplements the
			# single `lab_test_normal_range` string with a child table users
			# can populate per analyte. Blank gender / blank age_group on a
			# row = "matches any". For Compound templates, `analyte` on each
			# row picks which sub-analyte the row applies to.
			{
				"fieldname": "custom_reference_ranges_section",
				"label": "Reference Ranges",
				"fieldtype": "Section Break",
				"insert_after": "critical_value_high",
			},
			{
				"fieldname": "custom_reference_ranges",
				"label": "Reference Ranges",
				"fieldtype": "Table",
				"options": "ADMS Reference Range",
				"insert_after": "custom_reference_ranges_section",
			},
		],
		"Service Request": [
			{
				"fieldname": "imaging_modality",
				"label": "Imaging Modality",
				"fieldtype": "Data",
				"insert_after": "template_dt",
			},
			{
				"fieldname": "imaging_body_part",
				"label": "Body Part",
				"fieldtype": "Link",
				"options": "Body Part",
				"insert_after": "imaging_modality",
			},
			{
				"fieldname": "contrast_required",
				"label": "Contrast Required",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "imaging_body_part",
			},
			{
				"fieldname": "clinical_history_text",
				"label": "Clinical History",
				"fieldtype": "Long Text",
				"insert_after": "contrast_required",
			},
		],
		"Sample Collection": [
			{
				"fieldname": "barcode",
				"label": "Sample Barcode",
				"fieldtype": "Data",
				"insert_after": "naming_series",
			},
			{
				"fieldname": "container",
				"label": "Container / Tube",
				"fieldtype": "Select",
				# Tube-cap colour vocabulary — aligns with the container colours
				# seeded against Sample Type in setup/seed_data.py, plus the
				# common additional cap colours.
				"options": "\nRed\nGold\nLavender\nGreen\nGrey\nBlue\nYellow\nBrown\nWhite\nClear\nOther",
				"insert_after": "barcode",
			},
			{
				"fieldname": "workflow_status",
				"label": "Workflow Status",
				"fieldtype": "Select",
				# Specimen lifecycle ported from the Genetest system. Drives the
				# guided workflow (Order → Collection → Store → Result). Distinct
				# from Marley's `status` (Pending/Partly Collected/Collected),
				# which validate() force-sets and can't hold "Stored".
				"options": "To Be Collected\nCollected\nIn Transit\nReceived\nIn Processing\nTested\nStored\nRejected",
				"default": "To Be Collected",
				"insert_after": "status",
			},
			{
				"fieldname": "is_urgent",
				"label": "Urgent",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "workflow_status",
			},
			{
				"fieldname": "received_datetime",
				"label": "Received On",
				"fieldtype": "Datetime",
				"insert_after": "collected_time",
			},
			{
				"fieldname": "processed_datetime",
				"label": "Processed On",
				"fieldtype": "Datetime",
				"insert_after": "received_datetime",
			},
			{
				"fieldname": "department_barcodes",
				"label": "Department Barcodes",
				"fieldtype": "Table",
				"options": "Sample Department Barcode",
				"insert_after": "processed_datetime",
			},
			{
				"fieldname": "received_condition",
				"label": "Received Condition",
				"fieldtype": "Select",
				"options": "\nAcceptable\nHaemolysed\nClotted\nInsufficient\nWrong Tube\nOther",
				"insert_after": "collection_time",
			},
			{
				"fieldname": "rejection_reason_text",
				"label": "Rejection Reason",
				"fieldtype": "Small Text",
				"insert_after": "received_condition",
			},
		],
		"Diagnostic Report": [
			# When results are saved with `complete=1` (i.e. the technologist
			# clicks Save & Complete), we stamp this datetime. It marks the
			# moment results were ENTERED — NOT when the technologist
			# navigated to the Results step. Use this for SLAs/TAT reports
			# instead of `creation`.
			{
				"fieldname": "custom_reporting_completed_at",
				"label": "Reporting Completed At",
				"fieldtype": "Datetime",
				"insert_after": "status",
				"read_only": 1,
				"description": "Stamped when results are saved & completed (not when the Results step is opened).",
			},
			# Peer-review gate on Verify & Release. Same shape as the urgent-
			# review flow: Save & Complete auto-creates a Peer Review Case,
			# and until a reviewer closes it with Agree/Minor Disagreement
			# (which flips this flag to 1), the tech's Verify & Release
			# button stays disabled. Major Disagreement leaves the flag at
			# 0; Amendment Required rolls the Lab Tests back to Draft
			# (existing amend path).
			{
				"fieldname": "custom_peer_reviewed",
				"label": "Peer Reviewed",
				"fieldtype": "Check",
				"insert_after": "custom_reporting_completed_at",
				"read_only": 1,
				"default": "0",
				"description": "Set to 1 by submit_peer_review when a reviewer closes the case with Agree or Minor Disagreement. Required for Verify & Release.",
			},
			{
				"fieldname": "is_critical",
				"label": "Critical Result",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "custom_reporting_completed_at",
			},
			{
				"fieldname": "critical_acknowledged",
				"label": "Critical Acknowledged",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "is_critical",
			},
			{
				"fieldname": "critical_acknowledged_at",
				"label": "Critical Acknowledged At",
				"fieldtype": "Datetime",
				"insert_after": "critical_acknowledged",
			},
			{
				"fieldname": "diagnosis",
				"label": "Provisional Diagnosis",
				"fieldtype": "Small Text",
				"insert_after": "critical_acknowledged_at",
			},
			{
				"fieldname": "clinical_notes",
				"label": "Clinical Notes",
				"fieldtype": "Long Text",
				"insert_after": "diagnosis",
			},
			{
				"fieldname": "pathologist_remarks",
				"label": "Pathologist Remarks",
				"fieldtype": "Small Text",
				"insert_after": "clinical_notes",
			},
			{
				"fieldname": "accreditation_type",
				"label": "Accreditation",
				"fieldtype": "Data",
				"insert_after": "pathologist_remarks",
			},
			{
				"fieldname": "report_signature",
				"label": "Technologist Signature",
				"fieldtype": "Long Text",
				"insert_after": "accreditation_type",
			},
			{
				"fieldname": "signed_by",
				"label": "Signed By",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "report_signature",
			},
			{
				"fieldname": "pathologist_signature",
				"label": "Pathologist Signature",
				"fieldtype": "Long Text",
				"insert_after": "signed_by",
			},
			{
				"fieldname": "pathologist_name",
				"label": "Pathologist Name",
				"fieldtype": "Data",
				"insert_after": "pathologist_signature",
			},
			# Urgent-case authorization gate: an "Urgent Review Officer" must
			# authorize an urgent report before it can be Verified & Released.
			{
				"fieldname": "is_urgent",
				"label": "Urgent",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "pathologist_name",
			},
			{
				"fieldname": "urgent_review_status",
				"label": "Urgent Review Status",
				"fieldtype": "Select",
				"options": "\nPending\nAuthorized",
				"insert_after": "is_urgent",
			},
			{
				"fieldname": "urgent_reviewed_by",
				"label": "Urgent Reviewed By",
				"fieldtype": "Link",
				"options": "User",
				"insert_after": "urgent_review_status",
			},
			{
				"fieldname": "urgent_reviewed_at",
				"label": "Urgent Reviewed At",
				"fieldtype": "Datetime",
				"insert_after": "urgent_reviewed_by",
			},
			# Comma-separated Lab Test names that THIS report covers. Set by
			# save_sample when the user finalises results, so _build_lab_report
			# pulls exactly the current batch — even when a sample has stale
			# submitted Lab Tests from previous workflows (Marley reuses
			# Sample Collection docs across orders).
			{
				"fieldname": "custom_lab_tests_csv",
				"label": "Lab Tests (CSV)",
				"fieldtype": "Small Text",
				"insert_after": "urgent_reviewed_at",
				"read_only": 1,
			},
		],
		# Work Order automation (ported from genetest): each Lab Test created
		# from billing carries the Sales Invoice link, and each auto-created
		# Work Order carries the originating Sales Invoice for traceability.
		"Lab Test": [
			{
				"fieldname": "custom_sales_invoice",
				"label": "Sales Invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"insert_after": "service_request",
				"read_only": 1,
			},
		],
		# First-class Sales Invoice link on Sample Collection — auto-populated
		# from the first Lab Test that lands on the SC (via doc events). Lets
		# the workflow scope every list to "tests/samples for THIS invoice"
		# without walking session → orders → SI each time.
		"Sample Collection": [
			{
				"fieldname": "custom_sales_invoice",
				"label": "Sales Invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"insert_after": "patient",
				"read_only": 1,
			},
		],
		"Work Order": [
			{
				"fieldname": "custom_sales_invoice",
				"label": "Sales Invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"insert_after": "sales_order",
				"read_only": 1,
			},
		],
		# Branch tagging — multi-tenant scoping. Each User belongs to a Branch
		# (HRMS Branch doctype). Patients (and downstream records) inherit
		# that branch on create so a Lab Tech in Branch A only sees patients
		# registered at Branch A. Admins/System Managers bypass scoping.
		"User": [
			{
				"fieldname": "branch",
				"label": "Branch",
				"fieldtype": "Link",
				"options": "Branch",
				"insert_after": "username",
				"description": "Restrict this user to seeing records from this branch.",
			},
		],
		"Patient": [
			{
				"fieldname": "branch",
				"label": "Branch",
				"fieldtype": "Link",
				"options": "Branch",
				"insert_after": "mobile",
				"description": "Branch where the patient is registered.",
			},
		],
		# POS Profile branch — when a cashier opens a shift on a POS Profile
		# that has a branch set, the cashier's active branch lens switches
		# to that branch for the duration of the open shift. Lets a "Main
		# Branch" user temporarily work the "Westlands" counter.
		"POS Profile": [
			{
				"fieldname": "branch",
				"label": "Branch",
				"fieldtype": "Link",
				"options": "Branch",
				"insert_after": "warehouse",
				"description": "Cashiers on this profile's open shift see this branch's data.",
			},
		],
		# Lab Report extras.
		"Lab Report": [
			# When checked, the print format reserves a 6cm-tall blank box
			# above the signatures (for a stamp / manual signature / image).
			{
				"fieldname": "custom_has_image_space",
				"label": "Has image space (print)",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "status",
				"description": "Reserve a blank box on the print format above the signatures.",
			},
			# Optional image that fills the reserved box. When set AND the
			# checkbox is on, the print renders this <img> inside the box;
			# when unset but the checkbox is on, the box stays empty.
			{
				"fieldname": "custom_image_space_image",
				"label": "Image space image",
				"fieldtype": "Attach Image",
				"insert_after": "custom_has_image_space",
				"depends_on": "custom_has_image_space",
				"description": "Image rendered inside the reserved space (stamp, scanned signature, etc.).",
			},
			# When checked, the per-analyte trend charts are suppressed in
			# the print format (useful for short single-test reports where
			# trend graphs add noise instead of value).
			{
				"fieldname": "custom_hide_graphs",
				"label": "Don't show graphs on print",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "custom_image_space_image",
				"description": "Suppress trend charts on the printed Lab Report.",
			},
			# First-class Sales Invoice link — stamped from the sample / lab
			# tests this Lab Report bundles, so lists can filter by SI in one
			# step instead of walking sample → lab tests → SI.
			{
				"fieldname": "custom_sales_invoice",
				"label": "Sales Invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"insert_after": "custom_image_space_image",
				"read_only": 1,
			},
		],
		# Shift / cashier session: every Sales Invoice submitted while the
		# user has an open POS Opening Entry gets stamped here, so the
		# closing entry's reconciliation preview can pull a clean invoice
		# list (rather than scraping by timestamp alone).
		"Sales Invoice": [
			{
				"fieldname": "custom_pos_opening_entry",
				"label": "POS Opening Entry (Shift)",
				"fieldtype": "Link",
				"options": "POS Opening Entry",
				"insert_after": "pos_profile",
				"read_only": 1,
			},
			# Referring doctor — free-text so it works on sites where the
			# "Doctor" doctype was never installed (all genetest sites).
			# Was historically created interactively as `Link → Doctor`,
			# which caused the Framework UI's row-open to 404 fetching
			# the missing doctype's metadata. `create_custom_fields`
			# with `update=True` upgrades the existing field's fieldtype
			# on migrate; no data loss because values are already text.
			# `options` explicitly emptied — old Link definition left
			# "Doctor" in that column, which desk widgets still probe.
			{
				"fieldname": "custom_doctor",
				"label": "Doctor",
				"fieldtype": "Data",
				"options": "",
				"insert_after": "customer_name",
				"allow_on_submit": 1,
				"in_list_view": 1,
				"in_standard_filter": 1,
			},
			# NOTE: `branch` on financial doctypes (Sales Invoice / Payment
			# Entry / Purchase Invoice / Journal Entry / GL Entry / …) is NOT
			# managed here. Instead we register `Branch` as an ERPNext
			# Accounting Dimension in setup/accounting_dimension.py — ERPNext
			# then auto-creates the `branch` Custom Field on EVERY financial
			# doctype it knows about (including GL Entry), so OOTB Profit &
			# Loss, Balance Sheet, General Ledger and Trial Balance reports
			# all gain a Branch filter for free.
		],
		# Stock Entry traceability — each Material Issue auto-created when a
		# Sample Collection reaches "Tested" points back at the originating SI
		# and Sample. Lets Reports tie consumption to revenue and lets the
		# billing screen list the alerts for a given invoice.
		# Per-analyte status flag on the result row. Marley's Normal Test Result
		# only carries a free-form `lab_test_comment`; ADMS adds an explicit
		# Select so the Results step shows an editable badge (Normal / High /
		# Pre-diabetic / Diabetic / …) alongside the value. Same ladder as
		# Lab Report Numeric Result.status so badges render consistently on
		# the screen and on the printed Lab Report.
		"Normal Test Result": [
			{
				"fieldname": "status",
				"label": "Status",
				"fieldtype": "Select",
				"options": "Normal\nHigh\nLow\nAbnormal\nCritical\nOptimal\nIntermediate\nDeficiency\nInsufficiency\nSufficiency\nPotential Toxicity\nPre-diabetic\nDiabetic",
				"default": "Normal",
				"insert_after": "lab_test_comment",
			},
		],
		"Stock Entry": [
			{
				"fieldname": "custom_sales_invoice",
				"label": "Sales Invoice",
				"fieldtype": "Link",
				"options": "Sales Invoice",
				"insert_after": "stock_entry_type",
				"read_only": 1,
			},
			{
				"fieldname": "custom_sample_collection",
				"label": "Sample Collection",
				"fieldtype": "Link",
				"options": "Sample Collection",
				"insert_after": "custom_sales_invoice",
				"read_only": 1,
			},
		],
	}
