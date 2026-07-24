"""Sales Register with the referring Doctor.

ERPNext's Sales Register with one extra column: `Sales Invoice.custom_doctor`,
the referring doctor picked at Billing. Rather than fork the report (and inherit
the maintenance of every column, tax breakdown and dimension ERPNext adds later)
this calls ERPNext's own `_execute()` through its supported extension point,
`additional_table_columns` — the same hook `item_wise_sales_register` uses.

That means every column, filter and total stays identical to the stock report
and keeps tracking upstream; the Doctor column is selected in the same query,
so there is no per-row lookup.

The Doctor filter is applied after the fact because ERPNext's `get_conditions()`
only understands its own filter set. Rows come back as dicts keyed by fieldname,
so filtering on `custom_doctor` is exact.
"""

import frappe
from frappe import _

from erpnext.accounts.report.sales_register.sales_register import _execute

DOCTOR_FIELD = "custom_doctor"


def _doctor_column() -> dict:
	return {
		"label": _("Doctor"),
		"fieldname": DOCTOR_FIELD,
		"fieldtype": "Data",
		"width": 160,
	}


def execute(filters=None):
	filters = frappe._dict(filters or {})

	# Pulled out before delegating — ERPNext would reject an unknown filter.
	doctor = (filters.pop("doctor", None) or "").strip()

	if not frappe.db.has_column("Sales Invoice", DOCTOR_FIELD):
		# Custom field not installed yet (fresh site, pre-migrate). Degrade to
		# the stock report rather than throwing a SQL error at the user.
		frappe.msgprint(
			_("Sales Invoice has no {0} field yet — showing the standard Sales Register. "
			  "Run a migrate to install it.").format(frappe.bold(DOCTOR_FIELD)),
			indicator="orange", alert=True,
		)
		return _execute(filters)

	result = _execute(filters, additional_table_columns=[_doctor_column()])

	# _execute returns a variable-length tuple across ERPNext versions
	# (columns, data[, message, chart, report_summary]). Keep whatever else it
	# hands back instead of assuming a 2-tuple.
	columns, data = result[0], result[1]
	rest = tuple(result[2:])

	if doctor:
		wanted = doctor.casefold()
		data = [
			row for row in data
			if isinstance(row, dict) and (row.get(DOCTOR_FIELD) or "").strip().casefold() == wanted
		]

	return (columns, data) + rest


@frappe.whitelist()
def doctor_options(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
	"""Link-style options for the Doctor filter.

	`custom_doctor` is a free-text Data field, so the choices are the distinct
	values actually recorded on invoices — no separate master to point a Link
	filter at, and no stale names.
	"""
	conditions, values = ["COALESCE(custom_doctor, '') != ''"], []
	if txt:
		conditions.append("custom_doctor LIKE %s")
		values.append(f"%{txt}%")
	company = (filters or {}).get("company") if isinstance(filters, dict) else None
	if company:
		conditions.append("company = %s")
		values.append(company)

	return frappe.db.sql(
		f"""
		SELECT DISTINCT custom_doctor
		FROM `tabSales Invoice`
		WHERE docstatus = 1 AND {" AND ".join(conditions)}
		ORDER BY custom_doctor ASC
		LIMIT %s, %s
		""",
		(*values, int(start), int(page_len)),
	)
