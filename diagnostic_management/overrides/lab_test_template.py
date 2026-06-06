"""Override Marley's Lab Test Template so `sample_qty = 0` (or negative) is
allowed when the user genuinely wants a non-quantitative sample.

Marley's stock validator throws `Sample Quantity cannot be negative or 0`
whenever a Sample is picked and sample_qty <= 0. Some real-world templates
(qualitative tests, swabs, panels billed as a single line) don't have a
meaningful numeric quantity and storing 0 is the right answer. We re-implement
the same checks as the parent, but drop that one throw.
"""
from frappe import _
import frappe
from frappe.utils import flt

from healthcare.healthcare.doctype.lab_test_template.lab_test_template import (
	LabTestTemplate as MarleyLabTestTemplate,
)


class LabTestTemplate(MarleyLabTestTemplate):
	def validate(self):
		# Mirror Marley's validate(), minus the `sample_qty <= 0` throw.
		if (
			self.is_billable
			and not self.link_existing_item
			and (not self.lab_test_rate or self.lab_test_rate <= 0.0)
		):
			frappe.throw(_("Standard Selling Rate should be greater than zero."))

		# NOTE: skipped intentionally — ADMS supports templates with no
		# numeric sample quantity (qualitative / swab / panel-billed tests).
		# if self.sample and flt(self.sample_qty) <= 0:
		#     frappe.throw(_("Sample Quantity cannot be negative or 0"), title=_("Invalid Quantity"))

		self.validate_conversion_factor()
		self.enable_disable_item()
