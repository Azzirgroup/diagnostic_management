// Copyright (c) 2025, Genetest Laboratory
// TAT per Test - GENETEST

frappe.query_reports["TAT per Test - GENETEST"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today()
		},
		{
			fieldname: "template",
			label: __("Lab Test Template"),
			fieldtype: "Link",
			options: "Lab Test Template"
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "\nDraft\nPending\nIn Progress\nCompleted\nApproved\nCancelled"
		},
		{
			fieldname: "patient",
			label: __("Patient"),
			fieldtype: "Link",
			options: "Patient"
		}
	]
};
