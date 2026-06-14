"""Shift / cashier-session backend, ported from genetest/api/lists.py + shift_report.py.

The "shift" model is built directly on ERPNext POS:
  - POS Profile          → the shift profile (warehouse / accounts / payment modes)
  - POS Opening Entry    → opening a shift (with cash float per mode)
  - POS Closing Entry    → closing the shift (with reconciliation per mode)

Every endpoint mirrors genetest exactly so the ported ShiftList.vue works
unchanged except for the call path (now `diagnostic_management.api.shifts.*`).

Tying shifts to billing:
  - We stamp `custom_pos_opening_entry` + `custom_shift_profile` onto each
    Sales Invoice posted while the user has an open shift (see
    `tag_sales_invoice_with_shift`). The closing-entry preview reads that
    field to gather a clean list of invoices for reconciliation, so
    end-of-shift cash counts can't drift even if a user keeps their session
    open across multiple shifts.
"""
from __future__ import annotations

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, today
from collections import defaultdict


# ---------------------------------------------------------------------------
# POS Profile (Shift Profile)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_shift_profiles(search: str = "", limit: int = 25, start: int = 0) -> dict:
	filters = {"disabled": 0}
	or_filters = {}
	if search:
		or_filters = {
			"name": ["like", f"%{search}%"],
			"company": ["like", f"%{search}%"],
			"warehouse": ["like", f"%{search}%"],
		}
	data = frappe.get_list(
		"POS Profile", filters=filters, or_filters=or_filters,
		fields=["name", "company", "warehouse", "currency", "disabled"],
		limit_page_length=int(limit), start=int(start), order_by="modified desc",
	)
	total = frappe.db.count("POS Profile", filters=filters)
	return {"data": data, "total": total}


def _ensure_mode_of_payment_account(mode: str, company: str, account: str) -> None:
	"""Add a Mode of Payment Account row for (mode, company) if one doesn't
	already exist. Idempotent: skips if a row is already configured."""
	if not (mode and company and account and frappe.db.exists("Mode of Payment", mode)):
		return
	exists = frappe.db.exists("Mode of Payment Account", {"parent": mode, "company": company})
	if exists:
		return
	try:
		mop = frappe.get_doc("Mode of Payment", mode)
		mop.append("accounts", {"company": company, "default_account": account})
		mop.flags.ignore_permissions = True
		mop.save()
	except Exception:
		# Don't let a MoP setup failure abort the profile creation; the
		# downstream validate will surface a clearer error if it matters.
		frappe.log_error(title=f"shifts._ensure_mode_of_payment_account({mode}, {company})")


def _resolve_defaults(company: str) -> dict:
	"""Auto-fill the accounts a POS Profile needs but the UI doesn't ask for.
	Pulls from Company defaults; falls back to any matching account if a
	specific default isn't set on the company."""
	if not company:
		return {}
	c = frappe.db.get_value(
		"Company", company,
		[
			"cost_center", "default_income_account", "default_receivable_account",
			"write_off_account", "default_cash_account",
			"abbr", "default_currency",
		], as_dict=True,
	) or {}
	cost_center = c.get("cost_center") \
		or frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
	income_account = c.get("default_income_account") \
		or frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_type": "Income Account"}, "name") \
		or frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_name": ["like", "%Sales%"]}, "name")
	write_off_account = c.get("write_off_account") \
		or frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_name": ["like", "%Write Off%"]}, "name") \
		or income_account
	cash_account = c.get("default_cash_account") \
		or frappe.db.get_value("Account", {"company": company, "is_group": 0, "account_type": "Cash"}, "name")
	return {
		"cost_center": cost_center,
		"income_account": income_account,
		"write_off_account": write_off_account,
		"write_off_cost_center": cost_center,
		"cash_account": cash_account,
		"currency": c.get("default_currency"),
	}


