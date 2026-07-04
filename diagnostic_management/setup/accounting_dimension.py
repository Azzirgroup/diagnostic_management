"""Register `Branch` as an ERPNext Accounting Dimension.

Why this and not Custom Fields:
    ERPNext's Accounting Dimension feature was built exactly for this — adding
    a reporting axis (Project / Branch / Region / …) to every accounting
    document. Once we register `Branch` as a dimension, ERPNext auto-creates
    the `branch` Custom Field on EVERY financial doctype it knows about,
    *including GL Entry*. P&L, Balance Sheet, General Ledger, Trial Balance
    and Profit and Loss Statement reports all gain a Branch filter
    automatically — no custom report code needed.

Mandatory vs optional:
    We register the dimension as NON-mandatory. Marking it mandatory would
    break historical posting (every backfilled GL Entry would fail re-save).
    The Director's dashboard treats `branch IS NULL` as "Unbranched / Head
    Office" so legacy data still shows up.

Idempotency:
    Safe to call repeatedly. The function bails if a Branch dimension already
    exists with the same document_type and is not disabled.
"""

from __future__ import annotations

import frappe


def ensure_branch_accounting_dimension() -> None:
	"""Idempotent — creates the Accounting Dimension once, and always
	re-runs ERPNext's column fan-out so the `branch` column is present on
	every accounting table (Budget, GL Entry, Sales Invoice, …).

	The fan-out re-run is necessary because Accounting Dimension.insert()
	fires the fan-out via `after_insert`, but that only runs on the FIRST
	insert. Sites where the record survives a DB rebuild (e.g. our earlier
	restore workflow) end up with the record present but NO `branch`
	columns on the tables, which then 417s on invoice submit inside
	ERPNext's Budget controller.
	"""
	# Branch doctype is part of HRMS; if it isn't installed here, do nothing.
	if not frappe.db.exists("DocType", "Branch"):
		return
	# ERPNext provides Accounting Dimension; bail out cleanly if absent.
	if not frappe.db.exists("DocType", "Accounting Dimension"):
		return

	existing_name = frappe.db.get_value(
		"Accounting Dimension", {"document_type": "Branch"}, "name",
	)
	if existing_name:
		# Re-enable if the record was previously disabled.
		if frappe.db.get_value("Accounting Dimension", existing_name, "disabled"):
			frappe.db.set_value("Accounting Dimension", existing_name, "disabled", 0)
		# Re-run the column fan-out — cheap when columns already exist
		# (ALTER IF NOT EXISTS semantics on the ERPNext side), essential
		# when they don't.
		_ensure_columns(existing_name)
		frappe.db.commit()
		return

	doc = frappe.new_doc("Accounting Dimension")
	doc.document_type = "Branch"
	doc.label = "Branch"
	doc.fieldname = "branch"
	doc.disabled = 0
	# `insert()` triggers ERPNext's `after_insert` on Accounting Dimension,
	# which fans out and creates the `branch` Custom Field on every relevant
	# doctype (Sales Invoice, Purchase Invoice, Payment Entry, Journal Entry,
	# Journal Entry Account, GL Entry, Asset, Stock Entry, Subscription, …).
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
	print("  [branch-dim] registered Branch as Accounting Dimension "
	      "(custom field created on all financial doctypes incl. GL Entry)")


def _ensure_columns(dim_name: str) -> None:
	"""Re-run ERPNext's per-doctype fan-out for the given Accounting
	Dimension. Safe to call repeatedly — the underlying `create_custom_field`
	upserts and the column ALTERs are `IF NOT EXISTS`-guarded on the
	ERPNext side."""
	try:
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			make_dimension_in_accounting_doctypes,
		)
	except Exception:
		# ERPNext not on this bench — nothing we can do.
		return
	doc = frappe.get_doc("Accounting Dimension", dim_name)
	try:
		make_dimension_in_accounting_doctypes(doc)
	except Exception:
		# Never fail migrate on this — a partial fan-out is recoverable
		# via bench console and doesn't break existing data.
		frappe.log_error(title="branch-dim fan-out failed")
