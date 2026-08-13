"""Backfill + revert for Lab Reports showing an impossible collection date.

A Sample Collection is reused across orders for a patient + sample type; each
new order clears and re-stamps its single `collected_time`. Older reports read
that value live, so a later order's collection time leaks onto them — the print
then shows a collection date AFTER the report was generated.

Going forward this is fixed at build time (results._frozen_collection_datetime).
This module repairs the reports already broken, recovering the REAL collection
time from Frappe's version history (the value the sample held when the report
was created), falling back to the report's own creation only when no history
exists. Every change is backed up so `revert()` can undo it exactly.

SAFE BY DESIGN:
  * touches ONLY reports where collection_datetime is provably wrong
    (later than the report's own creation) — correct reports are never touched
  * dry-run by default: shows the plan, writes nothing
  * clamps so a repaired value can never itself be after the report
  * writes a backup file first; revert() restores the pre-change values

Run it from a browser (logged in) or bench:
  /api/method/diagnostic_management.utils.collection_date_fix.backfill          (preview)
  /api/method/diagnostic_management.utils.collection_date_fix.backfill?dry_run=0 (apply)
  /api/method/diagnostic_management.utils.collection_date_fix.revert            (preview undo)
  /api/method/diagnostic_management.utils.collection_date_fix.revert?dry_run=0  (undo)
"""

import json
import os

import frappe

_BACKUP_FILE = "collection_datetime_backup.json"


def _to_datetime(value):
	"""Parse a datetime from EITHER ISO (YYYY-MM-DD, from DB fields) OR Frappe's
	version-display format (DD-MM-YYYY, how `tabVersion` stores changes here).

	ISO patterns are tried first because a 4-digit-year-first string is
	unambiguous. Only then do we try day-first (DD-MM-YYYY) — parsing it
	EXPLICITLY, never by a guessing parser, so "06-08-2026" can't be misread as
	8-June instead of 6-August. Returns a datetime, or None if unparseable.
	"""
	if not value:
		return None
	from datetime import datetime as _dt

	if isinstance(value, _dt):
		return value
	s = str(value).strip()
	for fmt in (
		"%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
		"%d-%m-%Y %H:%M:%S.%f", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
	):
		try:
			return _dt.strptime(s, fmt)
		except ValueError:
			continue
	return None


def _backup_path():
	return frappe.get_site_path("private", "files", _BACKUP_FILE)


def _load_backup():
	path = _backup_path()
	if os.path.exists(path):
		try:
			with open(path) as f:
				return json.load(f)
		except Exception:
			return {}
	return {}


def _save_backup(data):
	with open(_backup_path(), "w") as f:
		json.dump(data, f, indent=2, default=str)


def _collected_time_as_of(sample, as_of):
	"""The sample's `collected_time` as it was at `as_of`, from version history.

	Walks `tabVersion` for the Sample Collection, tracks every change to
	`collected_time`, and returns the value in effect at `as_of` — i.e. the
	`new` value of the last change at or before `as_of`, or the value that
	preceded the first recorded change. None if history has nothing.
	"""
	from frappe.utils import get_datetime

	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": "Sample Collection", "docname": sample},
		fields=["data", "creation"],
		order_by="creation asc",
	)
	baseline = None          # value before the first recorded change
	changes = []             # [(version_creation, new_value), ...] in order
	for v in versions:
		try:
			data = json.loads(v.data)
		except Exception:
			continue
		for row in data.get("changed", []) or []:
			if row and len(row) >= 3 and row[0] == "collected_time":
				old_val, new_val = row[1], row[2]
				if baseline is None:
					baseline = old_val
				changes.append((get_datetime(v.creation), new_val))
	if not changes:
		return None

	as_of_dt = get_datetime(as_of)
	value = baseline
	for cdt, new_val in changes:
		if cdt <= as_of_dt:
			value = new_val
		else:
			break
	return value or None


