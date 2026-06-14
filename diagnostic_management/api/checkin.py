"""Check-In/Out backend — thin wrappers over HRMS Employee Checkin so the
ADMS SPA can clock the current user in/out and show their own history.

Every endpoint is scoped to `frappe.session.user`:
  - Resolves the Employee record from the user (Employee.user_id)
  - All Employee Checkin rows are filtered to that employee
  - ignore_permissions=True for queries that need to see their own data even
    when the role doesn't have global Employee Checkin read perm
"""
from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import now_datetime


def _resolve_employee(user: str | None = None) -> dict:
	"""Return {name, employee_name} for the current user, throws if not linked."""
	user = user or frappe.session.user
	emp = frappe.db.get_value(
		"Employee", {"user_id": user},
		["name", "employee_name", "company"], as_dict=True,
	)
	if not emp:
		frappe.throw(
			_("Your user account ({0}) isn't linked to an Employee record. "
			  "An HR admin needs to create an Employee with User ID = {0}.").format(user),
			title=_("Not an Employee"),
		)
	return emp


@frappe.whitelist()
def get_status() -> dict:
	"""Current check-in state for the calling user.

	Returns:
	  {
	    employee: {name, employee_name},
	    last_log: { name, time, log_type } | None,
	    is_in: bool — True if last log is IN, False if OUT or none today
	  }
	"""
	emp = _resolve_employee()
	rows = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": emp["name"]},
		fields=["name", "time", "log_type", "device_id"],
		order_by="time desc", limit=1, ignore_permissions=True,
	)
	last = rows[0] if rows else None
	if last:
		last["time"] = str(last["time"])
	is_in = bool(last and (last.get("log_type") == "IN"))
	return {"employee": emp, "last_log": last, "is_in": is_in}


@frappe.whitelist()
def clock(log_type: str = "IN", device_id: str | None = None) -> dict:
	"""Record an Employee Checkin row of the given log_type ('IN' | 'OUT').

	Defaults to IN. Skips auto-attendance (we just want the raw clock log,
	not the daily Attendance roll-up which is HRMS's nightly job)."""
	if log_type not in ("IN", "OUT"):
		frappe.throw(_("log_type must be 'IN' or 'OUT'"))
	emp = _resolve_employee()
	doc = frappe.get_doc({
		"doctype": "Employee Checkin",
		"employee": emp["name"],
		"employee_name": emp.get("employee_name"),
		"time": now_datetime(),
		"log_type": log_type,
		"device_id": device_id or "ADMS Frontend",
		"skip_auto_attendance": 1,
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	return {
		"ok": True,
		"name": doc.name,
		"time": str(doc.time),
		"log_type": doc.log_type,
		"employee": emp["name"],
	}


@frappe.whitelist()
def clock_in(device_id: str | None = None) -> dict:
	"""Convenience wrapper for log_type='IN'."""
	return clock(log_type="IN", device_id=device_id)


@frappe.whitelist()
def clock_out(device_id: str | None = None) -> dict:
	"""Convenience wrapper for log_type='OUT'."""
	return clock(log_type="OUT", device_id=device_id)


@frappe.whitelist()
def my_history(limit: int = 30) -> list[dict]:
	"""Recent Employee Checkin rows for the current user (newest first)."""
	emp = _resolve_employee()
	rows = frappe.db.get_all(
		"Employee Checkin",
		filters={"employee": emp["name"]},
		fields=["name", "time", "log_type", "device_id", "shift", "creation"],
		order_by="time desc", limit=int(limit or 30), ignore_permissions=True,
	)
	for r in rows:
		r["time"] = str(r.get("time") or "")
		r["creation"] = str(r.get("creation") or "")
	return rows


@frappe.whitelist()
def my_today() -> dict:
	"""Today's check-ins for the current user + duration if a matched OUT exists."""
	emp = _resolve_employee()
	rows = frappe.db.sql(
		"""SELECT name, time, log_type FROM `tabEmployee Checkin`
		WHERE employee = %s AND DATE(time) = CURDATE()
		ORDER BY time ASC""",
		(emp["name"],), as_dict=True,
	)
	# Pair INs with the next OUT for elapsed-time display.
	sessions: list[dict] = []
	open_in = None
	for r in rows:
		if r["log_type"] == "IN":
			open_in = {"in_time": str(r["time"]), "in_name": r["name"], "out_time": None, "duration_minutes": None}
			sessions.append(open_in)
		elif r["log_type"] == "OUT" and open_in:
			open_in["out_time"] = str(r["time"])
			# duration in minutes
			from datetime import datetime
			t_in = datetime.fromisoformat(open_in["in_time"])
			t_out = datetime.fromisoformat(open_in["out_time"])
			open_in["duration_minutes"] = round((t_out - t_in).total_seconds() / 60.0, 1)
			open_in = None
	total_minutes = sum((s.get("duration_minutes") or 0) for s in sessions if s.get("duration_minutes"))
	return {
		"employee": emp,
		"sessions": sessions,
		"total_minutes": total_minutes,
		"raw_logs": [{"name": r["name"], "time": str(r["time"]), "log_type": r["log_type"]} for r in rows],
	}
