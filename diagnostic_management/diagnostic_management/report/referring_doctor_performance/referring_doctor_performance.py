"""Referring Doctor Performance — aggregate patients, tests, revenue per doctor."""
import frappe
from frappe import _


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_apply_default_dates(filters)

	columns = _get_columns()
	rows = _get_data(filters)
	chart = _get_chart(rows)
	summary = _get_summary(rows)
	return columns, rows, None, chart, summary


def _apply_default_dates(filters):
	if not filters.get("from_date"):
		filters.from_date = frappe.utils.add_months(frappe.utils.nowdate(), -1)
	if not filters.get("to_date"):
		filters.to_date = frappe.utils.nowdate()


def _get_columns():
	return [
		{"label": _("Referring Doctor"), "fieldname": "doctor", "fieldtype": "Link", "options": "Doctor", "width": 200},
		{"label": _("Doctor Name / Invoice"), "fieldname": "doctor_name", "fieldtype": "Data", "width": 250},
		{"label": _("Invoice"), "fieldname": "invoice", "fieldtype": "Link", "options": "Sales Invoice", "width": 160},
		{"label": _("Patient"), "fieldname": "patient", "fieldtype": "Link", "options": "Patient", "width": 140},
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		{"label": _("Patients"), "fieldname": "patients", "fieldtype": "Int", "width": 90},
		{"label": _("Tests"), "fieldname": "tests", "fieldtype": "Int", "width": 80},
		{"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 130},
		{"label": _("Avg Revenue / Patient"), "fieldname": "avg_per_patient", "fieldtype": "Currency", "width": 160},
		{"label": _("Avg Revenue / Test"), "fieldname": "avg_per_test", "fieldtype": "Currency", "width": 160},
		{"label": _("Top Test"), "fieldname": "top_test", "fieldtype": "Data", "width": 200},
		{"label": _("Outstanding"), "fieldname": "outstanding", "fieldtype": "Currency", "width": 130},
	]


def _get_data(filters):
	conditions = _build_conditions(filters)

	doctor_rows = frappe.db.sql(
		f"""
		SELECT
			COALESCE(si.custom_doctor, '') AS doctor,
			COALESCE(NULLIF(si.custom_doctor, ''), '(No Doctor)') AS doctor_name,
			COUNT(DISTINCT si.patient) AS patients,
			COUNT(sii.name) AS tests,
			SUM(sii.net_amount) AS revenue,
			SUM(DISTINCT si.outstanding_amount) AS outstanding
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		LEFT JOIN `tabLab Test Template` ltt ON ltt.item = sii.item_code
		LEFT JOIN `tabPatient` p ON p.name = si.patient
		WHERE si.docstatus = 1
		  {conditions}
		GROUP BY COALESCE(si.custom_doctor, '')
		ORDER BY revenue DESC
		""",
		filters,
		as_dict=1,
	)

	output = []
	for r in doctor_rows:
		r["revenue"] = r["revenue"] or 0
		r["avg_per_patient"] = (r["revenue"] / r["patients"]) if r["patients"] else 0
		r["avg_per_test"] = (r["revenue"] / r["tests"]) if r["tests"] else 0
		r["top_test"] = _get_top_test(r["doctor"], filters)
		r["indent"] = 0
		output.append(r)

		for inv in _get_invoices_for_doctor(r["doctor"], filters):
			output.append({
				"doctor": "",
				"doctor_name": f"↳ {inv['name']}",
				"invoice": inv["name"],
				"patient": inv["patient"],
				"posting_date": inv["posting_date"],
				"patients": None,
				"tests": inv["tests"],
				"revenue": inv["revenue"],
				"avg_per_patient": None,
				"avg_per_test": (inv["revenue"] / inv["tests"]) if inv["tests"] else 0,
				"top_test": inv["items"],
				"outstanding": inv["outstanding_amount"],
				"indent": 1,
			})

	return output


def _get_invoices_for_doctor(doctor, filters):
	"""Per-invoice detail rows for one doctor within the current filter set."""
	conditions = _build_conditions(filters)
	params = dict(filters)
	params["_doctor"] = doctor
	return frappe.db.sql(
		f"""
		SELECT
			si.name,
			si.patient,
			si.posting_date,
			si.outstanding_amount,
			COUNT(sii.name) AS tests,
			SUM(sii.net_amount) AS revenue,
			GROUP_CONCAT(sii.item_name SEPARATOR ', ') AS items
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		LEFT JOIN `tabLab Test Template` ltt ON ltt.item = sii.item_code
		LEFT JOIN `tabPatient` p ON p.name = si.patient
		WHERE si.docstatus = 1
		  {conditions}
		  AND COALESCE(si.custom_doctor, '') = %(_doctor)s
		GROUP BY si.name
		ORDER BY si.posting_date DESC, si.name DESC
		""",
		params,
		as_dict=1,
	)


def _get_top_test(doctor, filters):
	conditions = _build_conditions(filters)
	doctor_cond = " AND COALESCE(si.custom_doctor, '') = %(_doctor)s"
	params = dict(filters)
	params["_doctor"] = doctor
	row = frappe.db.sql(
		f"""
		SELECT sii.item_name, COUNT(*) AS cnt
		FROM `tabSales Invoice` si
		INNER JOIN `tabSales Invoice Item` sii ON sii.parent = si.name
		LEFT JOIN `tabLab Test Template` ltt ON ltt.item = sii.item_code
		LEFT JOIN `tabPatient` p ON p.name = si.patient
		WHERE si.docstatus = 1
		  {conditions}
		  {doctor_cond}
		GROUP BY sii.item_name
		ORDER BY cnt DESC
		LIMIT 1
		""",
		params,
		as_dict=1,
	)
	return row[0].item_name if row else ""


def _build_conditions(filters):
	parts = ["AND si.posting_date BETWEEN %(from_date)s AND %(to_date)s"]
	if filters.get("status"):
		parts.append("AND si.status = %(status)s")
	if filters.get("referring_doctor"):
		parts.append("AND si.custom_doctor = %(referring_doctor)s")
	if filters.get("department"):
		parts.append("AND ltt.department = %(department)s")
	if filters.get("customer"):
		parts.append("AND si.customer = %(customer)s")
	if filters.get("branch"):
		parts.append("AND p.branch = %(branch)s")
	return " ".join(parts)


def _get_chart(rows):
	doctor_rows = [r for r in rows if r.get("indent") == 0]
	if not doctor_rows:
		return None
	top = doctor_rows[:10]
	return {
		"data": {
			"labels": [r["doctor_name"] for r in top],
			"datasets": [
				{"name": _("Revenue"), "values": [float(r["revenue"] or 0) for r in top]},
				{"name": _("Patients"), "values": [int(r["patients"] or 0) for r in top]},
			],
		},
		"type": "bar",
		"colors": ["#2490ef", "#48bb78"],
		"axisOptions": {"xIsSeries": 1},
	}


def _get_summary(rows):
	doctor_rows = [r for r in rows if r.get("indent") == 0]
	total_patients = sum((r.get("patients") or 0) for r in doctor_rows)
	total_tests = sum((r.get("tests") or 0) for r in doctor_rows)
	total_revenue = sum((r.get("revenue") or 0) for r in doctor_rows)
	active_doctors = sum(1 for r in doctor_rows if r.get("doctor"))
	avg_per_patient = (total_revenue / total_patients) if total_patients else 0
	return [
		{"label": _("Total Patients"), "value": total_patients, "datatype": "Int", "indicator": "Blue"},
		{"label": _("Total Tests"), "value": total_tests, "datatype": "Int", "indicator": "Blue"},
		{"label": _("Total Revenue"), "value": total_revenue, "datatype": "Currency", "indicator": "Green"},
		{"label": _("Active Referring Doctors"), "value": active_doctors, "datatype": "Int", "indicator": "Orange"},
		{"label": _("Avg Revenue / Patient"), "value": avg_per_patient, "datatype": "Currency", "indicator": "Purple"},
	]
