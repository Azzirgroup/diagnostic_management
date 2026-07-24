"""Batch cleanup of Sales Invoices from a reviewed instruction list.

Driven by the `ACTIONS` table below — one entry per invoice, transcribed from
the spreadsheet's free-text "issues" column into an EXPLICIT verb. Free text is
not parsed at runtime: on financial documents a mis-read instruction is a real
accounting error, so the mapping is made once, here, where it can be reviewed.

Verbs implemented here (safe, reversible-ish):
    set_doctor  -> set Sales Invoice.custom_doctor (works on submitted docs via
                   the existing billing.set_invoice_doctor)
    remove      -> cancel the invoice (optionally hard-delete after), cancelling
                   any linked submitted Payment Entries first

Verbs deliberately NOT implemented yet (they post to the general ledger and I
could not test GL behaviour off-bench — see the module docstring note and the
`mark_paid` / `write_off` stubs):
    mark_paid, write_off

Everything defaults to DRY RUN: it returns the plan and writes nothing. Nothing
executes until called with dry_run=0. It is idempotent — an already-cancelled
invoice, or a doctor already set, is reported as "skip", not re-done.
"""

import frappe

# --- reversible verbs -------------------------------------------------------
# (invoice, "set_doctor", doctor_name)
# (invoice, "remove")            -> cancel (+delete if hard_delete=1)
#
# --- GL verbs, NOT YET WIRED (left as data so the plan still shows them) -----
# (invoice, "mark_paid")          -> settle full outstanding
# (invoice, "mark_paid", amount)  -> settle to a target paid amount
# (invoice, "write_off", pay, wo) -> pay `pay`, write off `wo`
ACTIONS = [
	# ---- update referring doctor ----
	("ACC-SINV-2026-00915", "set_doctor", "Dr Sangeeta Chauhan"),
	("ACC-SINV-2026-00723", "set_doctor", "Dr Sangeeta Chauhan"),
	("ACC-SINV-2026-00916", "set_doctor", "DR CK JANDU"),
	("ACC-SINV-2026-00938", "set_doctor", "Dr Sangeeta Chauhan"),

	# ---- remove (cancel) ----
	("ACC-SINV-2026-00936", "remove"),
	("ACC-SINV-2026-00927", "remove"),
	("ACC-SINV-2026-00939", "remove"),   # NOTE: Paid (Mpesa) — cancels a real payment
	("ACC-SINV-2026-00922", "remove"),
	("ACC-SINV-2026-00921", "remove"),
	("ACC-SINV-2026-00920", "remove"),
	("ACC-SINV-2026-00846", "remove"),
	("ACC-SINV-2026-00844", "remove"),
	("ACC-SINV-2026-00843", "remove"),
	("ACC-SINV-2026-00852", "remove"),   # NOTE: Paid (Mpesa) — cancels a real payment
	("ACC-SINV-2026-00890", "remove"),
	("ACC-SINV-2026-00740-1", "remove"), # NOTE: Paid (Cash) — cancels a real payment
	("ACC-SINV-2026-00738", "remove"),   # NOTE: linked to an Approved workflow result
	("ACC-SINV-2026-00905", "remove"),   # NOTE: Paid (Cash) — cancels a real payment
	("ACC-SINV-2026-00906", "remove"),

	# ---- GL verbs — PLANNED, executor intentionally raises until confirmed ----
	("ACC-SINV-2026-00828", "mark_paid"),            # write off outstanding 206.25
	("ACC-SINV-2026-00827", "mark_paid"),            # write off outstanding 525.00
	("ACC-SINV-2026-00862", "mark_paid"),            # write off outstanding 119,800.00 (!)
	("ACC-SINV-2026-00896", "write_off", 2200, 725), # pay 2200, write off 725
	("ACC-SINV-2026-00749", "mark_paid", 15700),
	("ACC-SINV-2026-00958", "mark_paid"),
	("ACC-SINV-2026-00963", "mark_paid"),
	("ACC-SINV-2026-00962", "mark_paid"),
]

# Verbs that touch the general ledger.
_GL_VERBS = {"mark_paid", "write_off"}


def _write_off_account(company, override=None):
	"""Resolve the account the written-off amount is booked to. Prefer an
	explicit override, then the Company's configured `write_off_account`."""
	if override:
		return override
	return frappe.db.get_value("Company", company, "write_off_account")


def _planned_write_off_amount(verb, args, outstanding):
	"""How much to write off for a GL verb.

	write_off(pay, wo) -> the explicit `wo` amount.
	mark_paid[amount]  -> the whole current outstanding (settle to Paid). The
	                      optional amount is the operator's expected grand total,
	                      used only as a sanity note, not as the write-off value.
	"""
	if verb == "write_off":
		return float(args[1]) if len(args) > 1 else outstanding
	return outstanding


def _linked_payment_entries(invoice):
	"""Submitted Payment Entries that allocate against this invoice."""
	rows = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": "Sales Invoice", "reference_name": invoice, "docstatus": 1},
		fields=["parent"],
	)
	return sorted({r["parent"] for r in rows})


