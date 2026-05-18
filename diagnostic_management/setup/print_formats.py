"""Custom Print Formats shipped by ADMS.

A Print Format is just a `Print Format` doctype record. We upsert ours on
every migrate so updates to the HTML/Jinja template land without manual
import steps. The records are NOT marked `standard='Yes'` because they
belong to a custom app, not Frappe core — that flag is only for Frappe
shipped formats.
"""

from __future__ import annotations

import frappe


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
