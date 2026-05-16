import frappe
from frappe.model.document import Document


class PeerReviewCase(Document):
	def before_save(self):
		if self.status == "Closed" and not self.completed_at:
			self.completed_at = frappe.utils.now_datetime()
		if not self.submitted_at:
			self.submitted_at = frappe.utils.now_datetime()
