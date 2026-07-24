"""Recursive expansion for Grouped-inside-Grouped Lab Test Templates.

Marley's `load_result_format()` expands a `Grouped` template by walking
`lab_test_groups` and branching on each child's `lab_test_template_type`:

    Single      -> create_normals()
    Compound    -> create_compounds()
    Descriptive -> create_descriptives()

There is **no branch for `Grouped`**. So when a package contains another
package — e.g. "Afya Bora Comprehensive Male Package" contains "Thyroid
Function Test (TFT)", "Electrolytes", "Lipid Profile (Grouped)" and
"Liver Function Test,Male", all of which are themselves `Grouped` — the loop
matches nothing, appends nothing, and raises nothing. The analytes silently
vanish from `normal_test_items`, and every downstream consumer (result entry,
Lab Report `grouped_results`, print) is therefore missing them too.

This module runs as a `Lab Test.after_insert` doc_event, i.e. AFTER Marley has
already expanded what it can. It finds the nested `Grouped` members that
produced no rows and expands them recursively, reusing Marley's own
`create_normals` / `create_compounds` / `create_descriptives` so the field
mapping stays identical to a first-class expansion (and keeps tracking any
changes they make upstream).

It is idempotent: a member whose analytes are already on the doc is skipped.
If Marley ever adds the missing branch, this becomes a no-op rather than
double-expanding.
"""

import frappe


# A nested package renders as a section header row followed by its analytes —
# the same shape Marley already produces for a Compound sitting in a group
# (header row: no `lab_test_event`, allow_blank=1, require_result_value=0).
# Set False to expand nested packages flat, with no header row.
ADD_NESTED_GROUP_HEADER = True

# Guard against a package that (directly or transitively) contains itself.
MAX_GROUP_DEPTH = 5


def _marley_builders():
	"""Marley's row builders. Imported lazily so this module stays importable
	on a bench without the healthcare app installed."""
	from healthcare.healthcare.doctype.lab_test.lab_test import (
		create_compounds,
		create_descriptives,
		create_normals,
	)

	return create_normals, create_compounds, create_descriptives


def _group_rows(template_doc):
	"""`lab_test_groups` rows of a Grouped template, in idx order."""
	return sorted(template_doc.get("lab_test_groups") or [], key=lambda r: r.idx or 0)


def _new_line_label(row):
	"""Label for a `template_or_new_line == "Add new line"` group row.

	Marley has renamed this field across versions, so probe the candidates
	rather than hard-coding one.
	"""
	for fieldname in ("group_event", "group_event_name", "lab_test_event", "lab_test_name"):
		val = row.get(fieldname)
		if val:
			return val
	return None


def _collect_leaves(template_name, visited=None, depth=0):
	"""Flatten a template into the leaf units that actually produce rows.

	Returns an ordered list of tuples:
	    ("template", <Lab Test Template doc>)   -> Single / Compound / Descriptive
	    ("header",   <Lab Test Template doc>)   -> a nested Grouped's section header
	    ("newline",  <label:str>, <owner:str>)  -> an "Add new line" group row

	Recurses through nested `Grouped` members. `visited` breaks cycles.
	"""
	visited = visited if visited is not None else set()
	if depth > MAX_GROUP_DEPTH or template_name in visited:
		return []
	visited.add(template_name)

	try:
		tmpl = frappe.get_doc("Lab Test Template", template_name)
	except frappe.DoesNotExistError:
		return []

	ttype = tmpl.get("lab_test_template_type") or "Single"
	if ttype != "Grouped":
		return [("template", tmpl)]

	leaves = []
	if ADD_NESTED_GROUP_HEADER:
		# Every Grouped template that reaches here is a *member* of a package —
		# callers only enter with a nested member, never with the Lab Test's own
		# template (Marley already stamps that onto the Lab Test itself). So each
		# one earns a header row, at whatever depth it sits.
		leaves.append(("header", tmpl))

	for row in _group_rows(tmpl):
		child = row.get("lab_test_template")
		if child:
			leaves.extend(_collect_leaves(child, visited, depth + 1))
		else:
			label = _new_line_label(row)
			if label:
				leaves.append(("newline", label, tmpl.name, row))
	return leaves


def _append_header(lab_test, tmpl):
	"""Section-header row for a nested package — mirrors the header Marley
	writes for a Compound inside a group."""
	lab_test.normal_toggle = 1
	row = lab_test.append("normal_test_items")
	row.lab_test_name = tmpl.lab_test_name or tmpl.name
	row.template = tmpl.name
	row.require_result_value = 0
	row.allow_blank = 1
	return row


