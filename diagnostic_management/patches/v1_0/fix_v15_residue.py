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
	_resync_naming_series_counters()
	_remove_dead_genetest_client_scripts()
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


# ---------------------------------------------------------------------------
# 5. Naming series counter resync
# ---------------------------------------------------------------------------

def _resync_naming_series_counters() -> None:
	"""Bump every `tabSeries` counter past the highest existing name on the
	corresponding doctype. Restored sites carry the data but not the counters,
	so the next autoname tries a number that's already taken and the insert
	409s with DuplicateEntryError.

	Two flavours of autoname need different handling:

	a) `format:LW-{YYYY}-{#####}` style — Frappe parses each `{...}` token
	   independently, so when it hits `{#####}` the series key passed to
	   `getseries()` is the **empty string** (no prefix accumulator). ALL
	   format-string autonames with `{#####}` share the single empty-string
	   row in tabSeries. Bumping just that one row covers Lab Workflow
	   Session, Diagnostic Report, and any other format-style doctype.

	b) `naming_series:` style (the field-driven kind) — the key in tabSeries
	   IS the concrete prefix (e.g. `ACC-SINV-2026-`). For each distinct
	   prefix actually used, bump if its counter is behind.
	"""
	import re
	from collections import defaultdict

	# (a) Bump the empty-string global counter past the highest tail-number
	# on any doctype that uses a `format:...{#####}` autoname.
	max_global_tail = 0
	for dt_row in frappe.db.sql(
		"""SELECT name, autoname FROM `tabDocType`
		   WHERE autoname LIKE 'format:%' AND ifnull(istable,0)=0""",
		as_dict=True,
	):
		try:
			rows = frappe.db.sql(
				f"""SELECT name FROM `tab{dt_row['name']}`
				   WHERE name REGEXP %s""",
				r'-[0-9]+$',
			)
			for (n,) in rows:
				m = re.search(r"(\d+)$", n)
				if m:
					max_global_tail = max(max_global_tail, int(m.group(1)))
		except Exception:
			continue
	if max_global_tail:
		# Pad by 1 so the next autoname is max+1, not equal.
		target = max_global_tail
		row = frappe.db.sql("SELECT current FROM `tabSeries` WHERE name=%s", ("",))
		cur = row[0][0] if row else 0
		if cur < target:
			if row:
				frappe.db.sql("UPDATE `tabSeries` SET current=%s WHERE name=%s", (target, ""))
			else:
				frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", ("", target))
			print(f"  [v15-residue] bumped format-string series counter {cur} → {target}")

	# (b) `naming_series:` style — bump each concrete prefix past its max.
	for dt_row in frappe.db.sql(
		"""SELECT name FROM `tabDocType`
		   WHERE autoname = 'naming_series:' AND ifnull(istable,0)=0""",
		as_dict=True,
	):
		dt = dt_row["name"]
		try:
			rows = frappe.db.sql(
				f"""SELECT DISTINCT naming_series FROM `tab{dt}`
				   WHERE naming_series IS NOT NULL AND naming_series != ''""",
			)
		except Exception:
			continue
		for (prefix_template,) in rows:
			head = (prefix_template or "").split("#")[0].rstrip(".")
			rx = re.escape(head).replace(r"\.YYYY\.", r"\d{4}") \
				.replace(r"\.MM\.", r"\d{2}").replace(r"\.DD\.", r"\d{2}") \
				.replace(r"\.YY\.", r"\d{2}")
			try:
				rows2 = frappe.db.sql(
					f"""SELECT name FROM `tab{dt}` WHERE name REGEXP %s""",
					"^" + rx + r"-?\d+$",
				)
			except Exception:
				continue
			by_prefix: dict[str, list[int]] = defaultdict(list)
			for (n,) in rows2:
				m = re.match(r"^(.+?)-?(\d+)$", n)
				if m:
					by_prefix[m.group(1)].append(int(m.group(2)))
			for cp, nums in by_prefix.items():
				mx = max(nums)
				row = frappe.db.sql("SELECT current FROM `tabSeries` WHERE name=%s", (cp,))
				cur = row[0][0] if row else 0
				if cur < mx:
					if row:
						frappe.db.sql("UPDATE `tabSeries` SET current=%s WHERE name=%s", (mx, cp))
					else:
						frappe.db.sql("INSERT INTO `tabSeries` (name, current) VALUES (%s, %s)", (cp, mx))
					print(f"  [v15-residue] bumped {cp} counter {cur} → {mx}")


# ---------------------------------------------------------------------------
# 6. Dead Client Scripts that reference the removed `genetest` app
# ---------------------------------------------------------------------------

def _remove_dead_genetest_client_scripts() -> None:
	"""Delete Client Scripts whose JS calls into `genetest.api.*` Python
	methods. The genetest app was uninstalled (ADMS replaces it), so those
	calls now 500 the moment a user opens the corresponding form. Reads
	`tabClient Script.script` directly so we only target rows that actually
	depend on the dead app, not anything that just mentions the name.
	"""
	rows = frappe.db.sql(
		"""SELECT name FROM `tabClient Script` WHERE script LIKE '%genetest.api%'""",
		as_dict=True,
	)
	for r in rows:
		frappe.delete_doc("Client Script", r["name"], force=1, ignore_permissions=True)
		print(f"  [v15-residue] deleted dead Client Script {r['name']!r} (called removed genetest.api.*)")
