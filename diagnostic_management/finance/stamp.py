"""Auto-stamp the `branch` Accounting Dimension on financial documents.

ERPNext's Accounting Dimension feature adds the `branch` field to every
financial doctype (see setup/accounting_dimension.py), and when an SI/PE/PI/JE
is submitted ERPNext propagates the parent's dimension values to each GL
Entry row. So tagging the parent voucher tags the whole posting.

Stamp precedence is the same for every doctype below (SI / PE / PI / JE):

  1. Explicit value already on the doc — never overwrite a user choice.
  2. Per-user "acts-as" override (set_active_branch) — top of the implicit
     ladder because it's an admin's explicit "post as Branch X" action.
  3. **User.branch** — the persistent tag on the requesting User. This is
     the primary source of truth: an UMC-tagged user posts UMC invoices.
  4. **Open POS shift's branch** — only if User.branch is empty. Covers
     users who aren't permanently assigned to a branch but are working a
     branch-tagged counter for this shift.
  5. None — "Unbranched / Head Office" in the Director's dashboard.

We do NOT look at Patient.branch on the invoice — revenue attribution
follows the *cashier's* branch, not the patient's home branch. (A PMC-
registered patient billed by a UMC cashier is UMC revenue, by design.)


A return of None at the bottom is fine — `branch IS NULL` simply means
"unbranched / head office" in the Director's dashboard, so the doc still
posts cleanly. The Accounting Dimension is registered as optional, not
mandatory, precisely so historical data keeps working.
"""

from __future__ import annotations

import frappe


# ---------------------------------------------------------------------------
# Public hook entrypoints (registered in hooks.doc_events)
# ---------------------------------------------------------------------------

def stamp_sales_invoice(doc, method=None):
	if doc.get("branch"):
		return
	doc.branch = _effective_user_branch()


def stamp_payment_entry(doc, method=None):
	if doc.get("branch"):
		return
	doc.branch = _effective_user_branch()


def stamp_purchase_invoice(doc, method=None):
	if doc.get("branch"):
		return
	doc.branch = _effective_user_branch()


def stamp_journal_entry(doc, method=None):
	if doc.get("branch"):
		return
	doc.branch = _effective_user_branch()


def _effective_user_branch() -> str | None:
	"""Resolve the branch to stamp on a financial doc in the live request:
	   override > User.branch > open POS shift > None.

	NOTE: we intentionally diverge from `branches._user_branch()` here.
	That helper (used for viewing/permission scoping) puts the open shift
	above User.branch because a cashier covering another counter should
	SEE that counter's data. For BILLING attribution we flip it: a user's
	permanent branch tag is authoritative, the shift only matters as a
	fallback when User.branch is empty.
	"""
	try:
		from diagnostic_management.api.branches import (
			_active_override, _shift_branch,
		)
		user = frappe.session.user
		if not user or user == "Guest":
			return None
		ov = _active_override(user)
		if ov:
			return ov
		tagged = frappe.db.get_value("User", user, "branch") or None
		if tagged:
			return tagged
		return _shift_branch(user) or None
	except Exception:
		# Defensive: never fail a billing insert because branch resolution
		# tripped (e.g. session=None during a scheduled job).
		return None


# ---------------------------------------------------------------------------
# Precedence helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# One-shot backfill — populates branch on historical financial docs that
# have NULL because they were posted before the Accounting Dimension landed.
# Called from after_migrate; idempotent (only fills rows where branch IS NULL).
# ---------------------------------------------------------------------------

def backfill_branch_on_existing_docs() -> None:
	"""Walk Sales Invoice / Payment Entry / Purchase Invoice / Journal Entry
	rows where branch IS NULL and stamp it from the document owner's
	User.branch. Idempotent — only touches rows with branch IS NULL. We use
	direct SQL UPDATE (no doc.save) so submitted documents aren't re-
	validated and GL Entry rows are untouched; the dimension is purely
	informational on past postings, future ones inherit normally via the
	doc_events.

	Precedence mirrors the live auto-stamp: User.branch only. We do NOT
	walk Patient.branch or POS Profile.branch in backfill — those signals
	weren't authoritative when the original doc posted, and stamping them
	retroactively would misattribute revenue. Rows where the owner has
	no branch stay NULL (= "Unbranched" in the Director's view).
	"""
	updated = {"Sales Invoice": 0, "Payment Entry": 0, "Purchase Invoice": 0, "Journal Entry": 0}

	# Pre-cache owner → branch so we don't hit the User table N times.
	owner_branch_cache: dict[str, str | None] = {}
	def _owner_branch(user: str | None) -> str | None:
		if not user or user in ("Administrator", "Guest"):
			return None
		if user not in owner_branch_cache:
			owner_branch_cache[user] = frappe.db.get_value("User", user, "branch") or None
		return owner_branch_cache[user]

	for dt in ("Sales Invoice", "Payment Entry", "Purchase Invoice", "Journal Entry"):
		# Skip silently if the dimension hasn't fanned the column to this dt
		# (Journal Entry's branch field may live only on the child).
		cols = {c[0] for c in frappe.db.sql(f"SHOW COLUMNS FROM `tab{dt}`")}
		if "branch" not in cols:
			continue
		for r in frappe.db.sql(
			f"""SELECT name, owner FROM `tab{dt}` WHERE branch IS NULL OR branch = ''""",
			as_dict=True,
		):
			b = _owner_branch(r["owner"])
			if b:
				frappe.db.set_value(dt, r["name"], "branch", b, update_modified=False)
				updated[dt] += 1

	if any(updated.values()):
		frappe.db.commit()
		summary = ", ".join(f"{k}={v}" for k, v in updated.items() if v)
		print(f"  [branch-backfill] stamped: {summary}")
