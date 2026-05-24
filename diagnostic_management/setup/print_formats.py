"""Custom Print Formats shipped by ADMS.

A Print Format is just a `Print Format` doctype record. We upsert ours on
every migrate so updates to the HTML/Jinja template land without manual
import steps. The records are NOT marked `standard='Yes'` because they
belong to a custom app, not Frappe core — that flag is only for Frappe
shipped formats.
"""

from __future__ import annotations

import os

import frappe


def _read(filename: str) -> str:
	"""Read a print-format HTML shipped alongside this module."""
	path = os.path.join(os.path.dirname(__file__), filename)
	try:
		with open(path, encoding="utf-8") as f:
			return f.read()
	except OSError:
		return ""


def install_print_formats() -> None:
	for spec in _formats():
		_upsert(spec)


def _upsert(spec: dict) -> None:
	name = spec["name"]
	if frappe.db.exists("Print Format", name):
		doc = frappe.get_doc("Print Format", name)
	else:
		doc = frappe.new_doc("Print Format")
		doc.name = name
	for k, v in spec.items():
		setattr(doc, k, v)
	doc.flags.ignore_permissions = True
	doc.save()


def _formats() -> list[dict]:
	return [
		{
			"name": "Diagnostic Order Requisition",
			"doc_type": "Service Request",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 15.0,
			"margin_bottom": 15.0,
			"margin_left": 15.0,
			"margin_right": 15.0,
			"line_breaks": 0,
			"html": _ORDER_REQUISITION_HTML,
		},
		{
			"name": "Specimen Label",
			"doc_type": "Sample Collection",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 10.0,
			"margin_bottom": 10.0,
			"margin_left": 10.0,
			"margin_right": 10.0,
			"line_breaks": 0,
			"html": _SPECIMEN_LABEL_HTML,
		},
		{
			"name": "Patient Barcode Label",
			"doc_type": "Patient",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 5.0,
			"margin_bottom": 5.0,
			"margin_left": 5.0,
			"margin_right": 5.0,
			"line_breaks": 0,
			"html": _PATIENT_BARCODE_LABEL_HTML,
		},
		{
			"name": "Sample Collection Receipt",
			"doc_type": "Sample Collection",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 10.0,
			"margin_bottom": 10.0,
			"margin_left": 10.0,
			"margin_right": 10.0,
			"line_breaks": 0,
			"html": _SAMPLE_RECEIPT_HTML,
		},
		{
			"name": "Diagnostic Lab Report",
			"doc_type": "Diagnostic Report",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 15.0,
			"margin_bottom": 15.0,
			"margin_left": 15.0,
			"margin_right": 15.0,
			"line_breaks": 0,
			"html": _LAB_REPORT_HTML,
		},
		# Verbatim copy of genetest's "Genetest Lab Report" format, on the ported
		# Lab Report doctype. HTML lives in setup/lab_report_print.html unchanged.
		{
			"name": "Lab Report",
			"doc_type": "Lab Report",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 10.0,
			"margin_bottom": 10.0,
			"margin_left": 10.0,
			"margin_right": 10.0,
			"line_breaks": 0,
			"html": _read("lab_report_print.html"),
		},
		# Verbatim copies of the remaining genetest formats (HTML unchanged except
		# a neutral company fallback). Names drop the "Genetest" branding to match
		# the ADMS naming, like the Lab Report did.
		{
			"name": "Diagnostic Sales Invoice",
			"doc_type": "Sales Invoice",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 10.0,
			"margin_bottom": 10.0,
			"margin_left": 10.0,
			"margin_right": 10.0,
			"line_breaks": 0,
			"html": _read("sales_invoice_print.html"),
		},
		{
			"name": "Diagnostic Lab Test",
			"doc_type": "Lab Test",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 10.0,
			"margin_bottom": 10.0,
			"margin_left": 10.0,
			"margin_right": 10.0,
			"line_breaks": 0,
			"html": _read("lab_test_print.html"),
		},
		{
			"name": "Purchase Order Print",
			"doc_type": "Purchase Order",
			"module": "Diagnostic Management",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"font": "Default",
			"margin_top": 10.0,
			"margin_bottom": 10.0,
			"margin_left": 10.0,
			"margin_right": 10.0,
			"line_breaks": 0,
			"html": _read("purchase_order_print.html"),
		},
	]