@frappe.whitelist()
def create_shift_profile(
	name: str, company: str, warehouse: str, currency: str = "",
	payments: str = "[]", applicable_for_users: str = "[]",
	write_off_account: str = "", write_off_cost_center: str = "",
	cost_center: str = "", income_account: str = "",
	branch: str = "",
) -> dict:
	if isinstance(payments, str): payments = json.loads(payments)
	if isinstance(applicable_for_users, str): applicable_for_users = json.loads(applicable_for_users)

	defaults = _resolve_defaults(company)
	# Anything the user didn't supply, fall back to the company default so the
	# POS Profile insert doesn't blow up on mandatory fields the UI never asked.
	if not currency: currency = defaults.get("currency") or ""
	if not write_off_account: write_off_account = defaults.get("write_off_account") or ""
	if not write_off_cost_center: write_off_cost_center = defaults.get("write_off_cost_center") or ""
	if not cost_center: cost_center = defaults.get("cost_center") or ""
	if not income_account: income_account = defaults.get("income_account") or ""

	if not write_off_account or not write_off_cost_center:
		frappe.throw(
			f"Company {company} has no Write Off Account / Cost Center configured. "
			"Either set them on the Company doctype or pass them explicitly.",
			title="Missing Company Defaults",
		)

	doc = frappe.new_doc("POS Profile")
	doc.__newname = name
	doc.company = company
	doc.warehouse = warehouse
	if currency: doc.currency = currency
	doc.write_off_account = write_off_account
	doc.write_off_cost_center = write_off_cost_center
	if cost_center: doc.cost_center = cost_center
	if income_account: doc.income_account = income_account
	# Optional Branch tag — cashiers opening a shift on this profile
	# get steered to this branch's data for the duration of the shift.
	if branch:
		if not frappe.db.exists("Branch", branch):
			frappe.throw(_("Branch {0} does not exist.").format(branch))
		doc.branch = branch
	# A POS Profile must have at least one payment row, otherwise opening a
	# shift can't render a balance form. Default to Cash if nothing supplied.
	if not payments:
		payments = [{"mode_of_payment": "Cash", "default": 1}]
	# ERPNext also requires AT LEAST ONE row with default=1 — otherwise
	# `validate_payment_methods` throws "Please select a default mode of
	# payment". The Vue form often forgets to tick the checkbox, so we
	# auto-mark the first one when none is flagged.
	if not any(int(pm.get("default") or 0) for pm in payments):
		first_real = next((pm for pm in payments if pm.get("mode_of_payment")), None)
		if first_real:
			first_real["default"] = 1
	for pm in payments:
		mop = pm.get("mode_of_payment", "")
		if not mop:
			continue
		# ERPNext's POS Profile validator requires each Mode of Payment to
		# have a default account configured for this company. If it doesn't
		# we wire one up using the company default cash account so the user
		# never hits "Please set default Cash or Bank account in Mode of
		# Payments X" from the UI.
		_ensure_mode_of_payment_account(mop, company, defaults.get("cash_account") or write_off_account)
		row = {"mode_of_payment": mop, "default": int(pm.get("default") or 0)}
		row["account"] = defaults.get("cash_account") or write_off_account
		doc.append("payments", row)
	for u in applicable_for_users:
		if not u.get("user"):
			continue
		doc.append("applicable_for_users", {
			"user": u.get("user", ""),
			"default": u.get("default", 0),
		})
	doc.insert()
	return doc.as_dict()


@frappe.whitelist()
def get_pos_profiles() -> list[str]:
	return frappe.db.get_list("POS Profile",
		filters={"disabled": 0}, fields=["name"], pluck="name", order_by="name")


# ---------------------------------------------------------------------------
# POS Opening Entry (Shift Opening)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_shift_opening_entries(search: str = "", status: str = "", limit: int = 25, start: int = 0) -> dict:
	filters: dict = {}
	if status: filters["status"] = status
	or_filters = {}
	if search:
		or_filters = {
			"name": ["like", f"%{search}%"],
			"pos_profile": ["like", f"%{search}%"],
			"user": ["like", f"%{search}%"],
		}
	data = frappe.get_list(
		"POS Opening Entry", filters=filters, or_filters=or_filters,
		fields=["name", "pos_profile", "user", "company", "status",
		        "posting_date", "period_start_date"],
		limit_page_length=int(limit), start=int(start), order_by="creation desc",
	)
	total = frappe.db.count("POS Opening Entry", filters=filters)
	return {"data": data, "total": total}