def _append_new_line(lab_test, label, owner_template, src_row):
	"""Mirror of Marley's `else` branch for "Add new line" group rows."""
	lab_test.normal_toggle = 1
	row = lab_test.append("normal_test_items")
	row.lab_test_name = label
	row.template = owner_template
	row.require_result_value = 1
	row.allow_blank = src_row.get("allow_blank") or 0
	return row


def _build_leaf(lab_test, leaf):
	"""Append the rows for one leaf via Marley's own builders."""
	create_normals, create_compounds, create_descriptives = _marley_builders()

	kind = leaf[0]
	if kind == "header":
		_append_header(lab_test, leaf[1])
		return
	if kind == "newline":
		_append_new_line(lab_test, leaf[1], leaf[2], leaf[3])
		return

	tmpl = leaf[1]
	ttype = tmpl.get("lab_test_template_type") or "Single"
	if ttype == "Single":
		create_normals(tmpl, lab_test)
	elif ttype == "Compound":
		# is_group=True -> Marley writes the compound's own header row first,
		# which is what it does for a Compound sitting directly in a package.
		create_compounds(tmpl, lab_test, True)
	elif ttype == "Descriptive":
		create_descriptives(tmpl, lab_test)


def _present_templates(lab_test):
	"""Every template name already stamped on an expanded row of this doc."""
	present = set()
	for table in ("normal_test_items", "descriptive_test_items"):
		for row in lab_test.get(table) or []:
			if row.get("template"):
				present.add(row.get("template"))
	return present


def _leaf_template_names(leaves):
	"""Template names a leaf list would stamp onto rows — used to decide
	whether a member is already present."""
	names = set()
	for leaf in leaves:
		if leaf[0] in ("template", "header"):
			names.add(leaf[1].name)
		elif leaf[0] == "newline":
			names.add(leaf[2])
	return names


def _reorder_rows(lab_test, template_doc):
	"""Restore package order after appending.

	Appended rows land at the end of the child table, so TFT would print after
	eGFR instead of at its configured position 11. Rebuild the order from the
	package's `lab_test_groups` idx: every row is keyed by the group position
	its template belongs to, then stable-sorted so a Compound's header + its
	events stay together and in sequence.
	"""
	order = {}
	for row in _group_rows(template_doc):
		child = row.get("lab_test_template")
		pos = row.idx or 0
		if child:
			for leaf in _collect_leaves(child):
				if leaf[0] in ("template", "header"):
					order.setdefault(leaf[1].name, pos)
				elif leaf[0] == "newline":
					order.setdefault(leaf[2], pos)
		else:
			order.setdefault(template_doc.name, pos)

	if not order:
		return

	tail = max(order.values()) + 1
	for table in ("normal_test_items", "descriptive_test_items"):
		rows = lab_test.get(table) or []
		if not rows:
			continue
		# `sorted` is stable, so rows sharing a key keep their existing
		# relative order (header before its analytes).
		rows.sort(key=lambda r: order.get(r.get("template"), tail))
		for i, row in enumerate(rows, start=1):
			row.idx = i


def expand_nested_groups(doc, method=None):
	"""`Lab Test.after_insert` hook — expand Grouped members of a Grouped
	template, which Marley's `load_result_format()` skips.

	Never raises into the caller: a failure here must not roll back an
	otherwise-valid Lab Test. It logs and leaves the doc as Marley built it.
	"""
	try:
		if not doc.get("template"):
			return

		template_doc = frappe.get_doc("Lab Test Template", doc.template)
		if (template_doc.get("lab_test_template_type") or "") != "Grouped":
			return

		nested = [
			row for row in _group_rows(template_doc)
			if row.get("lab_test_template")
			and frappe.db.get_value(
				"Lab Test Template", row.get("lab_test_template"), "lab_test_template_type"
			) == "Grouped"
		]
		if not nested:
			return

		# Marley saved the doc during its own after_insert — re-read so we
		# append onto the rows it just wrote, not a stale in-memory copy.
		doc.reload()
		present = _present_templates(doc)

		added = 0
		for row in nested:
			leaves = _collect_leaves(row.get("lab_test_template"))
			if not leaves:
				continue
			# Idempotency: if any analyte of this member already landed on the
			# doc, Marley (or a previous run) handled it — leave it alone.
			if _leaf_template_names(leaves) & present:
				continue
			for leaf in leaves:
				_build_leaf(doc, leaf)
			added += 1

		if not added:
			return

		_reorder_rows(doc, template_doc)
		doc.save(ignore_permissions=True)
		frappe.logger("diagnostic_management").info(
			f"expand_nested_groups: {doc.name} — expanded {added} nested package(s) "
			f"under {doc.template}"
		)
	except Exception:
		frappe.log_error(
			title=f"expand_nested_groups failed for {doc.name}",
			message=frappe.get_traceback(),
		)


