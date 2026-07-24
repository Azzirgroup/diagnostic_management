"""Stop the Kanonas Diagnosis workspace throwing a Permission Error on open.

The "Diagnostic Reports" shortcut carried a count badge filter:

    stats_filter = {"status": ["in", ["Draft", "Pending"]]}

Frappe evaluates that server-side to render the badge. `Diagnostic Report.status`
is permlevel-restricted in Healthcare, so for any user without read access at
that permlevel the query aborts with:

    You do not have permission to access field: Diagnostic Report.status

The whole workspace load fails on it, so the user sees the dialog every single
time they open the page — the shortcut's badge takes the entire page down.

Dropping the filter keeps the shortcut (it still opens the Diagnostic Report
list, where per-user permissions apply normally) and just loses the count. That
is strictly better than widening permlevel access on a clinical doctype to make
a badge render.

Idempotent: only touches shortcuts that still carry a `status` filter.
"""

import json

import frappe

WORKSPACE = "Kanonas Diagnosis"
# Only Diagnostic Report is permlevel-restricted; the other shortcuts on this
# workspace filter on doctypes we own, so their badges are left working.
TARGET_DOCTYPES = ("Diagnostic Report",)


def execute():
	if not frappe.db.exists("Workspace", WORKSPACE):
		return

	ws = frappe.get_doc("Workspace", WORKSPACE)
	changed = False
	for row in ws.get("shortcuts") or []:
		if row.get("link_to") not in TARGET_DOCTYPES:
			continue
		raw = row.get("stats_filter") or ""
		if not raw:
			continue
		# Only strip filters that actually reference the restricted field —
		# leave anything else the lab may have configured by hand.
		try:
			parsed = json.loads(raw)
		except Exception:
			parsed = None
		if isinstance(parsed, dict) and "status" not in parsed:
			continue
		row.stats_filter = ""
		changed = True

	if not changed:
		return

	ws.flags.ignore_permissions = True
	ws.save()
	frappe.db.commit()
	print(f"  [patch] cleared permlevel-restricted stats_filter on {WORKSPACE} shortcuts")