# ---------------------------------------------------------------------------
# Jinja Print Format — modelled after ERPNext's stock formats (Sales Invoice,
# Sales Order). Leans on Frappe's built-in print stylesheet (Bootstrap-style
# `row`/`col-*` grid, .text-muted, table.table) instead of custom CSS, so
# the output picks up letterhead, font, and theme settings from the site.
# `doc` is the Service Request being printed; `frappe` and `_` are bound by
# Frappe's print engine.
# ---------------------------------------------------------------------------

_SPECIMEN_LABEL_HTML = """
<h3 class="text-center" style="margin-bottom: 2px;">Specimen Label</h3>
<p class="text-center text-muted" style="margin-top: 0; font-size: 10px;">{{ doc.company or '' }}</p>

<div class="text-center" style="margin: 4px 0;">
    {{ generate_barcode_svg(doc.barcode or doc.name) | safe }}
</div>

<hr style="margin: 8px 0;">

<table class="table" style="margin: 0;">
    <tr>
        <th style="width: 35%;">Sample ID</th>
        <td><strong style="font-size: 14px;">{{ doc.name }}</strong></td>
    </tr>
    {%- if doc.barcode %}
    <tr><th>Barcode</th><td style="font-family: monospace;">{{ doc.barcode }}</td></tr>
    {%- endif %}
    <tr>
        <th>Patient</th>
        <td><strong>{{ doc.patient_name or doc.patient or '' }}</strong></td>
    </tr>
    <tr><th>MRN</th><td>{{ doc.patient or '' }}</td></tr>
    {%- if doc.patient_sex %}
    <tr><th>Sex / Age</th><td>{{ doc.patient_sex }}{% if doc.patient_age %} · {{ doc.patient_age }}{% endif %}</td></tr>
    {%- endif %}
    <tr><th>Specimen</th><td>{{ doc.sample or '' }} ({{ doc.sample_qty or 0 }} {{ doc.sample_uom or '' }})</td></tr>
    {%- if doc.collected_time %}
    <tr><th>Collected</th><td>{{ frappe.utils.format_datetime(doc.collected_time) }}</td></tr>
    {%- endif %}
    {%- if doc.collected_by %}
    <tr><th>Collected By</th><td>{{ doc.collected_by }}</td></tr>
    {%- endif %}
    {%- if doc.service_request %}
    <tr><th>Order</th><td>{{ doc.service_request }}</td></tr>
    {%- endif %}
    <tr><th>Status</th><td>{{ doc.status }}{% if doc.received_condition %} · {{ doc.received_condition }}{% endif %}</td></tr>
</table>

<p class="text-center text-muted" style="font-size: 9px; margin-top: 12px;">
    Printed {{ frappe.utils.format_datetime(frappe.utils.now_datetime()) }} · {{ doc.name }}
</p>
"""


# Patient wristband / chart barcode label. Ported from the Genetest
# "Patient Barcode Label" — sized 60mm × 40mm for a label printer, with a
# real scannable Code128 barcode of the Patient id.
_PATIENT_BARCODE_LABEL_HTML = """
<style>
  @page { size: 60mm 40mm; margin: 2mm; }
  .patient-label { font-family: Arial, sans-serif; font-size: 9px; width: 56mm; padding: 2mm; }
  .patient-header { text-align: center; font-weight: bold; font-size: 10px; border-bottom: 1px solid #1a4a6e; padding-bottom: 2px; margin-bottom: 3px; color: #1a4a6e; }
  .patient-barcode { text-align: center; margin: 4px 0; }
  .patient-barcode svg { max-width: 100%; height: 25px; }
  .patient-id { text-align: center; font-family: 'Courier New', monospace; font-size: 10px; font-weight: bold; letter-spacing: 1px; color: #1a4a6e; }
  .patient-name { font-weight: bold; font-size: 10px; text-align: center; margin-top: 2px; }
  .patient-meta { text-align: center; font-size: 8px; color: #555; margin-top: 1px; }
</style>
{%- set co = frappe.get_all('Company', limit=1) -%}
{%- set co_name = frappe.get_cached_doc('Company', co[0].name).abbr if co else 'LAB' -%}
<div class="patient-label">
    <div class="patient-header">{{ co_name }} LAB</div>
    <div class="patient-barcode">{{ generate_barcode_svg(doc.name) | safe }}</div>
    <div class="patient-id">{{ doc.name }}</div>
    <div class="patient-name">{{ doc.patient_name or '-' }}</div>
    <div class="patient-meta">
        {{ doc.sex or '' }}
        {%- if doc.dob %} &middot; {{ format_patient_age(doc.dob) }}{% endif %}
        {%- if doc.mobile %} &middot; {{ doc.mobile }}{% endif %}
    </div>
</div>
"""


