import frappe
from frappe.model.document import Document


class RadiologyPreAuth(Document):
	def before_save(self):
		if self.status == "Submitted" and not self.submitted_date:
			self.submitted_date = frappe.utils.now_datetime()
		if self.status in ("Approved", "Denied", "Expired", "Cancelled") and not self.decision_date:
			self.decision_date = frappe.utils.now_datetime()
