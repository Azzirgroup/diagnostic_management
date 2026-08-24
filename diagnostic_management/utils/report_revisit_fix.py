"""One-time repair: give each PAST VISIT its own Lab Report.

A reused Sample Collection was shared across every visit, so a returning
patient's visits collapsed onto ONE Lab Report (one LRPT number, stale tests).
The per-visit fix (results._existing_report_for) handles NEW visits; this script
repairs the ones already created.

For every sample that belongs to more than one workflow session, it (re)builds a
Lab Report per session — scoped to that session's tests — so each visit ends up
with its own report and number.

SAFE BY DESIGN:
  * dry_run=1 by default — shows the plan, writes nothing
  * only touches REUSED samples (in >1 session); single-visit samples untouched
  * SKIPS submitted/signed reports (docstatus=1) — released reports are never
    altered
  * records every report it creates + every session it stamps, so revert()
    can undo the whole run
  * idempotent — a visit that already has its own report is left alone

Run (browser or bench):
  /api/method/diagnostic_management.utils.report_revisit_fix.run                (preview)
  /api/method/diagnostic_management.utils.report_revisit_fix.run?dry_run=0      (apply)
  /api/method/diagnostic_management.utils.report_revisit_fix.revert?dry_run=0   (undo)
"""

import json
import os

import frappe

_BACKUP = "report_revisit_backup.json"


def _backup_path():
	return frappe.get_site_path("private", "files", _BACKUP)


def _load_backup():
	p = _backup_path()
	if os.path.exists(p):
		try:
			with open(p) as f:
				return json.load(f)
		except Exception:
			return {"created": [], "stamped": []}
	return {"created": [], "stamped": []}


def _save_backup(data):
	with open(_backup_path(), "w") as f:
		json.dump(data, f, indent=2, default=str)


def _reused_samples(limit):
	"""Samples that appear in MORE THAN ONE workflow session."""
	rows = frappe.get_all(
		"Lab Workflow Session Sample", fields=["sample", "parent"], limit_page_length=0
	)
	by_sample = {}
	for r in rows:
		if not r.get("sample"):
			continue
		by_sample.setdefault(r["sample"], set()).add(r["parent"])
	reused = [(s, sorted(sessions)) for s, sessions in by_sample.items() if len(sessions) > 1]
	reused.sort()
	return reused[: int(limit)]


def _sample_reports(sample):
	"""Existing Lab Reports on a sample: name -> (docstatus, session)."""
	fields = ["docstatus"]
	if frappe.db.has_column("Lab Report", "custom_workflow_session"):
		fields.append("custom_workflow_session")
	out = {}
	for parent in frappe.get_all("Lab Report Sample", filters={"lab_sample": sample}, pluck="parent"):
		info = frappe.db.get_value("Lab Report", parent, fields, as_dict=True)
		if info:
			out[parent] = info
	return out


