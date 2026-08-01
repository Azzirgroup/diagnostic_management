"""Stop "You do not have permission to access field: Diagnostic Report.status".

`Diagnostic Report.status` sits at a restricted permlevel (set by the upstream
Healthcare app). Frappe's query engine refuses to FILTER, COUNT, SORT, or SEARCH
on a field the user can't read at its permlevel — so every workspace count
badge, list filter, global search, and report that touches `status` throws a
403 PermissionError and takes the page down with it:

    frappe.exceptions.PermissionError:
        You do not have permission to access field: Diagnostic Report.status

Blanking individual workspace filters is whack-a-mole; the durable fix is to let
the roles that already use the doctype READ the field at its permlevel. This
grants READ only — write access at that level is left exactly as the Healthcare
app configured it, so any "only pathologists may change status" intent is
preserved.

Self-discovering and idempotent:
  * no-op if the doctype isn't installed, or `status` is already permlevel 0
  * targets only roles that ALREADY hold a permlevel-0 permission on the
    doctype (doesn't invent access for unrelated roles)
  * uses Custom DocPerm via frappe.permissions.add_permission, which overlays
    the upstream app cleanly and survives its updates
"""

import frappe

DOCTYPE = "Diagnostic Report"
FIELD = "status"


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	meta = frappe.get_meta(DOCTYPE)
	df = meta.get_field(FIELD)
	if not df:
		return
	permlevel = int(df.permlevel or 0)
	if permlevel == 0:
		# Field isn't restricted — nothing blocks reading/filtering it.
		return

	from frappe.permissions import add_permission, update_permission_property

	# Roles that already have base (permlevel 0) access to the doctype. Those
	# are the roles whose users open these workspaces / run these searches, so
	# they're exactly who needs read at the restricted level.
	base_roles = {
		p.role for p in meta.permissions
		if int(p.permlevel or 0) == 0 and p.read and p.role
	}
	if not base_roles:
		return

	# Roles that already have a permission row at the restricted level — skip.
	existing = {
		r[0] for r in frappe.get_all(
			"Custom DocPerm",
			filters={"parent": DOCTYPE, "permlevel": permlevel},
			fields=["role"], as_list=True,
		)
	} | {
		int(p.permlevel or 0) == permlevel and p.role or None
		for p in meta.permissions
	}
	existing.discard(None)

	granted = []
	for role in sorted(base_roles):
		if role in existing:
			continue
		try:
			add_permission(DOCTYPE, role, permlevel)
			# Ensure READ is on; leave write/create/delete off at this level.
			update_permission_property(DOCTYPE, role, permlevel, "read", 1, validate=False)
			granted.append(role)
		except Exception:
			frappe.log_error(
				title=f"grant_diagnostic_report_status_read: failed for {role}",
				message=frappe.get_traceback(),
			)

	if granted:
		frappe.clear_cache(doctype=DOCTYPE)
		frappe.db.commit()
		print(f"  [patch] granted permlevel-{permlevel} READ on {DOCTYPE}.{FIELD} to: {', '.join(granted)}")
