// Custom desk actions for Lab Report — adds a "Refetch from Invoice"
// button that re-pulls the Lab Sample + Lab Tests linked to the report's
// Sales Invoice. Handy when the child tables got out of sync (a workflow
// re-opened, rows deleted manually, etc.) — one click and the report
// matches the source of truth again.
frappe.ui.form.on('Lab Report', {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__('Refetch from Invoice'), function () {
			if (!frm.doc.custom_sales_invoice) {
				frappe.msgprint({
					title: __('No linked Invoice'),
					message: __('This Lab Report has no <b>custom_sales_invoice</b> set. Refetch needs an invoice to walk back from.'),
					indicator: 'orange',
				});
				return;
			}
			frappe.confirm(
				__('Rebuild this Lab Report from Sales Invoice <b>{0}</b>? Existing rows in Numeric / Grouped / Qualitative / Descriptive tables will be replaced from the source Lab Tests.',
					[frm.doc.custom_sales_invoice]),
				() => {
					frm.call({
						method: 'refetch_from_invoice',
						doc: frm.doc,
						freeze: true,
						freeze_message: __('Refetching from invoice…'),
					}).then((r) => {
						if (!r || !r.message || !r.message.ok) return;
						const c = r.message.counts || {};
						frappe.show_alert({
							message: __('Refetched from {0}: {1} numeric, {2} grouped, {3} qualitative, {4} descriptive rows.',
								[r.message.sample, c.numeric, c.grouped, c.qualitative, c.descriptive]),
							indicator: 'green',
						}, 6);
						frm.reload_doc();
					});
				},
			);
		}, __('Actions'));
	},
});