@frappe.whitelist()
def create_shift_opening_entry(pos_profile: str, company: str, balance_details: str = "[]", user: str = "") -> dict:
	if isinstance(balance_details, str): balance_details = json.loads(balance_details)
	cashier = user or frappe.session.user
	doc = frappe.new_doc("POS Opening Entry")
	doc.pos_profile = pos_profile
	doc.company = company
	doc.user = cashier
	doc.period_start_date = frappe.utils.now()
	doc.posting_date = today()
	for bd in balance_details:
		doc.append("balance_details", {
			"mode_of_payment": bd.get("mode_of_payment", ""),
			"opening_amount": flt(bd.get("opening_amount", 0)),
		})
	doc.insert(); doc.submit()
	return doc.as_dict()


@frappe.whitelist()
def get_open_shift_entries(scope: str = "own") -> list[dict]:
	"""Currently open POS Opening Entries. `scope='own'` (default) restricts
	to the calling user's own shifts — what a cashier sees in the close-shift
	dropdown. `scope='all'` returns every open shift, for managers / admins
	reconciling across the team.

	Bypasses permission checks (internal helper called on behalf of the user)
	so Billing Officers / Receptionists who don't have global read on POS
	Opening Entry can still see their own open shifts."""
	filters: dict = {"status": "Open", "docstatus": 1}
	if scope != "all":
		filters["user"] = frappe.session.user
	rows = frappe.db.get_all(
		"POS Opening Entry", filters=filters,
		fields=["name", "pos_profile", "user", "company", "period_start_date", "posting_date"],
		order_by="creation desc", ignore_permissions=True,
	)
	# Stringify datetime/date so the frontend can serialize cleanly.
	for r in rows:
		if r.get("period_start_date") is not None:
			r["period_start_date"] = str(r["period_start_date"])
		if r.get("posting_date") is not None:
			r["posting_date"] = str(r["posting_date"])
	return rows


@frappe.whitelist()
def get_active_shift_for_user(user: str | None = None) -> dict | None:
	"""The currently-open shift for this user (or None). Used by the billing
	screen to stamp Sales Invoices with the right shift.

	Internal helper — runs with ignore_permissions because users who can post
	invoices (Receptionist, Billing Officer) need to KNOW their own shift
	even when they don't have permission to list everyone else's."""
	user = user or frappe.session.user
	rows = frappe.db.get_all(
		"POS Opening Entry",
		filters={"user": user, "status": "Open", "docstatus": 1},
		fields=["name", "pos_profile", "company", "period_start_date"],
		order_by="creation desc", limit=1, ignore_permissions=True,
	)
	if not rows:
		return None
	r = dict(rows[0])
	r["period_start_date"] = str(r.get("period_start_date") or "")
	return r


# ---------------------------------------------------------------------------
# POS Closing Entry (Shift Closing)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_shift_closing_entries(search: str = "", status: str = "", limit: int = 25, start: int = 0) -> dict:
	filters: dict = {}
	if status: filters["status"] = status
	or_filters = {}
	if search:
		or_filters = {
			"name": ["like", f"%{search}%"],
			"pos_profile": ["like", f"%{search}%"],
			"user": ["like", f"%{search}%"],
		}
	data = frappe.get_list(
		"POS Closing Entry", filters=filters, or_filters=or_filters,
		fields=["name", "pos_profile", "user", "company", "status",
		        "posting_date", "period_start_date", "period_end_date",
		        "grand_total", "net_total", "total_quantity"],
		limit_page_length=int(limit), start=int(start), order_by="creation desc",
	)
	total = frappe.db.count("POS Closing Entry", filters=filters)
	return {"data": data, "total": total}


