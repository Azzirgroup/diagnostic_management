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
	"""Idempotent — creates the Accounting Dimension once."""
	# Branch doctype is part of HRMS; if it isn't installed here, do nothing.
	if not frappe.db.exists("DocType", "Branch"):
		return
	# ERPNext provides Accounting Dimension; bail out cleanly if absent.
	if not frappe.db.exists("DocType", "Accounting Dimension"):
		return

	existing = frappe.db.get_value(
		"Accounting Dimension",
		{"document_type": "Branch"},
		["name", "disabled"],
		as_dict=True,
	)
	if existing:
		if existing.get("disabled"):
			frappe.db.set_value("Accounting Dimension", existing["name"], "disabled", 0)
			frappe.db.commit()
			print("  [branch-dim] re-enabled existing Branch accounting dimension")
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
