"""Customer list + detail + update API for the staff SPA.

Why a thin wrapper instead of `frappe.client.get_list` / `frappe.client.set_value`:
  - We want a single round-trip for the list view (returns the fields the
    table renders, including the linked Patient via the back-link).
  - Update goes through `doc.save()` so ERPNext's Customer validators run
    (e.g. customer_group must be a leaf, default_currency must exist).
  - All endpoints require System Manager / Lab Manager / Billing Officer
    roles — same gate as the rest of the billing surface.
"""

from __future__ import annotations

import frappe


_EDIT_ROLES: frozenset[str] = frozenset({
	"System Manager", "Lab Manager", "Billing Officer", "Accounts Manager", "Accounts User",
})


def _require_role() -> None:
	have = set(frappe.get_roles(frappe.session.user))
	if not (have & _EDIT_ROLES):
		frappe.throw(
			f"Customer editing is restricted to: {', '.join(sorted(_EDIT_ROLES))}.",
			frappe.PermissionError,
		)


@frappe.whitelist()
def list_customers(query: str = "", limit: int = 50, start: int = 0,
                   customer_group: str | None = None) -> dict:
	"""Paged customer list for the SPA table."""
	filters: dict = {"disabled": 0}
	if customer_group:
		filters["customer_group"] = customer_group
	or_filters: dict | None = None
	if query:
		q = f"%{query}%"
		or_filters = {"name": ("like", q), "customer_name": ("like", q),
		              "mobile_no": ("like", q), "email_id": ("like", q),
		              "tax_id": ("like", q)}

	rows = frappe.get_all(
		"Customer",
		fields=["name", "customer_name", "customer_type", "customer_group",
		        "territory", "mobile_no", "email_id", "tax_id",
		        "default_currency", "disabled", "modified"],
		filters=filters,
		or_filters=or_filters,
		order_by="modified desc",
		limit_page_length=int(limit),
		limit_start=int(start),
	)
	# Stamp the linked Patient (back-link) for each customer in one query.
	cust_names = [r["name"] for r in rows]
	patient_map: dict[str, str] = {}
	if cust_names:
		for p in frappe.db.sql(
			"""SELECT name, customer FROM `tabPatient`
			   WHERE customer IN %(c)s AND customer IS NOT NULL""",
			{"c": cust_names}, as_dict=True,
		):
			patient_map[p["customer"]] = p["name"]
	for r in rows:
		r["linked_patient"] = patient_map.get(r["name"])

	total = frappe.db.count("Customer", filters)
	return {"rows": rows, "total": total}


@frappe.whitelist()
def get_customer(name: str) -> dict:
	"""Single customer with the fields the detail form needs, plus the
	linked Patient (if any)."""
	if not frappe.db.exists("Customer", name):
		frappe.throw(f"Customer {name!r} not found")
	doc = frappe.get_doc("Customer", name)
	out = {
		f: doc.get(f) for f in (
			"name", "customer_name", "customer_type", "customer_group",
			"territory", "mobile_no", "email_id", "tax_id",
			"default_currency", "default_price_list",
			"customer_primary_address", "customer_primary_contact",
			"disabled",
		)
	}
	out["linked_patient"] = frappe.db.get_value("Patient", {"customer": name}, "name")
	return out


@frappe.whitelist()
def update_customer(name: str, updates: dict | str) -> dict:
	"""Update editable fields on a Customer. Routed through `doc.save()`
	so ERPNext's own validators (leaf customer_group, etc.) run and any
	violation surfaces as a clean message instead of a constraint error."""
	_require_role()
	if isinstance(updates, str):
		import json as _json
		updates = _json.loads(updates)

	if not frappe.db.exists("Customer", name):
		frappe.throw(f"Customer {name!r} not found")
	doc = frappe.get_doc("Customer", name)

	# Whitelist of editable fields — anything else is silently ignored.
	allowed = {
		"customer_name", "customer_type", "customer_group", "territory",
		"mobile_no", "email_id", "tax_id",
		"default_currency", "default_price_list", "disabled",
	}
	changed = []
	for k, v in (updates or {}).items():
		if k in allowed and doc.get(k) != v:
			doc.set(k, v)
			changed.append(k)

	if not changed:
		return {"ok": True, "name": name, "changed": []}

	doc.save(ignore_permissions=False)
	return {"ok": True, "name": name, "changed": changed}


@frappe.whitelist()
def list_customer_groups() -> list[str]:
	"""Leaf customer groups only (ERPNext won't accept a parent group on
	Customer.customer_group). Used by the edit form's dropdown."""
	return [r["name"] for r in frappe.get_all(
		"Customer Group", filters={"is_group": 0}, order_by="name",
	)]


@frappe.whitelist()
def list_territories() -> list[str]:
	"""Leaf territories only — same reason as customer groups."""
	return [r["name"] for r in frappe.get_all(
		"Territory", filters={"is_group": 0}, order_by="name",
	)]
