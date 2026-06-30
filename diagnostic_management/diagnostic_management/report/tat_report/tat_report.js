// Copyright (c) 2025, Genetest Laboratory
// TAT Report filters

frappe.query_reports["TAT Report"] = {
    "filters": [
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company"),
            "reqd": 1
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0
        },
        {
            "fieldname": "template",
            "label": __("Lab Test Template"),
            "fieldtype": "Link",
            "options": "Lab Test Template",
            "reqd": 0
        },
        {
            "fieldname": "status",
            "label": __("Status"),
            "fieldtype": "Select",
            "options": "\nDraft\nPending\nIn Progress\nCompleted\nApproved\nCancelled",
            "reqd": 0
        },
        {
            "fieldname": "patient",
            "label": __("Patient"),
            "fieldtype": "Link",
            "options": "Patient",
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": __("Branch"),
            "fieldtype": "Link",
            "options": "Branch",
            "reqd": 0
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "tat_status") {
            if (data.tat_status == "Within TAT") {
                value = `<span style="color: #27ae60; font-weight: bold;">${value}</span>`;
            } else if (data.tat_status == "Breached" || data.tat_status == "Overdue") {
                value = `<span style="color: #e74c3c; font-weight: bold;">${value}</span>`;
            } else if (data.tat_status == "In Progress") {
                value = `<span style="color: #3498db;">${value}</span>`;
            }
        }

        if (column.fieldname == "tat_variance" && data.tat_variance > 0) {
            value = `<span style="color: #e74c3c;">+${value}</span>`;
        }

        return value;
    }
};
