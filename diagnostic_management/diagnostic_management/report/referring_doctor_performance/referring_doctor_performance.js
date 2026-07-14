// Referring Doctor Performance — filters + drill-down on doctor row.
frappe.query_reports["Referring Doctor Performance"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_months(frappe.datetime.nowdate(), -1),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.nowdate(),
			reqd: 1,
		},
		{
			fieldname: "status",
			label: __("Invoice Status"),
			fieldtype: "Select",
			options: "\nPaid\nUnpaid\nOverdue\nPartly Paid\nReturn\nCredit Note Issued",
			default: "Paid",
		},
		{
			fieldname: "referring_doctor",
			label: __("Referring Doctor"),
			fieldtype: "Link",
			options: "Doctor",
		},
		{
			fieldname: "department",
			label: __("Laboratory Department"),
			fieldtype: "Link",
			options: "Medical Department",
		},
		{
			fieldname: "customer",
			label: __("Customer"),
			fieldtype: "Link",
			options: "Customer",
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
	],

	// Drill-down: clicking a doctor row opens the Sales Invoice list
	// filtered to that doctor within the selected date range.
	onload: function (report) {
		report.page.add_inner_button(__("Open Invoices for Selected Doctor"), () => {
			const doctor = report.get_filter_value("referring_doctor");
			if (!doctor) {
				frappe.msgprint(__("Pick a doctor in the filter first."));
				return;
			}
			frappe.set_route("List", "Sales Invoice", {
				custom_doctor: doctor,
				posting_date: ["between", [
					report.get_filter_value("from_date"),
					report.get_filter_value("to_date"),
				]],
				docstatus: 1,
			});
		});
	},

	formatter: function (value, row, column, data, default_formatter) {
		if (column.fieldname === "doctor_name" && data && data.doctor) {
			const from = frappe.query_report.get_filter_value("from_date");
			const to = frappe.query_report.get_filter_value("to_date");
			const q = encodeURIComponent(JSON.stringify({
				custom_doctor: data.doctor,
				posting_date: ["between", [from, to]],
				docstatus: 1,
			}));
			return `<a href="/app/sales-invoice/view/list?${q}" data-doctor="${frappe.utils.escape_html(data.doctor)}">${default_formatter(value, row, column, data)}</a>`;
		}
		return default_formatter(value, row, column, data);
	},
};
