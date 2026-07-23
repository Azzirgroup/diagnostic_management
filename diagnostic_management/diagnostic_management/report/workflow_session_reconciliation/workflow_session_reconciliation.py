"""Workflow Session Reconciliation — one row per Lab Workflow Session, joined
to its Sales Invoice, items, doctor, sample, and diagnostic report state.

Purpose: give the director / lab manager ONE screen that answers "for a
given window, which sessions were billed, for how much, by whom, for what
tests, and where does each one stand — paid, delivered, urgent, verified?"

Data model note: `Lab Workflow Session.draft_data` stores a JSON blob like
    {"invoice": "ACC-SINV-2026-00958", "orders": ["HSR-00137", ...]}
so the SI link is extracted via JSON_UNQUOTE(JSON_EXTRACT(...)).
"""
from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters: dict | None = None):
	filters = filters or {}
	columns = _columns()
	data = _rows(filters)
	return columns, data


def _columns() -> list[dict]:
	return [
		# Session identity
		{"fieldname": "session",          "label": _("Session"),           "fieldtype": "Link",  "options": "Lab Workflow Session", "width": 130},
		{"fieldname": "session_created",  "label": _("Session Started"),   "fieldtype": "Datetime", "width": 145},
		{"fieldname": "session_status",   "label": _("Session Status"),    "fieldtype": "Data",  "width": 100},
		{"fieldname": "current_step",     "label": _("Step"),              "fieldtype": "Data",  "width": 90},
		{"fieldname": "is_urgent",        "label": _("Urgent"),            "fieldtype": "Check", "width": 70},
		# Patient
		{"fieldname": "patient",          "label": _("Patient ID"),        "fieldtype": "Link",  "options": "Patient", "width": 130},
		{"fieldname": "patient_name",     "label": _("Patient Name"),      "fieldtype": "Data",  "width": 170},
		# Doctor
		{"fieldname": "doctor",           "label": _("Referring Doctor"),  "fieldtype": "Data",  "width": 170},
		# Sales Invoice header
		{"fieldname": "invoice",          "label": _("Sales Invoice"),     "fieldtype": "Link",  "options": "Sales Invoice", "width": 155},
		{"fieldname": "docstatus_label",  "label": _("Docstatus"),         "fieldtype": "Data",  "width": 90},
		{"fieldname": "si_status",        "label": _("SI Status"),         "fieldtype": "Data",  "width": 110},
		{"fieldname": "posting_date",     "label": _("Posting Date"),      "fieldtype": "Date",  "width": 100},
		{"fieldname": "mode_of_payment",  "label": _("Payment Mode"),      "fieldtype": "Data",  "width": 100},
		# Money
		{"fieldname": "net_total",        "label": _("Net"),               "fieldtype": "Currency", "options": "currency", "width": 110},
		{"fieldname": "grand_total",      "label": _("Grand Total"),       "fieldtype": "Currency", "options": "currency", "width": 120},
		{"fieldname": "paid_amount",      "label": _("Paid"),              "fieldtype": "Currency", "options": "currency", "width": 110},
		{"fieldname": "outstanding",      "label": _("Outstanding"),       "fieldtype": "Currency", "options": "currency", "width": 120},
		{"fieldname": "currency",         "label": _("Currency"),          "fieldtype": "Link",  "options": "Currency", "width": 80},
		# Tests
		{"fieldname": "item_count",       "label": _("# Tests"),           "fieldtype": "Int",   "width": 80},
		{"fieldname": "items",            "label": _("Tests"),             "fieldtype": "Small Text", "width": 320},
		# Sample + report state
		{"fieldname": "sample",           "label": _("Sample"),            "fieldtype": "Link",  "options": "Sample Collection", "width": 155},
		{"fieldname": "sample_status",    "label": _("Sample Status"),     "fieldtype": "Data",  "width": 120},
		{"fieldname": "dr_status",        "label": _("Report Status"),     "fieldtype": "Data",  "width": 110},
		{"fieldname": "peer_reviewed",    "label": _("Peer OK"),           "fieldtype": "Check", "width": 70},
		# Ops / accounting axes
		{"fieldname": "branch",           "label": _("Branch"),            "fieldtype": "Data",  "width": 110},
		{"fieldname": "owner",            "label": _("Session Owner"),     "fieldtype": "Link",  "options": "User", "width": 170},
	]


