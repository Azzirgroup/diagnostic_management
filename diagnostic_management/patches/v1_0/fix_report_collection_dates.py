"""Auto-correct Lab Reports whose collection date is later than their creation.

A reused Sample Collection gets re-collected by later orders, and older reports
read that value live — so their printed collection date ends up AFTER the report
was generated. Going forward this is frozen at build time
(results._frozen_collection_datetime); this patch repairs the reports already
broken, once, on migrate.

It delegates to collection_date_fix.backfill(dry_run=0), which:
  * touches ONLY reports where collection_datetime > creation (provably wrong)
  * recovers the REAL time from version history (falls back to report creation)
  * clamps so a repaired value can never itself be after the report
  * writes a backup file first, so collection_date_fix.revert() can undo it

Idempotent: once corrected, a report's collection date is <= its creation, so a
re-run finds nothing. Never raises into the migrate — a failure is logged and
the rest of the migrate continues.
"""

import frappe


def execute():
	try:
		from diagnostic_management.utils.collection_date_fix import backfill

		result = backfill(dry_run=0, show=0)
		n = result.get("broken_reports", 0)
		if n:
			print(f"  [patch] corrected collection date on {n} Lab Report(s); "
			      f"backup at {result.get('backup_file')} (revert via collection_date_fix.revert)")
	except Exception:
		frappe.log_error(
			title="fix_report_collection_dates patch failed",
			message=frappe.get_traceback(),
		)