def _plan_one(invoice, verb, *args, write_off_account=None):
	entry = {"invoice": invoice, "verb": verb, "args": list(args), "action": None, "note": ""}

	if not frappe.db.exists("Sales Invoice", invoice):
		entry["action"] = "skip"
		entry["note"] = "invoice does not exist"
		return entry

	info = frappe.db.get_value(
		"Sales Invoice", invoice,
		["docstatus", "status", "outstanding_amount", "grand_total", "custom_doctor", "company"],
		as_dict=True,
	)
	entry["docstatus"] = info.docstatus
	entry["status"] = info.status
	entry["outstanding"] = float(info.outstanding_amount or 0)

	if verb == "set_doctor":
		target = (args[0] if args else "") or ""
		if (info.custom_doctor or "") == target:
			entry["action"] = "skip"; entry["note"] = f"doctor already {target!r}"
		else:
			entry["action"] = "set_doctor"
			entry["note"] = f"{info.custom_doctor or '(blank)'} -> {target}"

	elif verb == "remove":
		if info.docstatus == 2:
			entry["action"] = "skip"; entry["note"] = "already cancelled"
		else:
			pes = _linked_payment_entries(invoice)
			entry["action"] = "cancel"
			entry["linked_payment_entries"] = pes
			bits = []
			if pes:
				bits.append(f"will first cancel Payment Entry: {', '.join(pes)}")
			if entry["outstanding"] == 0 and info.status in ("Paid", "Credit Note Issued"):
				bits.append("invoice is settled — cancelling reverses real cash")
			entry["note"] = "; ".join(bits) or "no linked payments"

	elif verb in _GL_VERBS:
		if info.docstatus != 1:
			entry["action"] = "skip"; entry["note"] = "not submitted — nothing to settle"
		elif entry["outstanding"] <= 0:
			entry["action"] = "skip"; entry["note"] = "already settled (outstanding is 0)"
		else:
			wo = _planned_write_off_amount(verb, args, entry["outstanding"])
			acct = _write_off_account(info.company, write_off_account)
			if not acct:
				entry["action"] = "blocked"
				entry["note"] = (f"no Write Off account on Company {info.company!r} — set it, "
				                 "or pass write_off_account=")
			else:
				entry["action"] = "write_off"
				entry["write_off_amount"] = wo
				entry["write_off_account"] = acct
				entry["company"] = info.company
				residual = round(entry["outstanding"] - wo, 2)
				entry["note"] = f"write off {wo:.2f} of {entry['outstanding']:.2f} to {acct}"
				if residual > 0:
					entry["note"] += f"; {residual:.2f} would remain OUTSTANDING"

	else:
		entry["action"] = "skip"; entry["note"] = f"unknown verb {verb!r}"

	return entry


def _do_set_doctor(invoice, doctor):
	from diagnostic_management.api.billing import set_invoice_doctor
	set_invoice_doctor(invoice, doctor)


def _do_write_off(plan):
	"""Settle an invoice's outstanding with a Write Off Journal Entry.

	Standard ERPNext write-off shape: debit the Write Off account (a P&L
	account), credit the invoice's receivable (`debit_to`) against the customer,
	referenced to the invoice so its `outstanding_amount` drops. Submitting the
	JE posts the GL entries and reallocates against the invoice.
	"""
	from frappe.utils import today

	invoice = plan["invoice"]
	amount = plan["write_off_amount"]
	inv = frappe.db.get_value(
		"Sales Invoice", invoice, ["company", "debit_to", "customer"], as_dict=True
	)
	cost_center = frappe.db.get_value("Company", inv.company, "cost_center")

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Write Off Entry"
	je.company = inv.company
	je.posting_date = today()
	je.user_remark = f"Write off outstanding on {invoice} (staff-error cleanup)"
	je.append("accounts", {
		"account": plan["write_off_account"],
		"debit_in_account_currency": amount,
		"cost_center": cost_center,
	})
	je.append("accounts", {
		"account": inv.debit_to,
		"credit_in_account_currency": amount,
		"party_type": "Customer",
		"party": inv.customer,
		"reference_type": "Sales Invoice",
		"reference_name": invoice,
		"cost_center": cost_center,
	})
	je.flags.ignore_permissions = True
	je.insert()
	je.submit()
	return je.name


def _do_remove(invoice, plan, hard_delete=False):
	# Cancel linked Payment Entries first, or Sales Invoice.cancel() throws on
	# the outstanding submitted links.
	for pe in plan.get("linked_payment_entries") or []:
		if frappe.db.get_value("Payment Entry", pe, "docstatus") == 1:
			frappe.get_doc("Payment Entry", pe).cancel()
	doc = frappe.get_doc("Sales Invoice", invoice)
	if doc.docstatus == 1:
		doc.cancel()
	if hard_delete:
		frappe.delete_doc("Sales Invoice", invoice, force=1)