@frappe.whitelist()
def get_shift_closing_preview(pos_opening_entry: str) -> dict:
	"""Fetch invoices + build per-payment-mode reconciliation rows for closing."""
	opening = frappe.get_doc("POS Opening Entry", pos_opening_entry)

	# We pick up invoices that either explicitly point at this opening entry
	# (via the custom_pos_opening_entry stamp) OR were posted by this user on
	# the same POS Profile after the shift started.
	invoices = frappe.db.sql("""
		SELECT si.name, si.posting_date, si.customer_name, si.grand_total,
		       si.net_total, si.total_qty
		FROM `tabSales Invoice` si
		WHERE si.owner = %s AND si.docstatus = 1
		  AND si.pos_profile = %s
		  AND (si.custom_pos_opening_entry = %s
		       OR timestamp(si.posting_date, si.posting_time) >= %s)
		ORDER BY si.creation
	""", (opening.user, opening.pos_profile, pos_opening_entry,
	      opening.period_start_date), as_dict=True)

	grand_total = sum(flt(inv.grand_total) for inv in invoices)
	net_total = sum(flt(inv.net_total) for inv in invoices)
	total_qty = sum(flt(inv.total_qty) for inv in invoices)

	# Per-payment-mode totals across all those invoices.
	payment_totals: dict[str, float] = {}
	for inv in invoices:
		payments = frappe.get_all("Sales Invoice Payment",
			filters={"parent": inv.name},
			fields=["mode_of_payment", "amount"])
		for p in payments:
			mop = p.mode_of_payment
			payment_totals[mop] = flt(payment_totals.get(mop, 0)) + flt(p.amount)

	# Opening balance per mode came from the user when they started the shift.
	opening_amounts: dict[str, float] = {}
	for bd in opening.balance_details:
		opening_amounts[bd.mode_of_payment] = flt(bd.opening_amount)

	# Build the reconciliation rows: opening + expected (filled by user later).
	all_modes = sorted(set(list(opening_amounts.keys()) + list(payment_totals.keys())))
	reconciliation = []
	for mop in all_modes:
		opening_amt = flt(opening_amounts.get(mop, 0))
		expected_amt = opening_amt + flt(payment_totals.get(mop, 0))
		reconciliation.append({
			"mode_of_payment": mop,
			"opening_amount": opening_amt,
			"expected_amount": expected_amt,
			"closing_amount": 0.0,
		})

	return {
		"invoices": invoices, "invoice_count": len(invoices),
		"grand_total": grand_total, "net_total": net_total, "total_qty": total_qty,
		"reconciliation": reconciliation,
	}


@frappe.whitelist()
def create_shift_closing_entry(pos_opening_entry: str, closing_details: str = "[]", do_submit: int = 0) -> dict:
	should_submit = cint(do_submit) or (isinstance(do_submit, str) and do_submit.lower() in ("true", "yes"))
	if isinstance(closing_details, str): closing_details = json.loads(closing_details)
	opening = frappe.get_doc("POS Opening Entry", pos_opening_entry)

	doc = frappe.new_doc("POS Closing Entry")
	doc.pos_opening_entry = pos_opening_entry
	doc.pos_profile = opening.pos_profile
	doc.company = opening.company
	doc.user = opening.user
	doc.period_start_date = opening.period_start_date
	doc.period_end_date = frappe.utils.now()
	doc.posting_date = today()
	doc.posting_time = frappe.utils.nowtime()

	invoices = frappe.db.sql("""
		SELECT si.name, si.posting_date, si.grand_total, si.net_total, si.total_qty,
		       si.customer, si.is_return
		FROM `tabSales Invoice` si
		WHERE si.owner = %s AND si.docstatus = 1
		  AND si.pos_profile = %s
		  AND (si.custom_pos_opening_entry = %s
		       OR timestamp(si.posting_date, si.posting_time) >= %s)
		ORDER BY si.creation
	""", (opening.user, opening.pos_profile, pos_opening_entry,
	      opening.period_start_date), as_dict=True)

	# We intentionally don't append invoices to POS Closing Entry's child
	# tables. Newer ERPNext validates that linked invoices must be created via
	# POS (`is_pos=1`) and have a Sales Invoice Payment row — ADMS Sales
	# Invoices are regular non-POS invoices, so the validation would refuse.
	# The shift↔invoice link still survives on the SI side via the
	# `custom_pos_opening_entry` stamp, so reports can derive the SI list
	# for any closing entry on demand. What the closing entry actually
	# *records* — the cash count per payment mode — sits in
	# payment_reconciliation, which we still populate below.

	doc.grand_total = sum(flt(inv.grand_total) for inv in invoices)
	doc.net_total = sum(flt(inv.net_total) for inv in invoices)
	doc.total_quantity = sum(flt(inv.total_qty) for inv in invoices)

	for cd in closing_details:
		doc.append("payment_reconciliation", {
			"mode_of_payment": cd.get("mode_of_payment", ""),
			"opening_amount": flt(cd.get("opening_amount", 0)),
			"expected_amount": flt(cd.get("expected_amount", 0)),
			"closing_amount": flt(cd.get("closing_amount", 0)),
			"difference": flt(cd.get("closing_amount", 0)) - flt(cd.get("expected_amount", 0)),
		})

	doc.insert()
	if should_submit:
		doc.submit()
	frappe.db.commit()
	return doc.as_dict()


