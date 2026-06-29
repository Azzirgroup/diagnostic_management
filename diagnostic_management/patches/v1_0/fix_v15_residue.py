"""Clean up v15 → v16 residue that blocks Sales Invoice creation on sites
restored from the old genetest backup.

Runs once on `bench migrate` and is idempotent (safe to re-run).

Three categories of cleanup, each independently guarded:

1.  Property Setters pinning `Sales Invoice.pos_profile.default` (or any
    other field's default) to a value that no longer resolves to a real
    record. The genetest backup set `pos_profile default = "POS Genetest"`,
    a profile that doesn't exist on either local or production after the
    migration. The bad default fires on every Sales Invoice insert and
    throws `LinkValidationError: Could not find POS Profile: POS Genetest`
    AFTER the Sample Collection is already created — leaving the workflow
    half-completed.

2.  User-level `is_pos=1` defaults in `tabDefaultValue`. These force POS
    mode on every new Sales Invoice the user creates, which makes
    `pos_profile` mandatory. Combined with #1 it's a guaranteed failure;
    alone it's a UX nuisance because the workflow never asks for a POS
    profile. ADMS doesn't use the sticky-default flow — POS mode is opened
    via POS Opening Entry per shift, so these stale defaults serve no
    purpose.

3.  Missing Healthcare Custom Fields on `Sales Invoice Item`. Healthcare's
    `setup_healthcare()` installs nine insurance-related fields
    (`insurance_coverage_amount` et al.) but early-returns if a
    "Cardiology" Medical Department already exists. On restored sites
    that condition is already true, so the fields never get added — and
    Healthcare's own validation code then throws AttributeError mid-save.

Also blanks `Website Settings.home_page` if it points to a non-existent
Web Page, so `/` doesn't 404 (a tertiary symptom of the restore).
"""

from __future__ import annotations

import frappe


def execute():
	_clean_stale_property_setters()
	_clean_stale_is_pos_defaults()
	_install_missing_healthcare_custom_fields()
	_fix_broken_homepage()
	frappe.db.commit()
	frappe.clear_cache()


# ---------------------------------------------------------------------------
# 1. Property Setters
# ---------------------------------------------------------------------------

def _clean_stale_property_setters() -> None:
	"""Delete Property Setter rows whose `property='default'` value names a
	record that doesn't exist for the field's Link target.

	Scope kept narrow: only `default` property setters on Link fields whose
	value can be resolved to a (doctype, name) check. We don't touch other
	property types (read_only, hidden, etc.) — those are usually intentional
	customisations.
	"""
	rows = frappe.db.sql(
		"""SELECT name, doc_type, field_name, value
		   FROM `tabProperty Setter`
		   WHERE property = 'default' AND value IS NOT NULL AND value != ''""",
		as_dict=True,
	)
	for row in rows:
		try:
			meta = frappe.get_meta(row["doc_type"])
		except Exception:
			continue
		field = meta.get_field(row["field_name"])
		if not field or field.fieldtype != "Link" or not field.options:
			continue
		# Link target must exist; otherwise the default is poison.
		if not frappe.db.exists(field.options, row["value"]):
			frappe.delete_doc("Property Setter", row["name"], force=1, ignore_permissions=True)
			print(
				f"  [v15-residue] deleted Property Setter "
				f"{row['doc_type']}.{row['field_name']} default={row['value']!r} "
				f"(no such {field.options})"
			)


# ---------------------------------------------------------------------------
# 2. is_pos user defaults
# ---------------------------------------------------------------------------

def _clean_stale_is_pos_defaults() -> None:
	"""Drop `is_pos=1` from tabDefaultValue. ADMS doesn't use the sticky POS
	default — opening a shift via POS Opening Entry sets POS mode for the
	session. Leaving `is_pos=1` on a user makes every new Sales Invoice
	mandate a `pos_profile`, which the ADMS billing flow doesn't supply.
	"""
	n = frappe.db.sql(
		"SELECT COUNT(*) FROM `tabDefaultValue` WHERE defkey = 'is_pos'",
	)[0][0]
	if not n:
		return
	frappe.db.sql("DELETE FROM `tabDefaultValue` WHERE defkey = 'is_pos'")
	print(f"  [v15-residue] cleared {n} stale `is_pos=1` user default(s)")


# ---------------------------------------------------------------------------
# 3. Healthcare Custom Fields
# ---------------------------------------------------------------------------

def _install_missing_healthcare_custom_fields() -> None:
	"""Re-run Healthcare's create_custom_fields, bypassing setup_healthcare's
	early-return guard. Idempotent — `create_custom_fields(..., update=True)`
	won't duplicate; missing fields get created, present ones get refreshed.
	"""
	try:
		from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
		from healthcare.setup import data as healthcare_data
	except ImportError:
		# Healthcare not installed on this site — nothing to do.
		return

	cf = healthcare_data.get("custom_fields") if isinstance(healthcare_data, dict) else None
	if not cf:
		return

	# Spot-check: if the canonical insurance_coverage_amount field is missing
	# on Sales Invoice Item, we KNOW Healthcare's setup never ran on this
	# site — install the whole batch.
	missing = not frappe.db.exists(
		"Custom Field",
		{"dt": "Sales Invoice Item", "fieldname": "insurance_coverage_amount"},
	)
	if not missing:
		# Nothing to do; common case on a healthy site.
		return

	create_custom_fields(cf, ignore_validate=True, update=True)
	print("  [v15-residue] installed missing Healthcare custom fields (Sales Invoice Item et al.)")


# ---------------------------------------------------------------------------
# 4. Broken homepage
# ---------------------------------------------------------------------------

def _fix_broken_homepage() -> None:
	"""If Website Settings.home_page points at a Web Page that doesn't exist,
	reset it to 'login' so `/` redirects sanely instead of 404'ing."""
	ws = frappe.db.get_value(
		"Website Settings", "Website Settings", "home_page",
	)
	if not ws or ws == "login":
		return
	exists = (
		frappe.db.exists("Web Page", {"route": ws})
		or frappe.db.exists("Web Page", ws)
	)
	if exists:
		return
	frappe.db.set_value("Website Settings", "Website Settings", "home_page", "login")
	print(f"  [v15-residue] reset Website Settings.home_page from {ws!r} → 'login' (Web Page missing)")
