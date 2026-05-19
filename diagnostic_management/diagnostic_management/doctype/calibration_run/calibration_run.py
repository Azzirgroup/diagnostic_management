from frappe.model.document import Document


class CalibrationRun(Document):
	def before_save(self):
		if self.performed_date and self.status == "Completed" and self.result == "Pass" and not self.next_due:
			from frappe.utils import add_months, getdate
			self.next_due = add_months(getdate(self.performed_date), 6)