def _plan_rows(limit):
	"""Reports whose collection_datetime is impossibly after their creation."""
	return frappe.db.sql(
		"""
		SELECT name, creation, collection_datetime
		FROM `tabLab Report`
		WHERE collection_datetime IS NOT NULL
		  AND collection_datetime > creation
		ORDER BY creation DESC
		LIMIT %s
		""",
		(int(limit),),
		as_dict=True,
	)


def _print(title, rows, cols):
	print("\n" + "=" * 72)
	print(f"  {title}")
	print("=" * 72)
	for r in rows[:200]:
		print("  " + "  |  ".join(str(r.get(c, "")) for c in cols))
	if not rows:
		print("  (nothing)")
	print("=" * 72 + "\n")


@frappe.whitelist()
def backfill(dry_run: int = 1, limit: int = 2000, show: int | None = None) -> dict:
	"""Repair reports with a collection date later than their own creation.

	dry_run=1 (default): preview only, writes nothing.
	dry_run=0          : apply, backing up each original value for revert().
	"""
	dry_run = int(dry_run or 0)
	rows = _plan_rows(limit)
	backup = _load_backup()
	plan = []

	for r in rows:
		sample = frappe.db.get_value("Lab Report Sample", {"parent": r.name}, "lab_sample")
		recovered = _collected_time_as_of(sample, r.creation) if sample else None
		source = "version-history"
		new_dt = _to_datetime(recovered)
		creation_dt = _to_datetime(r.creation)
		if new_dt is None:
			new_dt = creation_dt
			source = "report-creation (fallback: no usable history)"
		# Never let the repaired value itself be after the report's creation.
		if new_dt and creation_dt and new_dt > creation_dt:
			new_dt = creation_dt
			source += " +clamped"

		entry = {
			"report": r.name,
			"from": str(r.collection_datetime),
			"to": str(new_dt),
			"source": source,
			"sample": sample,
		}
		plan.append(entry)

		if not dry_run and new_dt is not None:
			# Preserve the ORIGINAL value only once, even across repeated runs.
			if r.name not in backup:
				backup[r.name] = str(r.collection_datetime)
			# Store a real datetime object — never the raw DD-MM-YYYY string,
			# which MySQL rejects.
			frappe.db.set_value("Lab Report", r.name, "collection_datetime", new_dt, update_modified=False)

	if not dry_run and plan:
		_save_backup(backup)
		frappe.db.commit()

	result = {
		"ok": True,
		"dry_run": bool(dry_run),
		"broken_reports": len(plan),
		"backup_file": _backup_path() if not dry_run and plan else None,
		"plan": plan,
	}
	if show is None:
		show = getattr(frappe.local, "request", None) is None
	if int(show or 0):
		_print(f"Collection-date backfill — {'DRY RUN' if dry_run else 'APPLIED'} — {len(plan)} report(s)",
		       plan, ["report", "from", "to", "source"])
		if dry_run and plan:
			print("  Nothing written. Re-run with dry_run=0 to apply.\n")
	return result


@frappe.whitelist()
def revert(dry_run: int = 1, show: int | None = None) -> dict:
	"""Undo backfill() — restore every report's pre-change collection date."""
	dry_run = int(dry_run or 0)
	backup = _load_backup()
	plan = []
	for name, old in backup.items():
		if not frappe.db.exists("Lab Report", name):
			continue
		cur = frappe.db.get_value("Lab Report", name, "collection_datetime")
		plan.append({"report": name, "current": str(cur), "restore_to": str(old)})
		if not dry_run:
			frappe.db.set_value("Lab Report", name, "collection_datetime", old, update_modified=False)
	if not dry_run and plan:
		frappe.db.commit()

	result = {
		"ok": True,
		"dry_run": bool(dry_run),
		"restored": len(plan),
		"backup_file": _backup_path(),
		"plan": plan,
	}
	if show is None:
		show = getattr(frappe.local, "request", None) is None
	if int(show or 0):
		_print(f"Collection-date REVERT — {'DRY RUN' if dry_run else 'APPLIED'} — {len(plan)} report(s)",
		       plan, ["report", "current", "restore_to"])
		if dry_run and plan:
			print("  Nothing written. Re-run with dry_run=0 to undo.\n")
	return result