def section_map(package_name):
	"""Map each leaf template -> the PANEL heading its results belong under.

	A package's printed report should read as one section per panel (FBC,
	Lipid Profile, Liver Function, Urinalysis, TFT…), not one undifferentiated
	list. The Lab Test row only knows its *leaf* template, which is too fine a
	grain: grouping by it would give every standalone analyte (Vitamin B12,
	Urea, eGFR…) a one-row section of its own.

	So the heading is the package's own group-row member that OWNS the leaf:
	  - member is Compound or Grouped  -> that member's name is the heading
	    (all of FBC's 18 analytes -> "Full Blood Count", TSH/FT3/FT4 -> "TFT")
	  - member is a plain Single       -> no heading; it belongs to the
	    package's own catch-all section

	Returns {leaf_template_name: heading}. Leaves of Single members are
	deliberately absent, so callers fall back to the package name.
	"""
	mapping = {}
	if not package_name or not frappe.db.exists("Lab Test Template", package_name):
		return mapping
	tmpl = frappe.get_doc("Lab Test Template", package_name)
	if (tmpl.get("lab_test_template_type") or "") != "Grouped":
		return mapping

	for row in _group_rows(tmpl):
		child = row.get("lab_test_template")
		if not child:
			continue
		child_type = frappe.db.get_value("Lab Test Template", child, "lab_test_template_type")
		if child_type not in ("Compound", "Grouped"):
			# Standalone analyte — leave it to the package's catch-all section.
			continue
		heading = frappe.db.get_value("Lab Test Template", child, "lab_test_name") or child
		# Every leaf under this member (recursing through nested packages)
		# prints under the member's heading.
		for leaf in _collect_leaves(child):
			if leaf[0] in ("template", "header"):
				mapping.setdefault(leaf[1].name, heading)
			elif leaf[0] == "newline":
				mapping.setdefault(leaf[2], heading)
		mapping.setdefault(child, heading)
	return mapping


def _describe_member(child_name):
	"""Diagnose ONE group member, purely from the templates — no Lab Test or
	Lab Report involved. This is what tells you whether a panel will ever
	expand, and if not, why."""
	info = {"template": child_name, "exists": False, "type": None, "disabled": None,
	        "group_rows": 0, "analyte_rows": 0, "leaf_count": 0, "leaves": [], "problem": None}
	if not child_name:
		info["problem"] = "group row has no template (an 'Add new line' entry)"
		return info
	if not frappe.db.exists("Lab Test Template", child_name):
		info["problem"] = "template does not exist — the group row points at a deleted/renamed template"
		return info

	tmpl = frappe.get_doc("Lab Test Template", child_name)
	info["exists"] = True
	info["type"] = tmpl.get("lab_test_template_type") or "Single"
	info["disabled"] = int(tmpl.get("disabled") or 0)
	info["group_rows"] = len(tmpl.get("lab_test_groups") or [])
	info["analyte_rows"] = len(tmpl.get("normal_test_templates") or []) + len(
		tmpl.get("descriptive_test_templates") or []
	)

	leaves = _collect_leaves(child_name)
	info["leaf_count"] = len([l for l in leaves if l[0] == "template"])
	info["leaves"] = [l[1].name for l in leaves if l[0] == "template"]

	if info["type"] == "Grouped":
		if info["group_rows"] == 0:
			info["problem"] = ("nested package with NO tests in its lab_test_groups table — "
			                   "nothing to expand, so it can never print")
		elif info["leaf_count"] == 0:
			info["problem"] = "nested package whose members are all empty/missing"
	elif info["type"] in ("Compound", "Descriptive") and info["analyte_rows"] == 0:
		info["problem"] = f"{info['type']} template with no analyte rows configured"
	if info["disabled"]:
		info["problem"] = (info["problem"] + "; also DISABLED") if info["problem"] else "template is DISABLED"
	return info


@frappe.whitelist()
def audit_template(name: str) -> dict:
	"""Explain exactly what ONE Grouped template will expand into.

	Reads only Lab Test Template data — no Lab Test, no Lab Report. Open in a
	browser while logged in:
	  /api/method/diagnostic_management.overrides.lab_test_expansion.audit_template?name=Afya%20Bora%20Comprehensive%20Male%20Package
	"""
	if not frappe.db.exists("Lab Test Template", name):
		frappe.throw(f"Lab Test Template {name} not found")
	tmpl = frappe.get_doc("Lab Test Template", name)
	ttype = tmpl.get("lab_test_template_type") or "Single"
	members = []
	for row in _group_rows(tmpl):
		info = _describe_member(row.get("lab_test_template"))
		info["idx"] = row.idx
		# Marley expands Single / Compound / Descriptive members and silently
		# skips Grouped ones. That single fact is the whole bug.
		info["marley_expands"] = info["type"] in ("Single", "Compound", "Descriptive")
		info["needs_recursion"] = info["type"] == "Grouped"
		members.append(info)

	return {
		"template": name,
		"type": ttype,
		"is_package": ttype == "Grouped",
		"member_count": len(members),
		"nested_packages": [m["template"] for m in members if m["needs_recursion"]],
		"dropped_by_marley": [m["template"] for m in members if m["needs_recursion"]],
		"broken": [{"template": m["template"], "problem": m["problem"]} for m in members if m["problem"]],
		"members": members,
	}


