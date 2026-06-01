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
			{
				"fieldname": "is_critical",
				"label": "Critical Result",
				"fieldtype": "Check",
				"default": "0",
				"insert_after": "status",
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
	}
