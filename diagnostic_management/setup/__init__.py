"""Idempotent setup helpers run from hooks.after_install / after_migrate.

Everything ADMS adds to other apps (Marley, ERPNext) is installed here:
- Custom Fields on Patient, Healthcare Practitioner, Lab Test Template,
  Service Request, Sample Collection, Diagnostic Report, Healthcare Settings.
- Roles introduced by ADMS (Lab Manager, Radiologist, Phlebotomist, etc.).
- Default Code System rows for LOINC / SNOMED / ICD-10 placeholders.

None of these change Marley source files — they are pure additive overlays.
"""

from .custom_fields import install_custom_fields  # noqa: F401
from .print_formats import install_print_formats  # noqa: F401
from .roles import install_roles  # noqa: F401
from .seed_data import install_seed_data  # noqa: F401


def _ensure_desk_icon():
	"""Make sure the Desktop Icon + Workspace Sidebar exist for ADMS.

	Frappe normally creates these on `after_app_install`, but if that hook
	doesn't run (e.g. the app was installed before `add_to_apps_screen` was
	wired up), the tile is missing from /desk. Calling the generator here is
	idempotent — it skips icons that already exist.
	"""
	try:
		from frappe.utils.install import auto_generate_icons_and_sidebar
		auto_generate_icons_and_sidebar()
	except Exception:
		# Don't block install/migrate if the desk icon helper changes shape.
		import frappe
		frappe.log_error(title="ADMS: failed to auto-generate desktop icon")


def _ensure_healthcare_settings():
	"""Turn on the Marley settings the SPA depends on.

	`create_sample_collection_for_lab_test`: when ON, creating a Lab Test
	auto-creates a Sample Collection row — that's what makes the Collection
	worklist populate once orders are placed. Off by default in Marley.
	"""
	import frappe
	try:
		frappe.db.set_single_value(
			"Healthcare Settings",
			"create_sample_collection_for_lab_test",
			1,
		)
	except Exception:
		frappe.log_error(title="ADMS: failed to enable auto sample-collection")


def _ensure_workspace_sidebars_populated():
	"""Re-populate empty Workspace Sidebar shells for our workspaces.

	Frappe's `create_workspace_sidebar_for_workspaces` skips any workspace
	that already has a Workspace Sidebar record — so if a sidebar shell
	exists but its items table is empty (e.g. because the parent Workspace
	was manually deleted and recreated), the user lands on a "No Sidebar
	Items" page. This helper deletes empty shells so the generator will
	rebuild them on the next migrate / direct call.
	"""
	import frappe

	try:
		our_workspaces = frappe.get_all(
			"Workspace",
			filters={"app": "diagnostic_management"},
			pluck="name",
		)
	except Exception:
		our_workspaces = []

	rebuild_needed = False
	for ws in our_workspaces:
		try:
			# A sidebar with zero items is the broken case we need to fix.
			has_items = frappe.db.exists(
				"Workspace Sidebar Item",
				{"parent": ws, "parenttype": "Workspace Sidebar"},
			)
			if frappe.db.exists("Workspace Sidebar", ws) and not has_items:
				frappe.db.delete("Workspace Sidebar", {"name": ws})
				rebuild_needed = True
		except Exception:
			pass

	if rebuild_needed:
		try:
			from frappe.desk.doctype.workspace_sidebar.workspace_sidebar import (
				create_workspace_sidebar_for_workspaces,
			)
			create_workspace_sidebar_for_workspaces()
		except Exception:
			frappe.log_error(title="ADMS: failed to rebuild workspace sidebars")