# ---------------------------------------------------------------------------
# Shift report
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_shift_report_data(from_date: str, to_date: str) -> dict:
	"""Aggregated shift reconciliation report over a date range — port of
	genetest's shift_report.get_shift_report_data."""
	entries = frappe.get_all(
		"POS Closing Entry",
		filters={"docstatus": 1, "posting_date": ["between", [from_date, to_date]]},
		fields=["name", "pos_profile", "user", "posting_date",
		        "grand_total", "net_total", "total_quantity"],
		order_by="posting_date asc",
	)

	shifts = []
	total_revenue = 0.0
	total_variance = 0.0
	daily_map: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "variance": 0.0})
	payment_mode_map: dict[str, dict] = defaultdict(lambda: {"expected": 0.0, "closing": 0.0, "difference": 0.0})

	for entry in entries:
		recon_rows = frappe.get_all(
			"POS Closing Entry Detail",
			filters={"parent": entry.name},
			fields=["mode_of_payment", "opening_amount", "expected_amount",
			        "closing_amount", "difference"],
		)
		shift_variance = sum(flt(r.difference) for r in recon_rows)
		shifts.append({
			"name": entry.name, "pos_profile": entry.pos_profile,
			"user": entry.user, "posting_date": str(entry.posting_date),
			"grand_total": flt(entry.grand_total),
			"net_total": flt(entry.net_total),
			"total_quantity": flt(entry.total_quantity),
			"variance": shift_variance,
			"reconciliation": recon_rows,
		})
		total_revenue += flt(entry.grand_total)
		total_variance += shift_variance
		day = str(entry.posting_date)
		daily_map[day]["revenue"] += flt(entry.grand_total)
		daily_map[day]["variance"] += shift_variance
		for r in recon_rows:
			payment_mode_map[r.mode_of_payment]["expected"] += flt(r.expected_amount)
			payment_mode_map[r.mode_of_payment]["closing"] += flt(r.closing_amount)
			payment_mode_map[r.mode_of_payment]["difference"] += flt(r.difference)

	return {
		"summary": {
			"total_shifts": len(shifts),
			"total_revenue": total_revenue,
			"total_variance": total_variance,
		},
		"shifts": shifts,
		"daily_totals": [{"date": k, **v} for k, v in sorted(daily_map.items())],
		"payment_mode_totals": [{"mode_of_payment": k, **v} for k, v in payment_mode_map.items()],
	}


# ---------------------------------------------------------------------------
# Lightweight list endpoints for the dropdowns on the page
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_companies() -> list[dict]:
	return frappe.get_list("Company", fields=["name", "default_currency"], order_by="name", limit_page_length=0)


@frappe.whitelist()
def get_warehouses(company: str = "") -> list[str]:
	"""Picker lookup for the New Shift Profile dialog. Uses ignore_permissions
	so non-admin users (Billing Officer, Receptionist) who can create POS
	Profiles still see the warehouse list — by default they don't have
	global Warehouse read permission."""
	filters = {"company": company} if company else {}
	return frappe.db.get_all("Warehouse", filters=filters, pluck="name",
		order_by="name", limit_page_length=0, ignore_permissions=True)


@frappe.whitelist()
def get_accounts(company: str = "", account_type: str = "") -> list[str]:
	"""Picker lookup; bypasses perms — see get_warehouses."""
	filters: dict = {"is_group": 0}
	if company: filters["company"] = company
	if account_type: filters["account_type"] = account_type
	return frappe.db.get_all("Account", filters=filters, pluck="name",
		order_by="name", limit_page_length=0, ignore_permissions=True)