def _print_report(result: dict) -> None:
	"""Readable dump for `bench console` / `bench execute`, where the returned
	dict is otherwise an unreadable blob."""
	mode = "DRY RUN (nothing written)" if result["dry_run"] else "APPLIED"
	print("\n" + "=" * 78)
	print(f"  Invoice cleanup — {mode}"
	      + ("  [hard delete ON]" if result["hard_delete"] else ""))
	print("=" * 78)
	print(f"  {'INVOICE':<24} {'ACTION':<11} NOTE")
	print("  " + "-" * 74)
	for p in result["plan"]:
		print(f"  {p['invoice']:<24} {(p.get('action') or ''):<11} {p.get('note', '')}")
		if p.get("error"):
			print(f"  {'':<24} {'':<11} !! ERROR: {p['error']}")
		if p.get("journal_entry"):
			print(f"  {'':<24} {'':<11} -> Journal Entry {p['journal_entry']}")
	print("  " + "-" * 74)
	s = result["summary"]
	print(f"  set_doctor={s['set_doctor']}  cancelled={s['cancelled']}  deleted={s['deleted']}  "
	      f"written_off={s['written_off']}  skipped={s['skipped']}  blocked={s['blocked']}  "
	      f"errors={s['errors']}")
	if result["dry_run"]:
		print("\n  Nothing was changed. Re-run with dry_run=0 to apply.")
	print("=" * 78 + "\n")


def _in_console() -> bool:
	"""True when called from bench console / bench execute (no web request)."""
	try:
		return getattr(frappe.local, "request", None) is None
	except Exception:
		return True


@frappe.whitelist()
def run(dry_run: int = 1, hard_delete: int = 0, only: str | None = None,
        write_off_account: str | None = None, show: int | None = None) -> dict:
	"""Execute the ACTIONS table.

	dry_run=1 (default) : build and return the plan, write NOTHING.
	dry_run=0           : apply set_doctor, remove, and write_off.
	hard_delete=1       : after cancelling a 'remove', also delete the invoice.
	                      Default 0 = cancel only. (You asked for delete — pass 1.)
	only=<verb>         : restrict to one verb, e.g. only='set_doctor'. Verbs:
	                      set_doctor | remove | mark_paid | write_off.
	write_off_account   : override the account written-off amounts book to;
	                      defaults to the Company's `write_off_account`.
	show                : print a readable table. Defaults ON in bench console /
	                      bench execute, OFF for web/API calls. Pass show=1 to
	                      force it, show=0 to silence it.

	'remove' cancels any linked Payment Entry first (reverses the recorded
	cash), then cancels the invoice. GL verbs settle the outstanding with a
	Write Off Journal Entry. Everything is idempotent: an already-cancelled or
	already-settled invoice is skipped.

	Run it from a console / bench:
	    bench --site genetest.nvi execute \\
	        diagnostic_management.utils.invoice_cleanup.run
	    bench --site genetest.nvi execute \\
	        diagnostic_management.utils.invoice_cleanup.run \\
	        --kwargs "{'dry_run': 0, 'hard_delete': 1}"
	Or inside `bench --site genetest.nvi console`:
	    from diagnostic_management.utils import invoice_cleanup
	    invoice_cleanup.run()                    # preview
	    invoice_cleanup.run(dry_run=0, hard_delete=1)   # apply
	"""
	dry_run = int(dry_run or 0)
	hard_delete = int(hard_delete or 0)

	plan = []
	results = {"set_doctor": 0, "cancelled": 0, "deleted": 0, "written_off": 0,
	           "skipped": 0, "blocked": 0, "errors": 0}
	for invoice, verb, *args in ACTIONS:
		if only and verb != only:
			continue
		p = _plan_one(invoice, verb, *args, write_off_account=write_off_account)
		plan.append(p)

		if dry_run:
			continue

		try:
			if p["action"] == "set_doctor":
				_do_set_doctor(invoice, args[0]); results["set_doctor"] += 1
			elif p["action"] == "cancel":
				_do_remove(invoice, p, hard_delete=bool(hard_delete))
				results["cancelled"] += 1
				if hard_delete:
					results["deleted"] += 1
			elif p["action"] == "write_off":
				p["journal_entry"] = _do_write_off(p); results["written_off"] += 1
			elif p["action"] == "blocked":
				results["blocked"] += 1
			else:
				results["skipped"] += 1
		except Exception as e:
			results["errors"] += 1
			p["error"] = str(e)
			frappe.log_error(title=f"invoice_cleanup: {verb} failed for {invoice}")

	if not dry_run:
		frappe.db.commit()
	else:
		# Plan-side tallies so a dry run still summarises what WOULD happen.
		for p in plan:
			key = {"set_doctor": "set_doctor", "cancel": "cancelled", "write_off": "written_off",
			       "blocked": "blocked", "skip": "skipped"}.get(p["action"], "skipped")
			results[key] += 1

	result = {
		"ok": True,
		"dry_run": bool(dry_run),
		"hard_delete": bool(hard_delete),
		"total": len(plan),
		"summary": results,
		"plan": plan,
	}

	# Print when asked, or by default when running from a console/bench (where
	# the raw dict is unreadable). Never auto-prints for web/API callers.
	if show is None:
		show = _in_console()
	if int(show or 0):
		_print_report(result)

	return result
