# Copyright (c) 2025, Genetest Laboratory
# Patient History Report - Shows all lab tests and results for a patient

import frappe
from frappe import _
from frappe.utils import getdate, flt


def execute(filters=None):
    if not filters.get("patient"):
        frappe.throw(_("Please select a Patient"))

    columns = get_columns()
    data = get_data(filters)
    message = get_patient_info(filters.get("patient"))

    return columns, data, message


def get_columns():
    return [
        {
            "fieldname": "test_date",
            "label": _("Test Date"),
            "fieldtype": "Date",
            "width": 100
        },
        {
            "fieldname": "lab_test",
            "label": _("Lab Test"),
            "fieldtype": "Link",
            "options": "Lab Test",
            "width": 140
        },
        {
            "fieldname": "test_name",
            "label": _("Test Name"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "parameter",
            "label": _("Parameter"),
            "fieldtype": "Data",
            "width": 150
        },
        {
            "fieldname": "result_value",
            "label": _("Result"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "unit",
            "label": _("Unit"),
            "fieldtype": "Data",
            "width": 80
        },
        {
            "fieldname": "reference_range",
            "label": _("Reference Range"),
            "fieldtype": "Data",
            "width": 130
        },
        {
            "fieldname": "result_status",
            "label": _("Status"),
            "fieldtype": "Data",
            "width": 80
        },
        {
            "fieldname": "test_status",
            "label": _("Test Status"),
            "fieldtype": "Data",
            "width": 100
        },
        {
            "fieldname": "practitioner",
            "label": _("Ordered By"),
            "fieldtype": "Link",
            "options": "Healthcare Practitioner",
            "width": 130
        }
    ]


def get_data(filters):
    patient = filters.get("patient")

    # Get all lab tests for patient
    tests = frappe.get_all("Lab Test",
        filters={
            "patient": patient,
            "docstatus": ["<", 2]
        },
        fields=["name", "lab_test_name", "template", "result_date", "creation",
                "status", "practitioner"],
        order_by="creation desc"
    )

    result = []

    for test in tests:
        test_date = test.result_date or getdate(test.creation)

        # Get test results from normal_test_items child table
        test_items = frappe.get_all("Normal Test Result",
            filters={"parent": test.name},
            fields=["lab_test_name", "result_value", "lab_test_uom", "normal_range"],
            order_by="idx"
        )

        if test_items:
            for idx, item in enumerate(test_items):
                # Determine result status based on normal_range (if available)
                result_status = get_result_status(item.result_value, item.normal_range)

                result.append({
                    "test_date": test_date if idx == 0 else None,
                    "lab_test": test.name if idx == 0 else None,
                    "test_name": test.lab_test_name if idx == 0 else None,
                    "parameter": item.lab_test_name,
                    "result_value": item.result_value,
                    "unit": item.lab_test_uom,
                    "reference_range": item.normal_range or "-",
                    "result_status": result_status,
                    "test_status": test.status if idx == 0 else None,
                    "practitioner": test.practitioner if idx == 0 else None
                })
        else:
            # No detailed results yet
            result.append({
                "test_date": test_date,
                "lab_test": test.name,
                "test_name": test.lab_test_name,
                "parameter": "-",
                "result_value": "-",
                "unit": "-",
                "reference_range": "-",
                "result_status": "-",
                "test_status": test.status,
                "practitioner": test.practitioner
            })

    return result


def get_result_status(result_value, normal_range):
    """
    Determine if result is Normal, High, or Low based on normal_range.
    normal_range is typically in format like "10 - 20" or "< 100" or "> 5"
    """
    if not result_value or not normal_range:
        return "-"

    try:
        result_num = flt(result_value)
    except (ValueError, TypeError):
        # Result is not a number (e.g., "Positive", "Negative")
        return "-"

    normal_range = normal_range.strip()

    # Try to parse range like "10 - 20" or "10-20"
    if " - " in normal_range or "-" in normal_range:
        separator = " - " if " - " in normal_range else "-"
        parts = normal_range.split(separator)
        if len(parts) == 2:
            try:
                min_val = flt(parts[0].strip())
                max_val = flt(parts[1].strip())
                if result_num < min_val:
                    return "Low"
                elif result_num > max_val:
                    return "High"
                else:
                    return "Normal"
            except (ValueError, TypeError):
                pass

    # Try to parse "< 100" or "<100"
    if normal_range.startswith("<"):
        try:
            max_val = flt(normal_range[1:].strip().lstrip("="))
            if result_num > max_val:
                return "High"
            else:
                return "Normal"
        except (ValueError, TypeError):
            pass

    # Try to parse "> 5" or ">5"
    if normal_range.startswith(">"):
        try:
            min_val = flt(normal_range[1:].strip().lstrip("="))
            if result_num < min_val:
                return "Low"
            else:
                return "Normal"
        except (ValueError, TypeError):
            pass

    return "-"


def get_patient_info(patient):
    """Get patient information to display at top of report"""
    if not patient:
        return ""

    patient_doc = frappe.get_doc("Patient", patient)

    info = f"""
    <div style="margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px;">
        <h4 style="margin: 0 0 10px 0;">{patient_doc.patient_name}</h4>
        <table style="width: 100%;">
            <tr>
                <td><strong>Patient ID:</strong> {patient_doc.name}</td>
                <td><strong>Gender:</strong> {patient_doc.sex or '-'}</td>
                <td><strong>DOB:</strong> {patient_doc.dob or '-'}</td>
            </tr>
            <tr>
                <td><strong>Mobile:</strong> {patient_doc.mobile or '-'}</td>
                <td><strong>Email:</strong> {patient_doc.email or '-'}</td>
                <td><strong>Blood Group:</strong> {patient_doc.blood_group or '-'}</td>
            </tr>
        </table>
    </div>
    """

    return info
