# Copyright (c) 2025, Genetest Laboratory
# TAT per Test - GENETEST

import frappe
from frappe import _
from frappe.utils import flt, time_diff_in_hours, get_datetime, now_datetime


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)

	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"fieldname": "lab_test",
			"label": _("Lab Test"),
			"fieldtype": "Link",
			"options": "Lab Test",
			"width": 150,
		},
		{
			"fieldname": "lab_test_name",
			"label": _("Test Name"),
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"fieldname": "patient",
			"label": _("Patient"),
			"fieldtype": "Link",
			"options": "Patient",
			"width": 120,
		},
		{
			"fieldname": "patient_name",
			"label": _("Patient Name"),
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"fieldname": "template",
			"label": _("Template"),
			"fieldtype": "Link",
			"options": "Lab Test Template",
			"width": 150,
		},
		{
			"fieldname": "creation_date",
			"label": _("Order Date"),
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"fieldname": "result_date",
			"label": _("Result Date"),
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"fieldname": "expected_tat",
			"label": _("Expected TAT (hrs)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 120,
		},
		{
			"fieldname": "actual_tat",
			"label": _("Actual TAT (hrs)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 120,
		},
		{
			"fieldname": "tat_variance",
			"label": _("Variance (hrs)"),
			"fieldtype": "Float",
			"precision": 1,
			"width": 110,
		},
		{
			"fieldname": "status",
			"label": _("Status"),
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"fieldname": "tat_status",
			"label": _("TAT Status"),
			"fieldtype": "Data",
			"width": 100,
		},
	]


def get_data(filters):
	conditions = get_conditions(filters)
	default_tat = filters.get("default_tat", 24)

	data = frappe.db.sql(
		"""
		SELECT
			lt.name as lab_test,
			lt.lab_test_name,
			lt.patient,
			lt.patient_name,
			lt.template,
			lt.creation as creation_date,
			lt.result_date,
			lt.status
		FROM `tabLab Test` lt
		WHERE lt.docstatus < 2
		{conditions}
		ORDER BY lt.creation DESC
	""".format(conditions=conditions),
		filters,
		as_dict=1,
	)

	result = []
	for row in data:
		row["expected_tat"] = default_tat
		actual_tat = None
		tat_variance = None
		tat_status = "Pending"

		if row.result_date and row.creation_date:
			creation_dt = get_datetime(row.creation_date)
			result_dt = get_datetime(row.result_date)
			actual_tat = time_diff_in_hours(result_dt, creation_dt)

			if row.expected_tat:
				tat_variance = actual_tat - flt(row.expected_tat)
				tat_status = "Within TAT" if tat_variance <= 0 else "Breached"
			else:
				tat_status = "Completed"
		elif row.status in ["Completed", "Approved"]:
			tat_status = "No Result Date"
		elif row.expected_tat:
			creation_dt = get_datetime(row.creation_date)
			current_hours = time_diff_in_hours(now_datetime(), creation_dt)
			if current_hours > flt(row.expected_tat):
				tat_status = "Overdue"
				actual_tat = current_hours
				tat_variance = current_hours - flt(row.expected_tat)
			else:
				tat_status = "In Progress"

		result.append(
			{
				"lab_test": row.lab_test,
				"lab_test_name": row.lab_test_name,
				"patient": row.patient,
				"patient_name": row.patient_name,
				"template": row.template,
				"creation_date": row.creation_date,
				"result_date": row.result_date,
				"expected_tat": row.expected_tat,
				"actual_tat": round(actual_tat, 1) if actual_tat else None,
				"tat_variance": round(tat_variance, 1) if tat_variance else None,
				"status": row.status,
				"tat_status": tat_status,
			}
		)

	return result


def get_conditions(filters):
	conditions = []

	if filters.get("company"):
		conditions.append("lt.company = %(company)s")
	if filters.get("from_date"):
		conditions.append("lt.creation >= %(from_date)s")
	if filters.get("to_date"):
		conditions.append("lt.creation <= %(to_date)s")
	if filters.get("template"):
		conditions.append("lt.template = %(template)s")
	if filters.get("status"):
		conditions.append("lt.status = %(status)s")
	if filters.get("patient"):
		conditions.append("lt.patient = %(patient)s")

	return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart(data):
	if not data:
		return None

	status_count = {}
	for row in data:
		status = row.get("tat_status", "Unknown")
		status_count[status] = status_count.get(status, 0) + 1

	return {
		"data": {
			"labels": list(status_count.keys()),
			"datasets": [
				{"name": "TAT Status", "values": list(status_count.values())}
			],
		},
		"type": "donut",
		"colors": ["#2ecc71", "#e74c3c", "#f39c12", "#3498db", "#95a5a6"],
	}


def get_summary(data):
	if not data:
		return []

	total = len(data)
	within_tat = len([d for d in data if d.get("tat_status") == "Within TAT"])
	breached = len([d for d in data if d.get("tat_status") == "Breached"])
	overdue = len([d for d in data if d.get("tat_status") == "Overdue"])

	completed_with_tat = [d for d in data if d.get("actual_tat")]
	avg_tat = (
		sum(d.get("actual_tat", 0) for d in completed_with_tat) / len(completed_with_tat)
		if completed_with_tat
		else 0
	)

	compliance_rate = (within_tat / total * 100) if total > 0 else 0

	return [
		{"value": total, "label": _("Total Tests"), "datatype": "Int"},
		{
			"value": within_tat,
			"label": _("Within TAT"),
			"datatype": "Int",
			"indicator": "green",
		},
		{
			"value": breached + overdue,
			"label": _("TAT Breaches"),
			"datatype": "Int",
			"indicator": "red",
		},
		{
			"value": round(avg_tat, 1),
			"label": _("Avg TAT (hrs)"),
			"datatype": "Float",
		},
		{
			"value": round(compliance_rate, 1),
			"label": _("Compliance Rate %"),
			"datatype": "Percent",
			"indicator": "green"
			if compliance_rate >= 90
			else "orange"
			if compliance_rate >= 70
			else "red",
		},
	]