# Hand-out receipt the collection desk gives the patient. Ported from the
# Genetest "Sample Collection Receipt", remapped to Marley Sample Collection
# fields (sample / collected_time / collected_by).
_SAMPLE_RECEIPT_HTML = """
<style>
  .receipt { font-family: Arial, sans-serif; font-size: 11px; max-width: 320px; }
  .receipt .header { text-align: center; border-bottom: 1px dashed #1a4a6e; padding-bottom: 5px; }
  .receipt .header h3 { color: #1a4a6e; margin: 4px 0; }
  .receipt .barcode { text-align: center; margin: 12px 0; }
  .receipt .barcode svg { max-width: 90%; height: 32px; }
  .receipt .info p { margin: 4px 0; }
</style>
<div class="receipt">
    <div class="header">
        <h3>Sample Collection Receipt</h3>
        <div class="text-muted">{{ doc.company or '' }}</div>
    </div>
    <div class="barcode">
        {{ generate_barcode_svg(doc.barcode or doc.name) | safe }}
        <div style="font-family: monospace; letter-spacing: 2px; font-weight: bold; color: #1a4a6e;">{{ doc.barcode or doc.name }}</div>
    </div>
    <div class="info">
        <p><b>Sample ID:</b> {{ doc.name }}</p>
        <p><b>Patient:</b> {{ doc.patient_name or doc.patient or '' }}</p>
        <p><b>Specimen:</b> {{ doc.sample or '' }}{% if doc.sample_qty %} ({{ doc.sample_qty }} {{ doc.sample_uom or '' }}){% endif %}</p>
        {%- if doc.container %}<p><b>Container:</b> {{ doc.container }}</p>{% endif %}
        <p><b>Collected:</b> {{ format_report_datetime(doc.collected_time) }}</p>
        {%- if doc.collected_by %}<p><b>Collector:</b> {{ doc.collected_by }}</p>{% endif %}
        {%- if doc.service_request %}<p><b>Order:</b> {{ doc.service_request }}</p>{% endif %}
    </div>
    <p style="text-align:center; margin-top: 10px;">Please retain this receipt</p>
</div>
"""


_ORDER_REQUISITION_HTML = """
{%- set priority_clean = (doc.priority or 'Routine').replace('-Priority', '') -%}
{%- set status_clean   = (doc.status   or 'Active' ).replace('-Request Status', '') -%}

<h2 class="text-center" style="margin-bottom: 4px;">Diagnostic Order Requisition</h2>
<p class="text-center text-muted" style="margin-top: 0;">{{ doc.company or '' }}</p>

<hr>

<div class="row" style="margin-bottom: 14px;">
    <div class="col-xs-6">
        <strong>Order ID:</strong> {{ doc.name }}<br>
        <strong>Order Date:</strong> {{ frappe.utils.formatdate(doc.order_date) if doc.order_date else '' }}
        {%- if doc.order_time %} {{ doc.order_time }}{% endif %}<br>
        {%- if doc.occurrence_date %}
        <strong>Required by:</strong> {{ frappe.utils.formatdate(doc.occurrence_date) }}<br>
        {%- endif %}
        <strong>Priority:</strong> {{ priority_clean }}<br>
        <strong>Status:</strong> {{ status_clean }}
    </div>
    <div class="col-xs-6 text-right">
        <strong>Patient:</strong> {{ doc.patient_name or doc.patient or '' }}<br>
        <strong>MRN:</strong> {{ doc.patient or '' }}<br>
        {%- if doc.patient_gender %}<strong>Sex:</strong> {{ doc.patient_gender }}<br>{% endif %}
        {%- if doc.patient_age %}<strong>Age:</strong> {{ doc.patient_age }}<br>{% endif %}
        {%- if doc.patient_mobile %}<strong>Mobile:</strong> {{ doc.patient_mobile }}<br>{% endif %}
        {%- if doc.practitioner %}<strong>Practitioner:</strong> {{ doc.practitioner_name or doc.practitioner }}<br>{% endif %}
    </div>
</div>

<h4>Requested Test / Service</h4>
<table class="table table-bordered" style="margin-top: 8px;">
    <thead>
        <tr>
            <th style="width: 22%;">Code</th>
            <th>Description</th>
            <th style="width: 18%;">Source</th>
            <th class="text-right" style="width: 10%;">Qty</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td><strong>{{ doc.template_dn or '' }}</strong></td>
            <td>{{ doc.title or doc.template_dn or '' }}</td>
            <td>{{ doc.template_dt or '' }}</td>
            <td class="text-right">{{ doc.quantity or 1 }}</td>
        </tr>
    </tbody>
</table>

{%- if doc.imaging_modality or doc.imaging_body_part or doc.contrast_required %}
<h4>Imaging Parameters</h4>
<table class="table table-bordered" style="margin-top: 8px;">
    {%- if doc.imaging_modality %}
    <tr><th style="width: 30%;">Modality</th><td>{{ doc.imaging_modality }}</td></tr>
    {%- endif %}
    {%- if doc.imaging_body_part %}
    <tr><th>Body Part</th><td>{{ doc.imaging_body_part }}</td></tr>
    {%- endif %}
    {%- if doc.contrast_required %}
    <tr><th>Contrast</th><td>Required</td></tr>
    {%- endif %}
</table>
{%- endif %}

<h4>Clinical History / Notes</h4>
<p style="white-space: pre-wrap; border: 1px solid #d1d8dd; padding: 10px; min-height: 60px;">
{{- doc.clinical_history_text or doc.order_description or doc.comment or '—' -}}
</p>

<div class="row" style="margin-top: 40px;">
    <div class="col-xs-6">
        <p style="border-top: 1px solid #000; padding-top: 6px; margin-top: 40px;" class="text-center text-muted">
            Ordering Practitioner Signature
        </p>
    </div>
    <div class="col-xs-6">
        <p style="border-top: 1px solid #000; padding-top: 6px; margin-top: 40px;" class="text-center text-muted">
            Collection / Receiving Officer
        </p>
    </div>
</div>

<p class="text-center text-muted" style="font-size: 10px; margin-top: 20px;">
    Generated on {{ frappe.utils.format_datetime(frappe.utils.now_datetime()) }} ·
    Order {{ doc.name }} · docstatus {{ doc.docstatus }}
</p>
"""