def _ensure_apps_screen_tiles():
	"""Synchronise the desk Apps-screen tiles with hooks.add_to_apps_screen.

	`add_to_apps_screen` only fires on `after_install` in Frappe, so a tile
	added after the app was installed never appears unless we manually upsert
	the corresponding Desktop Icon row. This helper iterates the hook config
	and reconciles each entry — adds missing tiles, refreshes logo/route on
	existing ones, and unhides any that were hidden by orphan cleanup.
	"""
	import frappe

	try:
		entries = frappe.get_hooks("add_to_apps_screen", app_name="diagnostic_management") or []
	except Exception:
		entries = []

	for raw in entries:
		# Hook values come as dicts wrapped in a list of dicts of lists in Frappe.
		entry = _normalize_hook_entry(raw)
		if not entry or not entry.get("title"):
			continue
		title = entry["title"]
		try:
			existing = frappe.db.get_value("Desktop Icon", {"label": title}, "name")
			if existing:
				doc = frappe.get_doc("Desktop Icon", existing)
			else:
				doc = frappe.new_doc("Desktop Icon")
				doc.label = title
			doc.app = "diagnostic_management"
			doc.link = entry.get("route") or "/diagnostic_management"
			doc.logo_url = entry.get("logo") or doc.logo_url
			# Desktop Icon.icon_type only accepts Link/Folder/App — "Link" is the
			# correct choice for a URL-routed tile.
			doc.icon_type = "Link"
			doc.standard = 1
			doc.hidden = 0
			doc.flags.ignore_permissions = True
			doc.save() if existing else doc.insert(ignore_permissions=True)
		except Exception:
			frappe.log_error(title=f"ADMS: failed to sync apps-screen tile {title}")


def _normalize_hook_entry(raw):
	# frappe.get_hooks returns values flattened; each entry can be a dict or a
	# list-of-dicts depending on how the hook was registered. Coerce both shapes
	# into a single dict so callers don't have to special-case.
	if isinstance(raw, dict):
		# Some hooks come back as { key: [value] } — un-listify the single values.
		out = {}
		for k, v in raw.items():
			out[k] = v[0] if isinstance(v, list) and len(v) == 1 else v
		return out
	return None


def after_install():
	install_roles()
	install_custom_fields()
	install_print_formats()
	install_seed_data()
	_ensure_healthcare_settings()
	_ensure_desk_icon()
	_ensure_apps_screen_tiles()
	_ensure_workspace_sidebars_populated()
	_ensure_shift_role_perms()


def after_migrate():
	# Custom fields & print formats are idempotent — safe to re-run on every
	# migrate, so updates to either land without manual import steps.
	install_custom_fields()
	install_print_formats()
	install_seed_data()
	_ensure_healthcare_settings()
	_ensure_desk_icon()
	_ensure_apps_screen_tiles()
	_ensure_workspace_sidebars_populated()
	_ensure_shift_role_perms()


def _ensure_shift_role_perms():
	"""Grant the shift-using roles (Billing Officer / Receptionist / Lab
	Manager / Diagnostic Director) read+create+write on POS Profile / POS
	Opening Entry / POS Closing Entry. Idempotent: skips rows that exist."""
	import frappe

	plan = {
		"POS Profile": {
			"Billing Officer": {"read": 1},
			"Receptionist": {"read": 1},
			"Lab Manager": {"read": 1, "write": 1, "create": 1},
			"Diagnostic Director": {"read": 1, "write": 1, "create": 1},
		},
		"POS Opening Entry": {
			"Billing Officer": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Receptionist": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Lab Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
			"Diagnostic Director": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
		},
		"POS Closing Entry": {
			"Billing Officer": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Receptionist": {"read": 1, "write": 1, "create": 1, "submit": 1},
			"Lab Manager": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
			"Diagnostic Director": {"read": 1, "write": 1, "create": 1, "submit": 1, "cancel": 1},
		},
	}
	for dt, role_perms in plan.items():
		if not frappe.db.exists("DocType", dt):
			continue
		for role, perms in role_perms.items():
			if not frappe.db.exists("Role", role):
				continue
			existing = frappe.db.exists("Custom DocPerm", {"parent": dt, "role": role})
			if existing:
				continue
			cd = frappe.get_doc({
				"doctype": "Custom DocPerm",
				"parent": dt, "parenttype": "DocType", "parentfield": "permissions",
				"role": role, "permlevel": 0, **perms,
			})
			cd.flags.ignore_permissions = True
			cd.insert()
	frappe.clear_cache()
