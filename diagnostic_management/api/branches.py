"""Branch admin + per-user branch scoping.

Each User can be assigned a `branch` (a Custom Field added to the standard
HRMS Branch doctype). Records that carry a branch tag (Patient today, more
later) are filtered server-side so a user in Branch A only sees Branch A's
data. Administrator / System Manager bypass scoping and see everything.

Hooks involved:
  - doc_events.Patient.validate           → auto_set_branch
  - permission_query_conditions.Patient   → patient_query_conditions
"""
from __future__ import annotations

import frappe
from frappe import _


# Roles that bypass branch scoping and see every record.
_BYPASS_ROLES = {"Administrator", "System Manager"}


def _cache_key(user: str) -> str:
	return f"adms_active_branch:{user}"


def _active_override(user: str) -> str | None:
	"""Return the per-user override branch (set via set_active_branch), or
	None when no override is active. Override has a 12-hour TTL so it
	auto-expires; users explicitly clear by switching to "All Branches"."""
	try:
		v = frappe.cache().get_value(_cache_key(user))
		# frappe.cache may return bytes; normalize
		if isinstance(v, bytes):
			v = v.decode()
		if not v or v == "__ALL__":
			return None
		return v
	except Exception:
		return None


def _shift_branch(user: str) -> str | None:
	"""If the user has an open shift (POS Opening Entry) whose POS Profile
	has a branch set, return that branch. None otherwise.

	Used to temporarily steer a cashier to whichever branch's counter they
	opened today, overriding their persistent tag."""
	try:
		row = frappe.db.sql(
			"""SELECT pp.branch
			FROM `tabPOS Opening Entry` poe
			JOIN `tabPOS Profile` pp ON pp.name = poe.pos_profile
			WHERE poe.user = %s AND poe.status = 'Open' AND poe.docstatus = 1
			  AND pp.branch IS NOT NULL AND pp.branch != ''
			ORDER BY poe.creation DESC LIMIT 1""",
			(user,), as_dict=True,
		)
		return row[0].branch if row else None
	except Exception:
		return None


def _user_branch(user: str | None = None) -> str | None:
	"""Return the branch the user is scoped to, or None for unscoped users.

	Precedence (first non-None wins):
	  1. Per-user override (set via set_active_branch) — admins use this to
	     "act as Branch X" temporarily.
	  2. **Open shift's branch** — if the user currently has an open POS
	     Opening Entry whose POS Profile has a `branch` set, that branch
	     wins. A Main-Branch cashier covering the Westlands counter sees
	     Westlands data until they close that shift.
	  3. Persistent tag on the User record — operator-assigned, authoritative
	     even for admin-roled users.
	  4. None — user sees all branches.
	"""
	user = user or frappe.session.user
	if user == "Guest":
		return None
	ov = _active_override(user)
	if ov:
		return ov
	sb = _shift_branch(user)
	if sb:
		return sb
	tagged = frappe.db.get_value("User", user, "branch") or None
	return tagged or None


@frappe.whitelist()
def set_active_branch(branch: str = "") -> dict:
	"""Switch the calling user's active branch view.

	Only meaningful for users who otherwise see all branches (admins or
	untagged users) — they pick a branch to focus on, or pass empty to
	revert to "All Branches". Users with a persistent branch tag can
	override their own scope only if they also have admin privileges
	(otherwise the tag is the boundary).
	"""
	user = frappe.session.user
	user_roles = set(frappe.get_roles(user))
	tagged = frappe.db.get_value("User", user, "branch") or None
	is_admin = bool(user_roles & _BYPASS_ROLES)
	if tagged and not is_admin:
		frappe.throw(_("Your branch is set by an administrator and can't be changed here."))

	if branch and not frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch {0} not found").format(branch))

	if not branch:
		# Clear override → revert to whatever's on the User record (or all).
		frappe.cache().delete_value(_cache_key(user))
	else:
		# 12-hour TTL so a forgotten override doesn't persist across days.
		frappe.cache().set_value(_cache_key(user), branch, expires_in_sec=12 * 60 * 60)

	return {
		"ok": True,
		"active_branch": branch or None,
		"sees_all_branches": not (branch or tagged),
	}


