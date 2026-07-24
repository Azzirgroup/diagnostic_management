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
				__('Rebuild this Lab Report from Sales Invoice <b>{0}</b>?<br><br>Existing rows in Numeric / Grouped / Qualitative / Descriptive tables will be replaced from the source Lab Tests.<br><br>Any package test missing from a draft Lab Test (e.g. a panel nested inside a package, like TFT inside a health package) is expanded first, so those analytes come back too. Results already entered are kept.',
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
						// Call out any Lab Test that was widened — the tech needs to
						// know new analytes just appeared and still need results.
						const repaired = r.message.repaired_lab_tests || [];
						if (repaired.length) {
							const lines = repaired
								.map((x) => `<li><b>${frappe.utils.escape_html(x.lab_test)}</b> — ${x.rows_added} missing test(s) restored</li>`)
								.join('');
							frappe.msgprint({
								title: __('Missing package tests restored'),
								message: __('These Lab Tests were missing analytes from packages nested inside a package. They have been expanded and pulled into this report — the new rows still need results entered.<br><ul>{0}</ul>', [lines]),
								indicator: 'blue',
							});
						}
						frm.reload_doc();
					});
				},
			);
		}, __('Actions'));
	},
});