# Diagnostic Lab Report — sample-centric results report (one per Sample
# Collection), aggregating every Lab Test on the sample, with the verifier's
# signature. `doc` is the Diagnostic Report (doc.sample_collection set).
_LAB_REPORT_HTML = """
<style>
  .lr-section { margin-top: 14px; }
  .lr-section-header { background:#1a4a6e; color:#fff; padding:4px 8px; font-weight:bold; font-size:12px; }
  .lr-grid { width:100%; font-size:11px; }
  .lr-grid td { padding:2px 6px; vertical-align:top; }
  .lr-grid .lbl { color:#666; width:16%; }
  table.lr-results { width:100%; border-collapse:collapse; font-size:11px; margin-top:4px; }
  table.lr-results th, table.lr-results td { border:1px solid #cbd5e1; padding:4px 6px; text-align:left; }
  table.lr-results th { background:#f1f5f9; }
  .flag-abn { color:#b91c1c; font-weight:bold; }
  .flag-norm { color:#15803d; }
  .lr-sign-grid { width:100%; margin-top:30px; }
  .lr-sign-cell { width:50%; vertical-align:bottom; padding:0 10px; }
  .lr-sign-img { height:48px; }
  .lr-sign-line { border-top:1px solid #000; padding-top:3px; font-size:11px; font-weight:bold; }
  .lr-muted { color:#888; font-size:10px; }
</style>
{%- set sample = doc.sample_collection -%}
{%- set pat = frappe.db.get_value('Patient', doc.patient, ['sex','dob','mobile'], as_dict=True) or {} -%}
{%- set scd = frappe.db.get_value('Sample Collection', sample, ['collected_time','collection_point','referring_practitioner'], as_dict=True) or {} -%}
{%- set tests = frappe.get_all('Lab Test', filters={'sample': sample}, fields=['name','template'], order_by='creation') if sample else [] -%}

<h2 class="text-center" style="margin-bottom:2px;">Laboratory Report</h2>
<p class="text-center text-muted" style="margin-top:0;">{{ doc.company or '' }}</p>
{%- if doc.is_critical %}<p class="text-center" style="color:#b91c1c;font-weight:bold;margin:4px 0;">⚠ CRITICAL RESULT</p>{%- endif %}

<div class="lr-section">
  <div class="lr-section-header">Patient Information</div>
  <table class="lr-grid">
    <tr><td class="lbl">Patient Name</td><td>{{ doc.patient_name or doc.patient or '' }}</td>
        <td class="lbl">Patient ID</td><td>{{ doc.patient or '' }}</td></tr>
    <tr><td class="lbl">Age / Gender</td><td>{{ format_patient_age(pat.dob) }}{% if pat.sex %} / {{ pat.sex }}{% endif %}</td>
        <td class="lbl">Contact</td><td>{{ pat.mobile or '' }}</td></tr>
    <tr><td class="lbl">Referred By</td><td>{{ scd.referring_practitioner or doc.practitioner or '' }}</td>
        <td class="lbl">Sample</td><td>{{ sample or '' }}</td></tr>
    <tr><td class="lbl">Collected</td><td>{{ format_report_datetime(scd.collected_time) }}</td>
        <td class="lbl">Report Date</td><td>{{ frappe.utils.format_datetime(doc.modified) }}</td></tr>
  </table>
</div>

<div class="lr-section">
  <div class="lr-section-header">Detailed Test Results</div>
  {%- for t in tests %}
  {%- set normals = frappe.get_all('Normal Test Result', filters={'parent': t.name}, fields=['lab_test_name','lab_test_event','result_value','lab_test_uom','normal_range'], order_by='idx') -%}
  {%- set descs = frappe.get_all('Descriptive Test Result', filters={'parent': t.name}, fields=['lab_test_particulars','result_value'], order_by='idx') -%}
  <p style="font-weight:bold;margin:8px 0 2px;">{{ t.template or t.name }}</p>
  {%- if normals %}
  <table class="lr-results">
    <thead><tr><th style="width:34%;">Test</th><th>Result</th><th>Unit</th><th>Reference Range</th><th>Status</th></tr></thead>
    <tbody>
      {%- for r in normals %}
      {%- set flag = result_flag(r.result_value, r.normal_range) -%}
      <tr>
        <td>{{ r.lab_test_name or r.lab_test_event or '' }}</td>
        <td class="{{ 'flag-abn' if flag in ['High','Low'] else '' }}">{{ r.result_value or '' }}</td>
        <td>{{ r.lab_test_uom or '' }}</td>
        <td>{{ r.normal_range or '' }}</td>
        <td class="{{ 'flag-abn' if flag in ['High','Low'] else ('flag-norm' if flag=='Normal' else '') }}">{{ flag }}</td>
      </tr>
      {%- endfor %}
    </tbody>
  </table>
  {%- endif %}
  {%- if descs %}
  <table class="lr-results">
    <thead><tr><th style="width:34%;">Test</th><th>Result / Finding</th></tr></thead>
    <tbody>{%- for r in descs %}<tr><td>{{ r.lab_test_particulars or '' }}</td><td>{{ r.result_value or '' }}</td></tr>{%- endfor %}</tbody>
  </table>
  {%- endif %}
  {%- endfor %}
</div>

{%- if doc.get('diagnosis') or doc.get('clinical_notes') or doc.get('pathologist_remarks') %}
<div class="lr-section">
  <div class="lr-section-header">Clinical Notes &amp; Remarks</div>
  <table class="lr-grid">
    {%- if doc.get('diagnosis') %}<tr><td class="lbl">Diagnosis</td><td>{{ doc.diagnosis }}</td></tr>{%- endif %}
    {%- if doc.get('clinical_notes') %}<tr><td class="lbl">Clinical Notes</td><td style="white-space:pre-wrap;">{{ doc.clinical_notes }}</td></tr>{%- endif %}
    {%- if doc.get('pathologist_remarks') %}<tr><td class="lbl">Pathologist Remarks</td><td style="white-space:pre-wrap;">{{ doc.pathologist_remarks }}</td></tr>{%- endif %}
  </table>
</div>
{%- endif %}

<table class="lr-sign-grid"><tr>
  <td class="lr-sign-cell">
    {%- if doc.get('report_signature') %}<img class="lr-sign-img" src="{{ doc.report_signature }}"><br>{%- endif %}
    <div class="lr-sign-line">Lab Technologist</div>
    <div class="lr-muted">{{ doc.get('signed_by') or '' }}</div>
  </td>
  <td class="lr-sign-cell">
    {%- if doc.get('pathologist_signature') %}<img class="lr-sign-img" src="{{ doc.pathologist_signature }}"><br>{%- endif %}
    <div class="lr-sign-line">Consultant Pathologist</div>
    <div class="lr-muted">{{ doc.get('pathologist_name') or '' }}</div>
  </td>
</tr></table>

<p class="text-center lr-muted" style="margin-top:18px;">
  {%- if doc.get('accreditation_type') %}{{ doc.accreditation_type }} · {% endif %}Status: {{ doc.status }} · Generated {{ frappe.utils.format_datetime(frappe.utils.now_datetime()) }}
</p>
"""