@frappe.whitelist()
def list_branches() -> list[dict]:
	"""All branches on the site, with their patient counts for the admin view.

	`patient_count` is the number of Patient records whose `branch` matches
	this branch — useful for tracking distribution across locations.
	"""
	rows = frappe.db.get_all(
		"Branch", fields=["name", "branch"], order_by="branch", ignore_permissions=True,
	)
	# Single SQL aggregation so we don't do N+1 counts.
	counts: dict[str, int] = {}
	for r in frappe.db.sql(
		"""SELECT COALESCE(branch, '') AS branch, COUNT(*) AS c
		FROM `tabPatient` GROUP BY branch""", as_dict=True,
	):
		counts[r["branch"]] = int(r["c"])
	# Branchless count exposed under empty-string key for callers that want it.
	for b in rows:
		b["patient_count"] = counts.get(b["name"], 0)
	return rows


@frappe.whitelist()
def patients_per_branch() -> dict:
	"""Patient distribution: {branch_name: count, '': branchless_count}."""
	out: dict[str, int] = {}
	for r in frappe.db.sql(
		"""SELECT COALESCE(branch, '') AS branch, COUNT(*) AS c
		FROM `tabPatient` GROUP BY branch""", as_dict=True,
	):
		out[r["branch"] or "(unassigned)"] = int(r["c"])
	return out


@frappe.whitelist()
def create_branch(branch: str) -> dict:
	"""Create a new Branch record (admin only — guarded by Branch doctype perms)."""
	if not branch:
		frappe.throw(_("Branch name is required"))
	if frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch {0} already exists").format(branch))
	doc = frappe.get_doc({"doctype": "Branch", "branch": branch})
	doc.insert()
	return {"ok": True, "name": doc.name, "branch": doc.branch}


@frappe.whitelist()
def set_user_branch(user: str, branch: str | None = None) -> dict:
	"""Admin endpoint: assign a User to a Branch (or clear)."""
	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} not found").format(user))
	if branch and not frappe.db.exists("Branch", branch):
		frappe.throw(_("Branch {0} not found").format(branch))
	frappe.db.set_value("User", user, "branch", branch or "")
	frappe.clear_cache(user=user)
	return {"ok": True, "user": user, "branch": branch or ""}


@frappe.whitelist()
def get_my_branch() -> dict:
	"""Current user's branch state for the topbar.

	Returns:
	  user
	  branch              — what the system is currently filtering by
	  source              — where `branch` came from: 'override' | 'shift'
	                        | 'tag' | None
	  tagged_branch       — the branch on the User record (None if untagged)
	  active_override     — set by set_active_branch
	  shift_branch        — branch of the user's open shift's POS Profile
	  is_admin            — has Administrator/System Manager role
	  can_switch_branch   — True → topbar should show the branch dropdown
	  sees_all_branches   — True when nothing is restricting the user
	"""
	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_admin = bool(roles & _BYPASS_ROLES)
	tagged = frappe.db.get_value("User", user, "branch") or None
	override = _active_override(user)
	shift = _shift_branch(user)
	# Match _user_branch precedence: override > shift > tag.
	if override:
		current, source = override, "override"
	elif shift:
		current, source = shift, "shift"
	elif tagged:
		current, source = tagged, "tag"
	else:
		current, source = None, None
	can_switch = is_admin or not tagged
	return {
		"user": user,
		"branch": current,
		"source": source,
		"tagged_branch": tagged,
		"active_override": override,
		"shift_branch": shift,
		"is_admin": is_admin,
		"can_switch_branch": can_switch,
		"sees_all_branches": not current,
	}