@frappe.whitelist()
def audit_nested_groups(limit: int = 500) -> dict:
	"""Scan EVERY Grouped Lab Test Template for packages nested inside packages.

	Template-only — needs no Lab Test or Lab Report to run, so it works before
	anything is ordered. Open in a browser while logged in:
	  /api/method/diagnostic_management.overrides.lab_test_expansion.audit_nested_groups
	"""
	packages = frappe.get_all(
		"Lab Test Template",
		filters={"lab_test_template_type": "Grouped"},
		pluck="name",
		limit_page_length=int(limit),
	)
	affected, broken = [], []
	for pkg in packages:
		report = audit_template(pkg)
		if report["nested_packages"]:
			affected.append({
				"package": pkg,
				"nested_packages": report["nested_packages"],
				"analytes_lost": sum(
					m["leaf_count"] for m in report["members"] if m["needs_recursion"]
				),
			})
		for b in report["broken"]:
			broken.append({"package": pkg, **b})

	return {
		"grouped_templates_scanned": len(packages),
		"packages_with_nested_packages": len(affected),
		"affected": affected,
		"misconfigured_members": broken,
	}


@frappe.whitelist()
def repair_lab_test(name: str, rebuild_report: int = 1) -> dict:
	"""Backfill one already-created Lab Test that lost its nested packages.

	Runs the same expansion against an existing doc, then (by default) rebuilds
	the Lab Report off the same Sales Invoice so `grouped_results` picks the new
	analytes up.
	"""
	doc = frappe.get_doc("Lab Test", name)
	if int(doc.docstatus or 0) != 0:
		frappe.throw("Only draft Lab Tests can be repaired — submitted results are locked.")

	before = len(doc.get("normal_test_items") or [])
	expand_nested_groups(doc)
	doc.reload()
	after = len(doc.get("normal_test_items") or [])

	report = None
	if int(rebuild_report or 0) and after > before and doc.get("custom_sales_invoice"):
		report = frappe.db.get_value(
			"Lab Report", {"custom_sales_invoice": doc.custom_sales_invoice}, "name"
		)
		if report:
			frappe.get_doc("Lab Report", report).refetch_from_invoice()

	return {
		"ok": True,
		"lab_test": name,
		"rows_before": before,
		"rows_after": after,
		"rows_added": after - before,
		"lab_report_rebuilt": report,
	}


@frappe.whitelist()
def repair_lab_tests(from_date: str | None = None, limit: int = 200, dry_run: int = 1) -> dict:
	"""Bulk backfill draft Lab Tests raised off a Grouped template.

	Defaults to `dry_run=1` — it reports which Lab Tests WOULD gain rows without
	writing. Re-run with `dry_run=0` to apply.
	"""
	packages = frappe.get_all(
		"Lab Test Template",
		filters={"lab_test_template_type": "Grouped"},
		pluck="name",
	)
	if not packages:
		return {"ok": True, "candidates": 0, "repaired": []}

	filters = {"template": ["in", packages], "docstatus": 0}
	if from_date:
		filters["creation"] = [">=", from_date]

	names = frappe.get_all(
		"Lab Test", filters=filters, pluck="name", order_by="creation desc", limit_page_length=int(limit)
	)

	repaired = []
	for name in names:
		doc = frappe.get_doc("Lab Test", name)
		template_doc = frappe.get_doc("Lab Test Template", doc.template)
		present = _present_templates(doc)
		missing = []
		for row in _group_rows(template_doc):
			child = row.get("lab_test_template")
			if not child:
				continue
			if frappe.db.get_value("Lab Test Template", child, "lab_test_template_type") != "Grouped":
				continue
			leaves = _collect_leaves(child)
			if leaves and not (_leaf_template_names(leaves) & present):
				missing.append(child)
		if not missing:
			continue
		entry = {"lab_test": name, "template": doc.template, "missing": missing}
		if not int(dry_run or 0):
			entry["result"] = repair_lab_test(name, rebuild_report=1)
		repaired.append(entry)

	return {
		"ok": True,
		"dry_run": bool(int(dry_run or 0)),
		"scanned": len(names),
		"candidates": len(repaired),
		"repaired": repaired,
	}
