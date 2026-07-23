"""One-shot: rename Patients whose `name` was set to the patient's own name
(bypassed naming series) to a proper v15-style code.

Call signature — invoke from `bench --site <s> execute` with dry_run flag:

    bench --site genetest.nvi.frappe.cloud execute \
      diagnostic_management.patches.rename_patients_to_series.run \
      --kwargs "{'dry_run': True}"

Then flip `dry_run` to False to actually rename.

Behaviour:
  * Finds ONLY Patients where `name == patient_name` — i.e. the autoname
    was bypassed and the record is keyed by the human name (like
    "ZAIN MOHAMED"). Every other patient is left alone, INCLUDING those
    with unfamiliar code prefixes (KE-TEST-..., PT-..., HLC-PAT-...) —
    those are considered intentional and out of scope.
  * Picks the target series from Patient.branch: UMC-branch → KE-UMC-,
    everything else → KE-PMC-.
  * Continues from MAX(series) so no collisions with existing v15 codes.
  * Uses `frappe.rename_doc(force=True, merge=False)` — Frappe cascades FK
    updates across every linking doctype (Lab Test, Sample Collection,
    Sales Invoice, etc.) inside a single transaction.
  * Idempotent: after the rename, `name != patient_name` so the row is
    excluded from a re-run.

Prints a per-row report (dry-run or actual) so the operator can audit
before committing."""
from __future__ import annotations

import re

import frappe


PMC_RE = re.compile(r"^KE-PMC-\d{4,}$")
UMC_RE = re.compile(r"^KE-UMC-\d{4,}$")


def run(dry_run: bool = True) -> dict:
	frappe.set_user("Administrator")
	summary = {"scanned": 0, "renamed": 0, "skipped": 0, "errors": 0, "actions": []}

	# Seed counters from current MAX per prefix so new codes never collide.
	next_seq: dict[str, int] = {
		"KE-PMC-": _next_seq_for("KE-PMC-"),
		"KE-UMC-": _next_seq_for("KE-UMC-"),
	}
	print(f"[start] dry_run={dry_run}  next_seq={next_seq}", flush=True)

	# Candidates: ONLY patients whose primary key equals their patient_name
	# — that's the fingerprint of an insert that bypassed the naming series.
	# BINARY comparison so casing differences still surface as a mismatch
	# (patient_name 'Zain Mohamed' vs name 'ZAIN MOHAMED' → not a match →
	# skipped, which is what we want since we can't know which spelling wins).
	rows = frappe.db.sql("""
		SELECT name, patient_name, branch
		FROM `tabPatient`
		WHERE BINARY name = BINARY patient_name
		ORDER BY creation ASC
	""", as_dict=True)

	for r in rows:
		summary["scanned"] += 1
		old_name = r["name"]

		# Extra defence: even though the SQL filter should have caught this,
		# a properly-coded patient must never fall through to rename.
		if PMC_RE.match(old_name) or UMC_RE.match(old_name):
			summary["skipped"] += 1
			continue

		prefix = "KE-UMC-" if (r.get("branch") or "").lower().find("umc") >= 0 \
		         else "KE-PMC-"
		seq = next_seq[prefix]
		new_name = f"{prefix}{seq:08d}"
		next_seq[prefix] = seq + 1

		action = {"old": old_name, "new": new_name, "branch": r.get("branch") or "-"}
		if dry_run:
			summary["actions"].append(action)
			print(f"  [dry] {old_name!r:35s}  →  {new_name}   (branch={action['branch']})",
			      flush=True)
			continue

		try:
			# rename_doc doesn't accept ignore_permissions (it's an admin
			# operation — permission is checked via `force` and the caller
			# being System Manager, which frappe.set_user('Administrator')
			# above satisfies).
			frappe.rename_doc("Patient", old_name, new_name,
			                  force=True, merge=False,
			                  show_alert=False, rebuild_search=False)
			# Advance the Frappe Series counter so future auto-inserts don't
			# collide. `tabSeries` is keyed by the prefix; increment `current`
			# to the seq we just used.
			_bump_series(prefix, seq)
			summary["renamed"] += 1
			summary["actions"].append(action)
			print(f"  [ok]  {old_name!r:35s}  →  {new_name}", flush=True)
		except Exception as e:
			summary["errors"] += 1
			print(f"  [!!]  {old_name!r:35s}  RENAME FAILED: {type(e).__name__}: {e}",
			      flush=True)
			# Roll back this one rename attempt but keep going for others.
			frappe.db.rollback()

	if not dry_run:
		frappe.db.commit()

	print(f"\n[done] scanned={summary['scanned']}  renamed={summary['renamed']}  "
	      f"skipped={summary['skipped']}  errors={summary['errors']}", flush=True)
	return summary


def _next_seq_for(prefix: str) -> int:
	"""MAX(series-suffix) + 1, or 1 if no rows carry this prefix yet.
	Extracts the trailing digits and takes the max as an integer."""
	rows = frappe.db.sql("""
		SELECT MAX(CAST(SUBSTRING(name, %(offset)s) AS UNSIGNED)) AS max_seq
		FROM `tabPatient` WHERE name LIKE %(pat)s
	""", {"offset": len(prefix) + 1, "pat": f"{prefix}%"}, as_dict=True)
	current = int(rows[0]["max_seq"] or 0) if rows else 0
	return current + 1


def _bump_series(prefix: str, up_to: int) -> None:
	"""Advance `tabSeries.current` for this prefix so Frappe's next auto-
	insert doesn't hand out an already-used sequence number. INSERT ON
	DUPLICATE KEY so the row is created if absent."""
	frappe.db.sql("""
		INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)
		ON DUPLICATE KEY UPDATE current = GREATEST(current, VALUES(current))
	""", (prefix, up_to))
