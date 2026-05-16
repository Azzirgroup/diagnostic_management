"""Idempotent setup helpers run from hooks.after_install / after_migrate.

Everything ADMS adds to other apps (Marley, ERPNext) is installed here:
- Custom Fields on Patient, Healthcare Practitioner, Lab Test Template,
  Service Request, Sample Collection, Diagnostic Report, Healthcare Settings.
- Roles introduced by ADMS (Lab Manager, Radiologist, Phlebotomist, etc.).
- Default Code System rows for LOINC / SNOMED / ICD-10 placeholders.

None of these change Marley source files — they are pure additive overlays.
"""

from .custom_fields import install_custom_fields  # noqa: F401
from .roles import install_roles  # noqa: F401


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
	_ensure_desk_icon()
	_ensure_apps_screen_tiles()
	_ensure_workspace_sidebars_populated()


def after_migrate():
	# Custom fields are idempotent — safe to re-run on every migrate.
	install_custom_fields()
	_ensure_desk_icon()
	_ensure_apps_screen_tiles()
	_ensure_workspace_sidebars_populated()