@frappe.whitelist()
def backfill_patient_branches(default_branch: str) -> dict:
	"""Admin tool: every Patient that currently has no `branch` gets tagged
	with `default_branch`. Useful after rolling branches out across an
	existing site — without this, branch-scoped users can't see any legacy
	patients (because the filter is strict)."""
	if not frappe.db.exists("Branch", default_branch):
		frappe.throw(_("Branch {0} not found").format(default_branch))
	rows = frappe.db.sql(
		"UPDATE `tabPatient` SET branch=%s WHERE branch IS NULL OR branch=''",
		(default_branch,),
	)
	frappe.db.commit()
	count = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabPatient` WHERE branch=%s",
		(default_branch,),
	)[0][0]
	return {"ok": True, "default_branch": default_branch, "now_in_branch": count}


@frappe.whitelist()
def list_users_with_branch() -> list[dict]:
	"""Admin: list system users + their assigned branch (for the Branches admin page)."""
	rows = frappe.db.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		fields=["name", "full_name", "branch"],
		order_by="full_name",
		ignore_permissions=True,
	)
	return rows


# ─────────────────────────────────────────────────────────────────────────
# Doc events
# ─────────────────────────────────────────────────────────────────────────

def patient_branch_filter(field_name: str = "patient") -> dict:
	"""Reusable filter for any doctype whose rows link to a Patient.

	Returns a Frappe filters dict that restricts the result set to rows
	whose `<field_name>` (default 'patient') is one of the Patients in the
	calling user's branch. Empty dict for admins / unscoped users
	(see everything).

	When the user IS branch-scoped but has zero patients in their branch,
	we return a filter that matches nothing — so the screen shows empty
	instead of falling through and returning every row.
	"""
	b = _user_branch()
	if not b:
		return {}
	names = frappe.db.get_all(
		"Patient", filters={"branch": b}, pluck="name", ignore_permissions=True,
	)
	if not names:
		# Match nothing — branch has no patients yet.
		return {field_name: ["in", ["__NO_PATIENTS_IN_BRANCH__"]]}
	return {field_name: ["in", names]}


def stamp_sample_collection_si(doc, method=None) -> None:
	"""Doc event (Lab Test on insert) — if the Lab Test carries a
	custom_sales_invoice and the linked Sample Collection has none yet,
	stamp it. Makes Sample Collection.custom_sales_invoice authoritative for
	"which invoice owns this sample" without walking through Lab Tests."""
	si = doc.get("custom_sales_invoice")
	sc_name = doc.get("sample")
	if not (si and sc_name and frappe.db.exists("Sample Collection", sc_name)):
		return
	existing = frappe.db.get_value("Sample Collection", sc_name, "custom_sales_invoice") or None
	if not existing:
		frappe.db.set_value("Sample Collection", sc_name, "custom_sales_invoice", si)


def auto_set_patient_branch(doc, method=None) -> None:
	"""On Patient validate, default `branch` to the creating user's branch
	when it's not already set. Admins create patients without a branch (so
	they can later assign or leave global)."""
	if doc.get("branch"):
		return
	b = _user_branch(frappe.session.user)
	if b:
		doc.branch = b


# ─────────────────────────────────────────────────────────────────────────
# Permission query conditions — hooked from hooks.py.
# Frappe calls these as `fn(user)` and expects a SQL WHERE-clause fragment
# (e.g. "`tabPatient`.branch = 'Main'") or None to mean "no extra filter".
# ─────────────────────────────────────────────────────────────────────────

def patient_query_conditions(user: str | None = None) -> str | None:
	"""STRICT branch filter — Patient.branch must match the user's branch.
	Branchless patients are hidden from branch-scoped users. Admins and
	unscoped users get no filter (see everything)."""
	user = user or frappe.session.user
	b = _user_branch(user)
	if not b:
		return None
	b_safe = frappe.db.escape(b)
	return f"`tabPatient`.branch = {b_safe}"


def patient_has_permission(doc, user=None, permission_type=None) -> bool:
	"""Per-doc gate: a non-admin can only touch patients in their branch
	(or branchless ones). Mirrors the query filter for list/load access."""
	user = user or frappe.session.user
	b = _user_branch(user)
	if not b:
		return True  # admin / unscoped
	doc_branch = getattr(doc, "branch", None)
	return (not doc_branch) or (doc_branch == b)