@frappe.whitelist()
def run(dry_run: int = 1, limit: int = 200, show: int | None = None) -> dict:
	"""Rebuild a per-visit Lab Report for each session of every reused sample."""
	from diagnostic_management.api.results import _build_lab_report

	# The per-visit fix needs the custom_workflow_session field. If a migrate
	# hasn't created it yet, running would silently give wrong results — refuse
	# clearly instead. Create it with report_diagnostics.install_report_fields.
	if not frappe.db.has_column("Lab Report", "custom_workflow_session"):
		return {
			"ok": False,
			"error": "custom_workflow_session field is not installed yet.",
			"fix": "Run report_diagnostics.install_report_fields (or migrate) first, then re-run.",
		}

	dry_run = int(dry_run or 0)
	backup = _load_backup()
	plan = []
	created = 0

	for sample, sessions in _reused_samples(limit):
		before = _sample_reports(sample)
		# Safety: never split a sample that has a SIGNED (submitted) report — we
		# can't know which visit owns it, and touching released records is unsafe.
		# Flag the whole sample for manual review instead.
		if any(int(i.get("docstatus") or 0) == 1 for i in before.values()):
			plan.append({"sample": sample, "sessions": sessions, "action": "skip-sample",
			             "reason": "has a signed/submitted report — manual review needed"})
			continue
		# Track which existing report each session has claimed — so the DRY-RUN
		# reflects reality: only the FIRST visit adopts the shared report, the
		# rest create their own (exactly what apply mode does as it stamps).
		claimed = {r: info.get("custom_workflow_session") for r, info in before.items()
		           if info.get("custom_workflow_session")}
		for session in sessions:
			# 1) a report already stamped with THIS session?
			target = next((r for r, s in claimed.items() if s == session), None)
			already = target is not None
			# 2) else adopt an unclaimed, non-submitted report on this sample
			if not target:
				for r, info in before.items():
					if r in claimed:
						continue
					if int(info.get("docstatus") or 0) == 1:
						continue  # never touch a signed report
					target = r
					claimed[r] = session
					break
			target_info = before.get(target) if target else None
			# A submitted/signed report must never be rebuilt.
			if target_info and int(target_info.get("docstatus") or 0) == 1:
				plan.append({"sample": sample, "session": session, "action": "skip",
				             "reason": "target report is submitted/signed", "report": target})
				continue
			action = "reuse (already this visit)" if already else (
				"rebuild+stamp existing" if target else "CREATE new report")
			entry = {"sample": sample, "session": session, "action": action, "report_before": target}
			if not dry_run:
				try:
					# Migration keeps adopting an old un-stamped report so it retains
					# its number; normal report-building never adopts (a returning
					# patient must get a fresh report, not inherit an older visit's).
					new_name = _build_lab_report(sample, {"status": "Approved"}, session=session,
					                             adopt_unsessioned=True)
					entry["report_after"] = new_name
					if new_name and new_name not in before:
						backup["created"].append(new_name)
						created += 1
					elif target and not already:
						backup["stamped"].append({"report": target, "session": session})
				except Exception as e:
					entry["action"] = "error"; entry["error"] = str(e)
					frappe.log_error(title=f"report_revisit_fix: {sample}/{session} failed")
			plan.append(entry)

	if not dry_run:
		_save_backup(backup)
		frappe.db.commit()

	result = {
		"ok": True,
		"dry_run": bool(dry_run),
		"reused_samples": len({p["sample"] for p in plan}),
		"visits_planned": len(plan),
		"reports_created": created,
		"backup_file": _backup_path() if not dry_run else None,
		"plan": plan[:300],
	}
	if show is None:
		show = getattr(frappe.local, "request", None) is None
	if int(show or 0):
		print(json.dumps(result, indent=2, default=str))
	return result


@frappe.whitelist()
def revert(dry_run: int = 1) -> dict:
	"""Undo run(): delete the Lab Reports it created and clear the session stamps
	it added. Signed reports were never touched, so nothing there to undo."""
	dry_run = int(dry_run or 0)
	backup = _load_backup()
	deleted, unstamped = [], []

	for name in backup.get("created", []):
		if frappe.db.exists("Lab Report", name):
			if not dry_run:
				# Only delete if still a draft — never a report someone has since signed.
				if int(frappe.db.get_value("Lab Report", name, "docstatus") or 0) == 0:
					frappe.delete_doc("Lab Report", name, force=1, ignore_permissions=True)
			deleted.append(name)
	has_field = frappe.db.has_column("Lab Report", "custom_workflow_session")
	for row in backup.get("stamped", []):
		if frappe.db.exists("Lab Report", row["report"]):
			if not dry_run and has_field:
				frappe.db.set_value("Lab Report", row["report"], "custom_workflow_session", None,
				                    update_modified=False)
			unstamped.append(row["report"])

	if not dry_run:
		# Clear the backup so a second revert is a no-op.
		_save_backup({"created": [], "stamped": []})
		frappe.db.commit()

	return {
		"ok": True,
		"dry_run": bool(dry_run),
		"reports_deleted": deleted,
		"stamps_cleared": unstamped,
	}
