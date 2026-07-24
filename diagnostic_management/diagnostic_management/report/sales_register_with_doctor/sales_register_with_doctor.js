// Sales Register with Doctor — ERPNext's Sales Register filters, plus a
// Doctor filter fed from the distinct `custom_doctor` values actually recorded
// on submitted invoices (it's a free-text field, so there's no master to link).
frappe.query_reports["Sales Register with Doctor"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			width: "80",
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
			fieldname: "doctor",
			label: __("Doctor"),
			fieldtype: "Autocomplete",
			get_data: function (txt) {
				return new Promise((resolve) => {
					frappe.call({
						method: "diagnostic_management.diagnostic_management.report.sales_register_with_doctor.sales_register_with_doctor.doctor_options",
						args: {
							txt: txt,
							page_len: 50,
							filters: {
								company: frappe.query_report.get_filter_value("company"),
							},
						},
						callback: function (r) {
							resolve((r.message || []).map((row) => row[0]));
						},
					});
				});
			},
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "customer_group",
			label: __("Customer Group"),
			fieldtype: "Link",
			options: "Customer Group",
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "mode_of_payment",
			label: __("Mode of Payment"),
			fieldtype: "Link",
			options: "Mode of Payment",
		},
		{
			fieldname: "owner",
			label: __("Owner"),
			fieldtype: "Link",
			options: "User",
		},
		{
			fieldname: "cost_center",
			label: __("Cost Center"),
			fieldtype: "Link",
			options: "Cost Center",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
		{
			fieldname: "brand",
			label: __("Brand"),
			fieldtype: "Link",
			options: "Brand",
		},
		{
			fieldname: "item_group",
			label: __("Item Group"),
			fieldtype: "Link",
			options: "Item Group",
		},
		{
			fieldname: "include_payments",
			label: __("Show Ledger View"),
			fieldtype: "Check",
			default: 0,
		},
	],
};

// Same accounting-dimension filters the stock Sales Register exposes.
if (typeof erpnext !== "undefined" && erpnext.utils && erpnext.utils.add_dimensions) {
	erpnext.utils.add_dimensions("Sales Register with Doctor", 7);
}
