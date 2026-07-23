// Copyright (c) 2026, Azzir Group and contributors
// For license information, please see license.txt

frappe.query_reports["Workflow Session Reconciliation"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "session_status",
			label: __("Session Status"),
			fieldtype: "Select",
			options: "\nIn Progress\nCompleted\nCancelled",
		},
		{
			fieldname: "si_status",
			label: __("Sales Invoice Status"),
			fieldtype: "Select",
			options: "\nDraft\nUnpaid\nPartly Paid\nPaid\nOverdue\nCancelled\nReturn\nCredit Note Issued",
		},
		{
			fieldname: "docstatus",
			label: __("SI docstatus"),
			fieldtype: "Select",
			options: "\n0 (Draft)\n1 (Submitted)\n2 (Cancelled)",
		},
		{
			fieldname: "patient",
			label: __("Patient"),
			fieldtype: "Link",
			options: "Patient",
		},
		{
			fieldname: "doctor",
			label: __("Referring Doctor (Data)"),
			fieldtype: "Data",
			description: "Case-insensitive match against Sales Invoice.custom_doctor",
		},
		{
			fieldname: "is_urgent",
			label: __("Urgent Only"),
			fieldtype: "Check",
		},
		{
			fieldname: "unpaid_only",
			label: __("Unpaid / Overdue Only"),
			fieldtype: "Check",
		},
	],

	// Color-code SI status so eyes catch overdue / unpaid quickly.
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "si_status" && data) {
			const map = {
				"Overdue":       "#ef4444",
				"Unpaid":        "#f97316",
				"Partly Paid":   "#eab308",
				"Paid":          "#16a34a",
				"Cancelled":     "#6b7280",
				"Return":        "#6b7280",
				"Credit Note Issued": "#6b7280",
			};
			const color = map[data.si_status];
			if (color) value = `<span style="color:${color};font-weight:600">${value}</span>`;
		}
		if (column.fieldname === "session_status" && data && data.session_status === "In Progress") {
			value = `<span style="color:#2563eb;font-weight:600">${value}</span>`;
		}
		if (column.fieldname === "is_urgent" && data && data.is_urgent) {
			value = `<span style="color:#dc2626;font-weight:700">URGENT</span>`;
		}
		return value;
	},
};
