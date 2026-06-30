// Copyright (c) 2025, Genetest Laboratory
// Patient History Report filters

frappe.query_reports["Patient History"] = {
    "filters": [
        {
            "fieldname": "patient",
            "label": __("Patient"),
            "fieldtype": "Link",
            "options": "Patient",
            "reqd": 1,
            "get_query": function() {
                return {
                    filters: {
                        "status": "Active"
                    }
                };
            }
        },
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -12),
            "reqd": 0
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 0
        }
    ],
    "formatter": function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);

        if (column.fieldname == "result_status") {
            if (data.result_status == "High") {
                value = `<span style="color: #e74c3c; font-weight: bold;">↑ ${value}</span>`;
            } else if (data.result_status == "Low") {
                value = `<span style="color: #3498db; font-weight: bold;">↓ ${value}</span>`;
            } else if (data.result_status == "Normal") {
                value = `<span style="color: #27ae60;">${value}</span>`;
            }
        }

        if (column.fieldname == "test_status") {
            if (data.test_status == "Completed" || data.test_status == "Approved") {
                value = `<span style="color: #27ae60;">${value}</span>`;
            } else if (data.test_status == "Pending" || data.test_status == "Draft") {
                value = `<span style="color: #f39c12;">${value}</span>`;
            }
        }

        return value;
    },
    "tree": false,
    "initial_depth": 1
};