@frappe.whitelist()
def get_cost_centers(company: str = "") -> list[str]:
	"""Picker lookup; bypasses perms — see get_warehouses."""
	filters: dict = {"is_group": 0}
	if company: filters["company"] = company
	return frappe.db.get_all("Cost Center", filters=filters, pluck="name",
		order_by="name", limit_page_length=0, ignore_permissions=True)


@frappe.whitelist()
def get_users() -> list[dict]:
	return frappe.get_list(
		"User", filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name"], order_by="full_name", limit_page_length=0,
	)


@frappe.whitelist()
def get_modes_of_payment() -> list[str]:
	return frappe.get_list("Mode of Payment", filters={"enabled": 1}, pluck="name", order_by="name", limit_page_length=0)


# ---------------------------------------------------------------------------
# Detail / submit helpers (used by the ShiftList UI for "view" + "submit draft")
# ---------------------------------------------------------------------------

_ALLOWED_DETAIL = {"POS Profile", "POS Opening Entry", "POS Closing Entry",
                   "Sales Invoice", "Payment Entry", "Customer", "Patient",
                   "Lab Sample", "Lab Test", "Lab Report"}


@frappe.whitelist()
def get_record_detail(doctype: str, name: str) -> dict:
	if doctype not in _ALLOWED_DETAIL:
		frappe.throw(_("Invalid doctype"))
	return frappe.get_doc(doctype, name).as_dict()


_SUBMITTABLE = {"POS Opening Entry", "POS Closing Entry", "Sales Invoice", "Payment Entry"}


@frappe.whitelist()
def submit_document(doctype: str, name: str) -> dict:
	if doctype not in _SUBMITTABLE:
		frappe.throw(_("Cannot submit this document type"))
	doc = frappe.get_doc(doctype, name)
	if doc.docstatus != 0:
		frappe.throw(_("Document is not in Draft status"))
	doc.submit()
	return {"name": doc.name, "docstatus": doc.docstatus}


# ---------------------------------------------------------------------------
# Tie shift → billing
# ---------------------------------------------------------------------------

# Roles that may post invoices WITHOUT an open shift (admins / back-office
# adjustments / lab managers correcting historical data). Anyone else hits
# the shift-required gate below.
_SHIFT_EXEMPT_ROLES = {"Administrator", "System Manager", "Accounts Manager"}


def tag_sales_invoice_with_shift(doc, method=None) -> None:
	"""Validate hook — every cashier-facing Sales Invoice must be posted while
	the user has an open shift. If one is open we auto-stamp the invoice so
	the closing reconciliation picks it up; if not we throw, telling the user
	to open a shift first."""
	if doc.docstatus != 0:
		return  # only stamp drafts; existing submitted invoices are immutable
	if doc.get("custom_pos_opening_entry"):
		return  # already stamped (manual or earlier in the lifecycle)

	active = get_active_shift_for_user(frappe.session.user)
	if active:
		doc.custom_pos_opening_entry = active["name"]
		if not doc.get("pos_profile"):
			doc.pos_profile = active["pos_profile"]
		return

	# No active shift — block unless the caller is an exempt role.
	user_roles = set(frappe.get_roles(frappe.session.user))
	if user_roles & _SHIFT_EXEMPT_ROLES:
		return
	# Also skip if the invoice was raised by an automated background job
	# (e.g. recurring invoices, scheduled tasks) — those have no human user.
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_test:
		return

	frappe.throw(
		"You don't have an open shift. Open a shift from the <b>Shifts</b> screen before raising invoices, "
		"so end-of-shift reconciliation can pick this up.",
		title="Shift Required",
	)


@frappe.whitelist()
def shift_required_for_billing() -> dict:
	"""Tiny endpoint the billing UI uses to decide whether to disable the
	'create invoice' buttons. Returns {required, has_shift, active}."""
	user_roles = set(frappe.get_roles(frappe.session.user))
	exempt = bool(user_roles & _SHIFT_EXEMPT_ROLES)
	active = get_active_shift_for_user(frappe.session.user)
	return {
		"required": not exempt,
		"has_shift": bool(active),
		"active": active,
	}
