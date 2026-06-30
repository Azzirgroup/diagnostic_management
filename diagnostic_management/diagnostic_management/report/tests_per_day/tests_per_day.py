# Copyright (c) 2026, Genetest Laboratory
# Tests per Day Report - Monitor workload and demand

import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)

    return columns, data, None, chart, summary


def get_columns():
    return [
        {
            "fieldname": "posting_date",
            "label": _("Date"),
            "fieldtype": "Date",
            "width": 120
        },
        {
            "fieldname": "total_created",
            "label": _("Tests Created"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "completed",
            "label": _("Completed"),
            "fieldtype": "Int",
            "width": 120
        },
        {
            "fieldname": "processing",
            "label": _("Processing"),
            "fieldtype": "Int",
            "width": 120
        },
    ]


def get_data(filters):
    conditions = get_conditions(filters)

    # Patient join is conditional — only added when filtering by branch so
    # the un-filtered query stays cheap on the indexed tabLab Test scan.
    patient_join = " LEFT JOIN `tabPatient` p ON p.name = lt.patient" if filters.get("branch") else ""
    data = frappe.db.sql("""
        SELECT
            COALESCE(lt.date, DATE(lt.creation)) as posting_date,
            COUNT(*) as total_created,
            SUM(CASE WHEN lt.status = 'Completed' AND lt.docstatus = 1 THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN lt.status = 'Processing' AND lt.docstatus = 1 THEN 1 ELSE 0 END) as processing
        FROM `tabLab Test` lt
        {patient_join}
        WHERE lt.docstatus = 1
        {conditions}
        GROUP BY COALESCE(lt.date, DATE(lt.creation))
        ORDER BY posting_date DESC
    """.format(patient_join=patient_join, conditions=conditions), filters, as_dict=1)

    return data


def get_conditions(filters):
    conditions = []

    if filters.get("from_date"):
        conditions.append("COALESCE(lt.date, DATE(lt.creation)) >= %(from_date)s")
    if filters.get("to_date"):
        conditions.append("COALESCE(lt.date, DATE(lt.creation)) <= %(to_date)s")
    if filters.get("template"):
        conditions.append("lt.template = %(template)s")
    if filters.get("department"):
        conditions.append("lt.department = %(department)s")
    if filters.get("company"):
        conditions.append("lt.company = %(company)s")
    # Branch is on Patient, joined into the query when this filter is set.
    if filters.get("branch"):
        conditions.append("p.branch = %(branch)s")

    return " AND " + " AND ".join(conditions) if conditions else ""


def get_chart(data):
    if not data:
        return None

    sorted_data = sorted(data, key=lambda x: x.get("posting_date") or "")

    labels = [str(d.get("posting_date", "")) for d in sorted_data]
    total_created = [d.get("total_created", 0) for d in sorted_data]
    completed = [d.get("completed", 0) for d in sorted_data]

    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": _("Tests Created"), "values": total_created},
                {"name": _("Completed"), "values": completed},
            ]
        },
        "type": "bar",
        "colors": ["#3498db", "#2ecc71"],
    }


def get_summary(data):
    if not data:
        return []

    total = sum(d.get("total_created", 0) for d in data)
    completed = sum(d.get("completed", 0) for d in data)
    processing = sum(d.get("processing", 0) for d in data)
    days = len(data)
    avg_per_day = round(total / days, 1) if days else 0

    return [
        {
            "value": total,
            "label": _("Total Tests"),
            "datatype": "Int"
        },
        {
            "value": completed,
            "label": _("Completed"),
            "datatype": "Int",
            "indicator": "green"
        },
        {
            "value": processing,
            "label": _("Processing"),
            "datatype": "Int",
            "indicator": "orange"
        },
        {
            "value": avg_per_day,
            "label": _("Avg Tests/Day"),
            "datatype": "Float"
        },
        {
            "value": days,
            "label": _("Days"),
            "datatype": "Int"
        }
    ]
