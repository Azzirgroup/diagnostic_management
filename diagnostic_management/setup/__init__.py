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


def after_install():
	install_roles()
	install_custom_fields()
	_ensure_desk_icon()


def after_migrate():
	# Custom fields are idempotent — safe to re-run on every migrate.
	install_custom_fields()
	_ensure_desk_icon()