def _rows(filters: dict) -> list[dict]:
	where = ["1 = 1"]
	params: dict = {}

	if filters.get("from_date"):
		where.append("lws.creation >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		# End-of-day so the current day's sessions are included.
		where.append("lws.creation <= CONCAT(%(to_date)s, ' 23:59:59')")
		params["to_date"] = filters["to_date"]
	if filters.get("session_status"):
		where.append("lws.status = %(session_status)s")
		params["session_status"] = filters["session_status"]
	if filters.get("patient"):
		where.append("lws.patient = %(patient)s")
		params["patient"] = filters["patient"]
	if filters.get("is_urgent"):
		# Session has no direct urgent flag — walk to the sample.
		where.append("""EXISTS (
			SELECT 1 FROM `tabLab Test` lt2
			INNER JOIN `tabSample Collection` sc2 ON sc2.name = lt2.sample
			WHERE lt2.service_request = lws.service_request AND sc2.is_urgent = 1
		)""")

	sql = f"""
		SELECT
			lws.name              AS session,
			lws.creation          AS session_created,
			lws.status            AS session_status,
			lws.current_step      AS current_step,
			lws.patient           AS patient,
			lws.patient_name      AS patient_name,
			lws.service_request   AS service_request,
			lws.draft_data        AS draft_data,
			lws.owner             AS owner
		FROM `tabLab Workflow Session` lws
		WHERE {' AND '.join(where)}
		ORDER BY lws.creation DESC
	"""
	sessions = frappe.db.sql(sql, params, as_dict=True)

	# Batch-resolve SI + Sample + DR + items so we don't N+1.
	si_by_session: dict[str, str | None] = {}
	for s in sessions:
		si = _si_from_draft(s.get("draft_data"))
		si_by_session[s["session"]] = si

	si_names = [v for v in si_by_session.values() if v]
	si_meta: dict[str, dict] = {}
	if si_names:
		si_fields = [
			"name", "docstatus", "status", "posting_date",
			"grand_total", "net_total", "paid_amount", "outstanding_amount",
			"currency", "custom_doctor",
		]
		# Mode of payment lives on Sales Invoice Payment (child) for POS
		# invoices — the parent has no mode_of_payment column in vanilla
		# ERPNext. Query it separately with fallback = ''.
		for r in frappe.db.get_all(
			"Sales Invoice",
			filters={"name": ["in", si_names]},
			fields=si_fields,
		):
			si_meta[r["name"]] = r
		mop_by_si = {r["parent"]: r["mode_of_payment"] for r in frappe.db.sql(
			"""SELECT parent, mode_of_payment
			   FROM `tabSales Invoice Payment`
			   WHERE parent IN %(ns)s""",
			{"ns": tuple(si_names)}, as_dict=True,
		)}
		for name, meta in si_meta.items():
			meta["mode_of_payment"] = mop_by_si.get(name, "")

	# Branch column exists after `ensure_branch_accounting_dimension` fires.
	branch_by_si: dict[str, str | None] = {}
	if si_names and _column_exists("tabSales Invoice", "branch"):
		for r in frappe.db.sql(
			"SELECT name, branch FROM `tabSales Invoice` WHERE name IN %(ns)s",
			{"ns": tuple(si_names)}, as_dict=True,
		):
			branch_by_si[r["name"]] = r["branch"]

	# Items per SI — concatenated names + count.
	items_by_si: dict[str, list[str]] = {}
	if si_names:
		for r in frappe.db.sql(
			"""SELECT parent, item_name FROM `tabSales Invoice Item`
			   WHERE parent IN %(ns)s ORDER BY parent, idx""",
			{"ns": tuple(si_names)}, as_dict=True,
		):
			items_by_si.setdefault(r["parent"], []).append(r["item_name"])

	# Sample + DR — via the session's service_request → Lab Test → sample.
	sample_by_session: dict[str, str | None] = {}
	sample_status_by_sample: dict[str, str | None] = {}
	dr_by_sample: dict[str, dict] = {}

	srs = [s.get("service_request") for s in sessions if s.get("service_request")]
	if srs:
		sr_to_sample = {}
		for r in frappe.db.sql(
			"""SELECT DISTINCT service_request, sample FROM `tabLab Test`
			   WHERE service_request IN %(srs)s AND sample IS NOT NULL""",
			{"srs": tuple(srs)}, as_dict=True,
		):
			sr_to_sample.setdefault(r["service_request"], r["sample"])
		for s in sessions:
			sample_by_session[s["session"]] = sr_to_sample.get(s.get("service_request"))

		samples = [v for v in sample_by_session.values() if v]
		if samples:
			for r in frappe.db.get_all(
				"Sample Collection",
				filters={"name": ["in", samples]},
				fields=["name", "workflow_status"],
			):
				sample_status_by_sample[r["name"]] = r.get("workflow_status")

			# Diagnostic Report keyed by sample.
			dr_fields = {"status", "custom_peer_reviewed"}
			meta_fields = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
			dr_fields = list(dr_fields & meta_fields | {"name", "sample_collection"})
			for r in frappe.db.get_all(
				"Diagnostic Report",
				filters={"sample_collection": ["in", samples]},
				fields=dr_fields,
			):
				dr_by_sample[r["sample_collection"]] = r

	# Row-level filters that need the SI joined
	si_status_filter = filters.get("si_status")
	docstatus_filter = filters.get("docstatus")
	doctor_filter    = (filters.get("doctor") or "").strip().lower()
	unpaid_only      = bool(filters.get("unpaid_only"))

	rows: list[dict] = []
	for s in sessions:
		si_name = si_by_session.get(s["session"])
		si = si_meta.get(si_name) if si_name else None
		if si_status_filter and (not si or si.get("status") != si_status_filter):
			continue
		if docstatus_filter:
			want = int(docstatus_filter.split(" ", 1)[0])
			if not si or si.get("docstatus") != want:
				continue
		if doctor_filter:
			doc_val = (si.get("custom_doctor") or "") if si else ""
			if doctor_filter not in doc_val.lower():
				continue
		if unpaid_only:
			# "Unpaid only" means both: SI exists AND its status indicates
			# money outstanding. A session with no SI yet is NOT unpaid — it's
			# unbilled, which is a separate concern.
			if not si or si.get("status") not in ("Unpaid", "Overdue", "Partly Paid"):
				continue

		sample = sample_by_session.get(s["session"])
		dr = dr_by_sample.get(sample) if sample else None

		items = items_by_si.get(si_name or "", [])
		item_summary = ", ".join(items[:3])
		if len(items) > 3:
			item_summary += f", + {len(items) - 3} more"

		is_urgent = 0
		if sample:
			is_urgent = int(frappe.db.get_value("Sample Collection", sample, "is_urgent") or 0)

		row: dict = {
			"session":         s["session"],
			"session_created": s["session_created"],
			"session_status":  s["session_status"],
			"current_step":    _step_label(s.get("current_step")),
			"is_urgent":       is_urgent,
			"patient":         s.get("patient"),
			"patient_name":    s.get("patient_name"),
			"doctor":          (si or {}).get("custom_doctor") or "",
			"invoice":         si_name,
			"docstatus_label": _docstatus_label((si or {}).get("docstatus")),
			"si_status":       (si or {}).get("status") or "",
			"posting_date":    (si or {}).get("posting_date"),
			"mode_of_payment": (si or {}).get("mode_of_payment") or "",
			"net_total":       flt((si or {}).get("net_total")),
			"grand_total":     flt((si or {}).get("grand_total")),
			"paid_amount":     flt((si or {}).get("paid_amount")),
			"outstanding":     flt((si or {}).get("outstanding_amount")),
			"currency":        (si or {}).get("currency") or "",
			"item_count":      len(items),
			"items":           item_summary,
			"sample":          sample,
			"sample_status":   sample_status_by_sample.get(sample) if sample else "",
			"dr_status":       (dr or {}).get("status") or "",
			"peer_reviewed":   int((dr or {}).get("custom_peer_reviewed") or 0),
			"branch":          branch_by_si.get(si_name) if si_name else "",
			"owner":           s.get("owner"),
		}
		rows.append(row)

	return rows


def _si_from_draft(raw) -> str | None:
	"""LWS.draft_data is a JSON string; extract the invoice key safely."""
	if not raw:
		return None
	try:
		data = json.loads(raw) if isinstance(raw, str) else raw
	except (ValueError, TypeError):
		return None
	return (data or {}).get("invoice")


def _column_exists(table: str, column: str) -> bool:
	rows = frappe.db.sql(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
	return bool(rows)


def _step_label(n) -> str:
	# Lab Workflow Session.current_step is an integer 1..4; humanise for
	# the report so users don't have to remember the mapping.
	labels = {1: "Patient", 2: "Order", 3: "Collection", 4: "Results"}
	try:
		return labels.get(int(n), str(n or ""))
	except (TypeError, ValueError):
		return str(n or "")


def _docstatus_label(n) -> str:
	return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(int(n or 0), "")
