"""Workflow Session Reconciliation — every Sales Invoice in the window,
plus every Lab Workflow Session in the window, joined together where they
share billing (LWS.draft_data.invoice → SI.name).

Row grain: ONE row per (session, invoice) pair. If an SI has no session,
the session columns are blank; if a session has no SI yet, the invoice
columns are blank. Directors can see workflow-billed AND directly-billed
revenue on one screen, alongside stalled workflows that haven't been
billed. `source` column marks which case each row is.
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
		# Row provenance
		{"fieldname": "source",           "label": _("Source"),            "fieldtype": "Data",  "width": 90},
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
		# Sample + report state (workflow-billed rows only)
		{"fieldname": "sample",           "label": _("Sample"),            "fieldtype": "Link",  "options": "Sample Collection", "width": 155},
		{"fieldname": "sample_status",    "label": _("Sample Status"),     "fieldtype": "Data",  "width": 120},
		{"fieldname": "dr_status",        "label": _("Report Status"),     "fieldtype": "Data",  "width": 110},
		{"fieldname": "peer_reviewed",    "label": _("Peer OK"),           "fieldtype": "Check", "width": 70},
		# Ops / accounting axes
		{"fieldname": "branch",           "label": _("Branch"),            "fieldtype": "Data",  "width": 110},
		{"fieldname": "owner",            "label": _("Created By"),        "fieldtype": "Link",  "options": "User", "width": 170},
	]


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _rows(filters: dict) -> list[dict]:
	# Collect the RAW inputs from both sides, then merge.
	sessions = _fetch_sessions(filters)
	si_names_from_sessions = {_si_from_draft(s.get("draft_data")) for s in sessions}
	si_names_from_sessions.discard(None)

	sis = _fetch_invoices(filters, extra_names=si_names_from_sessions)

	# Batch-load the accessory data keyed by SI name.
	si_meta = {r["name"]: r for r in sis}
	items_by_si = _items_by_si(list(si_meta.keys()))
	mop_by_si   = _mop_by_si(list(si_meta.keys()))
	branch_by_si= _branch_by_si(list(si_meta.keys()))
	for name, meta in si_meta.items():
		meta["mode_of_payment"] = mop_by_si.get(name, "")

	# Session-side accessories (sample + DR).
	sr_by_session = {s["session"]: s.get("service_request") for s in sessions}
	sample_by_session = _sample_by_session(sr_by_session)
	sample_meta = _sample_meta(sample_by_session.values())
	dr_by_sample = _dr_by_sample(sample_by_session.values())

	# Invert: si_name → session_row (each SI is billed by at most one LWS
	# via draft_data, so a 1-1 map is safe).
	session_by_si: dict[str, dict] = {}
	for s in sessions:
		si_name = _si_from_draft(s.get("draft_data"))
		if si_name:
			session_by_si[si_name] = s

	# Track which sessions we've emitted so we can add unbilled sessions after.
	emitted_sessions: set[str] = set()

	# Row-level filters
	row_filters = {
		"si_status": filters.get("si_status"),
		"docstatus": filters.get("docstatus"),
		"doctor":    (filters.get("doctor") or "").strip().lower(),
		"unpaid":    bool(filters.get("unpaid_only")),
		"session_status": filters.get("session_status"),
	}

	rows: list[dict] = []

	# ---- SI-driven rows (every SI in window, workflow info left-filled) ----
	for si in _sort_invoices(sis):
		si_name = si["name"]
		sess = session_by_si.get(si_name)
		if sess:
			emitted_sessions.add(sess["session"])
		if not _passes_row_filters(sess, si, row_filters):
			continue
		rows.append(_build_row(
			source="Workflow" if sess else "Direct SI",
			session=sess, si=si,
			items=items_by_si.get(si_name, []),
			branch=branch_by_si.get(si_name),
			sample_by_session=sample_by_session,
			sample_meta=sample_meta, dr_by_sample=dr_by_sample,
		))

	# ---- LWS-only rows: sessions with no SI (or SI outside window) --------
	for s in sessions:
		if s["session"] in emitted_sessions:
			continue
		if not _passes_row_filters(s, None, row_filters):
			continue
		rows.append(_build_row(
			source="Workflow (unbilled)" if not _si_from_draft(s.get("draft_data")) else "Workflow",
			session=s, si=None, items=[], branch=None,
			sample_by_session=sample_by_session,
			sample_meta=sample_meta, dr_by_sample=dr_by_sample,
		))

	return rows


def _passes_row_filters(sess: dict | None, si: dict | None, f: dict) -> bool:
	if f["session_status"] and (not sess or sess.get("session_status") != f["session_status"]):
		return False
	if f["si_status"] and (not si or si.get("status") != f["si_status"]):
		return False
	if f["docstatus"]:
		want = int(f["docstatus"].split(" ", 1)[0])
		if not si or si.get("docstatus") != want:
			return False
	if f["doctor"]:
		doc_val = (si.get("custom_doctor") or "") if si else ""
		if f["doctor"] not in doc_val.lower():
			return False
	if f["unpaid"]:
		if not si or si.get("status") not in ("Unpaid", "Overdue", "Partly Paid"):
			return False
	return True


def _build_row(*, source: str, session: dict | None, si: dict | None,
               items: list[str], branch,
               sample_by_session: dict, sample_meta: dict, dr_by_sample: dict) -> dict:
	# Only workflow-billed rows resolve a sample; direct SIs don't have one.
	sample = sample_by_session.get(session["session"]) if session else None
	sample_row = sample_meta.get(sample) if sample else {}
	dr = dr_by_sample.get(sample) if sample else None

	item_summary = ", ".join(items[:3])
	if len(items) > 3:
		item_summary += f", + {len(items) - 3} more"

	return {
		"source":          source,
		"session":         (session or {}).get("session"),
		"session_created": (session or {}).get("session_created"),
		"session_status":  (session or {}).get("session_status") or "",
		"current_step":    _step_label((session or {}).get("current_step")),
		"is_urgent":       int(sample_row.get("is_urgent") or 0),
		# Prefer SI's patient (authoritative when billed) — fall back to session.
		"patient":         (si or {}).get("patient") or (session or {}).get("patient"),
		"patient_name":    (si or {}).get("patient_name") or (session or {}).get("patient_name"),
		"doctor":          (si or {}).get("custom_doctor") or "",
		"invoice":         (si or {}).get("name"),
		"docstatus_label": _docstatus_label((si or {}).get("docstatus")) if si else "",
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
		"sample_status":   sample_row.get("workflow_status") or "",
		"dr_status":       (dr or {}).get("status") or "",
		"peer_reviewed":   int((dr or {}).get("custom_peer_reviewed") or 0),
		"branch":          branch or (si or {}).get("branch") or "",
		# "Created By" — SI's owner when billed, else the session's owner.
		"owner":           (si or {}).get("owner") or (session or {}).get("owner"),
	}


# ---------------------------------------------------------------------------
# Fetch helpers — separated so the query construction is easy to audit.
# ---------------------------------------------------------------------------

def _fetch_sessions(filters: dict) -> list[dict]:
	"""Every Lab Workflow Session in the window (or matching patient / status
	when filters narrow it), keyed for later join by draft_data.invoice."""
	where = ["1 = 1"]
	params: dict = {}
	if filters.get("from_date"):
		where.append("lws.creation >= %(from_date)s")
		params["from_date"] = filters["from_date"]
	if filters.get("to_date"):
		where.append("lws.creation <= CONCAT(%(to_date)s, ' 23:59:59')")
		params["to_date"] = filters["to_date"]
	if filters.get("patient"):
		where.append("lws.patient = %(patient)s")
		params["patient"] = filters["patient"]
	if filters.get("is_urgent"):
		where.append("""EXISTS (
			SELECT 1 FROM `tabLab Test` lt2
			INNER JOIN `tabSample Collection` sc2 ON sc2.name = lt2.sample
			WHERE lt2.service_request = lws.service_request AND sc2.is_urgent = 1
		)""")

	return frappe.db.sql(f"""
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
	""", params, as_dict=True)


def _fetch_invoices(filters: dict, extra_names: set[str]) -> list[dict]:
	"""Every Sales Invoice whose posting_date is in the window, PLUS any SI
	referenced by an in-window session (even if its own posting_date is
	outside the window — e.g. session opened today, SI dated yesterday)."""
	si_fields = [
		"name", "docstatus", "status", "posting_date",
		"grand_total", "net_total", "paid_amount", "outstanding_amount",
		"currency", "custom_doctor", "patient", "patient_name", "owner",
	]
	base_filters: dict = {"docstatus": ["<", 2]}
	if filters.get("from_date") and filters.get("to_date"):
		base_filters["posting_date"] = ["between",
			[filters["from_date"], filters["to_date"]]]
	elif filters.get("from_date"):
		base_filters["posting_date"] = [">=", filters["from_date"]]
	elif filters.get("to_date"):
		base_filters["posting_date"] = ["<=", filters["to_date"]]
	if filters.get("patient"):
		base_filters["patient"] = filters["patient"]

	primary = frappe.db.get_all(
		"Sales Invoice", filters=base_filters, fields=si_fields, limit_page_length=0,
	)

	# Union with any SI a session references but wasn't picked up by date filter.
	got = {r["name"] for r in primary}
	extras = [n for n in (extra_names or set()) if n and n not in got]
	if extras:
		primary += frappe.db.get_all(
			"Sales Invoice", filters={"name": ["in", extras]},
			fields=si_fields, limit_page_length=0,
		)
	return primary


def _items_by_si(names: list[str]) -> dict[str, list[str]]:
	if not names:
		return {}
	out: dict[str, list[str]] = {}
	for r in frappe.db.sql(
		"""SELECT parent, item_name FROM `tabSales Invoice Item`
		   WHERE parent IN %(ns)s ORDER BY parent, idx""",
		{"ns": tuple(names)}, as_dict=True,
	):
		out.setdefault(r["parent"], []).append(r["item_name"])
	return out


def _mop_by_si(names: list[str]) -> dict[str, str]:
	# Mode of payment lives on Sales Invoice Payment (POS child) — parent
	# has no such column in vanilla ERPNext.
	if not names:
		return {}
	rows = frappe.db.sql(
		"""SELECT parent, mode_of_payment
		   FROM `tabSales Invoice Payment`
		   WHERE parent IN %(ns)s""",
		{"ns": tuple(names)}, as_dict=True,
	)
	return {r["parent"]: r["mode_of_payment"] for r in rows}


def _branch_by_si(names: list[str]) -> dict[str, str | None]:
	if not names or not _column_exists("tabSales Invoice", "branch"):
		return {}
	rows = frappe.db.sql(
		"SELECT name, branch FROM `tabSales Invoice` WHERE name IN %(ns)s",
		{"ns": tuple(names)}, as_dict=True,
	)
	return {r["name"]: r["branch"] for r in rows}


def _sample_by_session(sr_by_session: dict) -> dict[str, str | None]:
	srs = [sr for sr in sr_by_session.values() if sr]
	if not srs:
		return {}
	sr_to_sample = {}
	for r in frappe.db.sql(
		"""SELECT DISTINCT service_request, sample FROM `tabLab Test`
		   WHERE service_request IN %(srs)s AND sample IS NOT NULL""",
		{"srs": tuple(srs)}, as_dict=True,
	):
		sr_to_sample.setdefault(r["service_request"], r["sample"])
	return {sess: sr_to_sample.get(sr) for sess, sr in sr_by_session.items()}


def _sample_meta(names) -> dict[str, dict]:
	names = [n for n in names if n]
	if not names:
		return {}
	rows = frappe.db.get_all(
		"Sample Collection",
		filters={"name": ["in", list(set(names))]},
		fields=["name", "workflow_status", "is_urgent"],
	)
	return {r["name"]: r for r in rows}


def _dr_by_sample(sample_names) -> dict[str, dict]:
	names = [n for n in sample_names if n]
	if not names:
		return {}
	dr_meta = {df.fieldname for df in frappe.get_meta("Diagnostic Report").fields}
	fields = list({"status", "custom_peer_reviewed"} & dr_meta | {"name", "sample_collection"})
	rows = frappe.db.get_all(
		"Diagnostic Report",
		filters={"sample_collection": ["in", list(set(names))]},
		fields=fields,
	)
	return {r["sample_collection"]: r for r in rows}


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _si_from_draft(raw) -> str | None:
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


def _sort_invoices(sis: list[dict]) -> list[dict]:
	# Newest posting_date first, ties broken by name descending so
	# ACC-SINV-2026-00959 comes before -00958 within the same day.
	return sorted(sis,
		key=lambda r: (r.get("posting_date") or "", r.get("name") or ""),
		reverse=True,
	)


def _step_label(n) -> str:
	labels = {1: "Patient", 2: "Order", 3: "Collection", 4: "Results"}
	try:
		return labels.get(int(n), str(n or ""))
	except (TypeError, ValueError):
		return str(n or "")


def _docstatus_label(n) -> str:
	return {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(int(n or 0), "")
